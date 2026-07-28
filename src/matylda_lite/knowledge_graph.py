"""knowledge_graph.py — v0.5 typed knowledge graph with confidence propagation.

Storage: data/knowledge_graph.json (single file, loaded fully into memory)

Entity kinds: "thread" | "insight" | "concept" | "external"
Relation types (7): contradicts | extends | cites | refutes | supports | depends_on | failed_approach

Confidence propagation rules (depth-limited BFS):
  A -[contradicts(p)]→ B -[supports(q)]→ C     → A -[weakens(p*q)]→ C
  A -[contradicts(p)]→ B -[contradicts(q)]→ C  → A -[reinforces(p*q*0.9)]→ C  (double negation)
  A -[supports(p)]→ B -[supports(q)]→ C         → A -[supports(p*q*0.9)]→ C
  A -[supports(p)]→ B -[contradicts(q)]→ C      → A -[weakens(p*q)]→ C
  A -[extends(p)]→ B -[extends(q)]→ C           → A -[extends(p*q*0.9)]→ C
  A -[depends_on(p)]→ B -[refutes(q)]→ C        → A -[threatened_by(p*q)]→ C
  failed_approach is terminal — nothing propagates through it

Inferred relations are NOT stored; they are computed on demand.

Design constraints:
  - No circular imports (no secretary, no darkroom, no server)
  - All numeric limits from BOUNDS
  - Thread-safe writes via file lock simulation (single writer, read-only queries safe)
"""
from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ROOT
from .constitutional import BOUNDS

GRAPH_FILE = ROOT / "data" / "knowledge_graph.json"
GRAPH_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────

RELATION_TYPES: frozenset[str] = frozenset({
    "contradicts",
    "extends",
    "cites",
    "refutes",
    "supports",
    "depends_on",
    "failed_approach",
})

ENTITY_KINDS: frozenset[str] = frozenset({
    "thread", "insight", "concept", "external",
})

# Propagation table: (A→B type, B→C type) → (derived A→C type, damping factor)
# Confidence of inferred edge = conf_AB * conf_BC * damping
_PROPAGATION: dict[tuple[str, str], tuple[str, float]] = {
    ("contradicts", "supports"):    ("weakens",     1.0),
    ("contradicts", "contradicts"): ("reinforces",  0.9),  # double negation
    ("contradicts", "refutes"):     ("supports_source", 0.85),
    ("supports",    "supports"):    ("supports",    0.9),
    ("supports",    "contradicts"): ("weakens",     1.0),
    ("supports",    "refutes"):     ("weakens",     0.9),
    ("supports",    "extends"):     ("supports",    0.85),
    ("extends",     "extends"):     ("extends",     0.9),
    ("extends",     "supports"):    ("supports",    0.85),
    ("extends",     "contradicts"): ("weakens",     0.9),
    ("depends_on",  "refutes"):     ("threatened_by", 1.0),
    ("depends_on",  "contradicts"): ("threatened_by", 0.9),
    ("cites",       "contradicts"): ("aware_of_contradiction", 0.8),
    ("cites",       "extends"):     ("aware_of_extension", 0.8),
}

# Relation types that are "terminal" — propagation stops here
_TERMINAL_TYPES: frozenset[str] = frozenset({"failed_approach"})

_WRITE_LOCK = threading.Lock()


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Relation:
    """A typed, weighted edge in the knowledge graph."""
    relation_id: str
    rel_type:    str           # one of RELATION_TYPES
    target:      str           # entity_id of target
    confidence:  float         # 0.0–1.0
    source:      str           # "user" | "auto" | insight_id | diary_id
    note:        str = ""
    date:        str = ""

    def __post_init__(self) -> None:
        if not self.date:
            self.date = datetime.now(timezone.utc).isoformat()
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class Entity:
    """A node in the knowledge graph."""
    entity_id:   str
    label:       str           # human-readable name
    kind:        str           # one of ENTITY_KINDS
    thread_stem: str | None = None
    insight_id:  str | None = None
    description: str = ""
    tags:        list[str] = field(default_factory=list)
    relations:   list[Relation] = field(default_factory=list)
    created:     str = ""
    updated:     str = ""

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if not self.created:
            self.created = now
        if not self.updated:
            self.updated = now

    def touch(self) -> None:
        self.updated = datetime.now(timezone.utc).isoformat()

    def outgoing(self, rel_type: str | None = None) -> list[Relation]:
        if rel_type:
            return [r for r in self.relations if r.rel_type == rel_type]
        return list(self.relations)


@dataclass
class InferredRelation:
    """A relation inferred through confidence propagation (not stored)."""
    from_entity: str
    via_entity:  str
    to_entity:   str
    derived_type: str
    confidence:  float
    path:        list[str]      # [from, via, ..., to]


# ── Serialization ─────────────────────────────────────────────────────────────

def _relation_to_dict(r: Relation) -> dict:
    return asdict(r)


def _relation_from_dict(d: dict) -> Relation:
    return Relation(**{k: v for k, v in d.items() if k in Relation.__dataclass_fields__})


def _entity_to_dict(e: Entity) -> dict:
    d = asdict(e)
    d["relations"] = [_relation_to_dict(r) for r in e.relations]
    return d


def _entity_from_dict(d: dict) -> Entity:
    rels = [_relation_from_dict(r) for r in d.pop("relations", [])]
    e = Entity(**{k: v for k, v in d.items() if k in Entity.__dataclass_fields__})
    e.relations = rels
    return e


# ── Persistence ───────────────────────────────────────────────────────────────

def _load_raw() -> dict:
    if not GRAPH_FILE.exists():
        return {"version": "0.5", "entities": {}, "updated": ""}
    try:
        return json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"version": "0.5", "entities": {}, "updated": ""}


def load_graph() -> dict[str, Entity]:
    """Return {entity_id: Entity} dict from disk."""
    raw = _load_raw()
    return {
        eid: _entity_from_dict(edata)
        for eid, edata in raw.get("entities", {}).items()
    }


def _save_graph(entities: dict[str, Entity]) -> None:
    """Write full graph to disk (caller holds _WRITE_LOCK)."""
    payload = {
        "version":  "0.5",
        "updated":  datetime.now(timezone.utc).isoformat(),
        "entities": {eid: _entity_to_dict(e) for eid, e in entities.items()},
    }
    GRAPH_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2))


# ── Mutations ─────────────────────────────────────────────────────────────────

def add_entity(
    *,
    entity_id:   str | None = None,
    label:       str,
    kind:        str = "concept",
    thread_stem: str | None = None,
    insight_id:  str | None = None,
    description: str = "",
    tags:        list[str] | None = None,
) -> Entity:
    """Add or update an entity. Returns the entity.

    If entity_id already exists, updates label/description/tags only.
    """
    if kind not in ENTITY_KINDS:
        raise ValueError(f"kind must be one of {ENTITY_KINDS}, got: {kind!r}")

    with _WRITE_LOCK:
        entities = load_graph()
        eid = entity_id or f"ent_{uuid.uuid4().hex[:8]}"

        if eid in entities:
            e = entities[eid]
            e.label       = label or e.label
            e.description = description or e.description
            if tags:
                e.tags = list(set(e.tags) | set(tags))
            e.touch()
        else:
            e = Entity(
                entity_id=eid, label=label, kind=kind,
                thread_stem=thread_stem, insight_id=insight_id,
                description=description, tags=tags or [],
            )
            entities[eid] = e

        _save_graph(entities)
        return e


def add_relation(
    *,
    from_id:    str,
    rel_type:   str,
    to_id:      str,
    confidence: float,
    source:     str = "user",
    note:       str = "",
) -> Relation:
    """Add a typed relation from from_id → to_id.

    Both entities must exist. Duplicate (from, type, to) triples are
    updated in-place rather than duplicated.
    """
    if rel_type not in RELATION_TYPES:
        raise ValueError(f"rel_type must be one of {RELATION_TYPES}")
    confidence = max(0.0, min(1.0, confidence))

    with _WRITE_LOCK:
        entities = load_graph()
        if from_id not in entities:
            raise KeyError(f"Entity not found: {from_id!r}")
        if to_id not in entities:
            raise KeyError(f"Entity not found: {to_id!r}")

        entity = entities[from_id]

        # Update existing relation of same (type, target) rather than duplicate
        for existing in entity.relations:
            if existing.rel_type == rel_type and existing.target == to_id:
                existing.confidence = confidence
                existing.source = source
                existing.note   = note
                existing.date   = datetime.now(timezone.utc).isoformat()
                entity.touch()
                _save_graph(entities)
                return existing

        rel = Relation(
            relation_id=f"rel_{uuid.uuid4().hex[:8]}",
            rel_type=rel_type, target=to_id,
            confidence=confidence, source=source, note=note,
        )
        entity.relations.append(rel)
        entity.touch()
        _save_graph(entities)
        return rel


def remove_relation(from_id: str, relation_id: str) -> bool:
    """Remove a relation by relation_id. Returns True if found."""
    with _WRITE_LOCK:
        entities = load_graph()
        if from_id not in entities:
            return False
        entity = entities[from_id]
        before = len(entity.relations)
        entity.relations = [r for r in entity.relations if r.relation_id != relation_id]
        if len(entity.relations) < before:
            entity.touch()
            _save_graph(entities)
            return True
        return False


# ── Queries ───────────────────────────────────────────────────────────────────

def get_entity(entity_id: str) -> Entity | None:
    return load_graph().get(entity_id)


def find_entity_by_label(label: str, kind: str | None = None) -> Entity | None:
    """Case-insensitive label lookup."""
    label_lower = label.lower()
    for e in load_graph().values():
        if kind and e.kind != kind:
            continue
        if e.label.lower() == label_lower:
            return e
    return None


def get_incoming(entity_id: str, entities: dict[str, Entity] | None = None) -> list[tuple[Entity, Relation]]:
    """Return [(source_entity, relation)] for all relations pointing TO entity_id."""
    graph = entities or load_graph()
    result: list[tuple[Entity, Relation]] = []
    for e in graph.values():
        for r in e.relations:
            if r.target == entity_id:
                result.append((e, r))
    return result


def get_neighbours(entity_id: str) -> dict[str, Any]:
    """Return outgoing and incoming relations for an entity."""
    graph = load_graph()
    entity = graph.get(entity_id)
    if entity is None:
        return {}
    incoming = get_incoming(entity_id, graph)
    return {
        "entity":   _entity_to_dict(entity),
        "outgoing": [_relation_to_dict(r) for r in entity.relations],
        "incoming": [
            {
                "from_entity": e.entity_id,
                "from_label":  e.label,
                **_relation_to_dict(r),
            }
            for e, r in incoming
        ],
    }


# ── Confidence propagation ────────────────────────────────────────────────────

def propagate(
    entity_id: str,
    max_depth: int = 2,
    min_confidence: float = 0.3,
) -> list[InferredRelation]:
    """BFS confidence propagation from entity_id up to max_depth hops.

    Returns inferred relations (not stored — computed on demand).
    Stops at terminal relation types (failed_approach).
    Filters out inferred relations below min_confidence.
    """
    graph = load_graph()
    if entity_id not in graph:
        return []

    inferred: list[InferredRelation] = []
    seen_paths: set[tuple[str, ...]] = set()

    # Queue: (current_entity_id, accumulated_path, accumulated_confidence, last_rel_type)
    queue: list[tuple[str, list[str], float, str | None]] = [
        (entity_id, [entity_id], 1.0, None)
    ]

    while queue:
        current_id, path, acc_conf, last_type = queue.pop(0)
        if len(path) > max_depth + 1:
            continue

        entity = graph.get(current_id)
        if entity is None:
            continue

        for rel in entity.relations:
            if rel.rel_type in _TERMINAL_TYPES:
                continue  # don't propagate through failed_approach
            if len(path) > 1:
                # We're at depth >= 1 — try to infer a relation from the origin
                derived_key = (last_type, rel.rel_type)
                if derived_key not in _PROPAGATION:
                    continue
                derived_type, damping = _PROPAGATION[derived_key]
                inferred_conf = round(acc_conf * rel.confidence * damping, 4)
                if inferred_conf < min_confidence:
                    continue
                path_tuple = tuple(path + [rel.target])
                if path_tuple in seen_paths:
                    continue
                seen_paths.add(path_tuple)
                inferred.append(InferredRelation(
                    from_entity  = entity_id,
                    via_entity   = current_id,
                    to_entity    = rel.target,
                    derived_type = derived_type,
                    confidence   = inferred_conf,
                    path         = list(path) + [rel.target],
                ))
            # Continue BFS
            new_path = path + [rel.target]
            queue.append((rel.target, new_path, acc_conf * rel.confidence, rel.rel_type))

    # Sort by confidence desc
    inferred.sort(key=lambda x: x.confidence, reverse=True)
    return inferred


# ── Auto-detect from thread similarity ───────────────────────────────────────

def auto_register_thread(stem: str, label: str | None = None) -> Entity:
    """Ensure a thread entity exists in the graph. Idempotent.

    Called by the thread.write hook when a thread file is saved.
    """
    entity_id = f"thread:{stem}"
    return add_entity(
        entity_id=entity_id,
        label=label or stem.replace("_", " ").title(),
        kind="thread",
        thread_stem=stem,
    )


def suggest_relations_from_links(
    stem: str,
    min_similarity: float = 0.75,
) -> list[dict]:
    """Read thread_links.json and suggest knowledge graph relations.

    Returns a list of suggested relation dicts (not applied automatically —
    must be confirmed via add_relation to keep epistemic integrity).
    Each dict: {from_id, rel_type_suggestion, to_id, confidence, reason}

    Similarity score from thread_links is cosine-like (shared keywords / min_kws).
    We map it to relation suggestion:
      score >= 0.75 → "extends" (high overlap, probably building on same ideas)
      To refine: user can override to contradicts/supports/etc.
    """
    links_file = ROOT / "data" / "thread_links.json"
    if not links_file.exists():
        return []
    try:
        all_links: dict = json.loads(links_file.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []

    links = all_links.get(stem, [])
    suggestions: list[dict] = []
    graph = load_graph()

    from_id = f"thread:{stem}"

    for link in links:
        score = link.get("score", 0)
        target_stem = link.get("stem", "")
        if not target_stem or score < min_similarity * 100:  # links use integer scores
            continue
        to_id = f"thread:{target_stem}"
        # Only suggest if both are registered (or auto-register target)
        if from_id not in graph:
            continue
        suggestions.append({
            "from_id":    from_id,
            "to_id":      to_id,
            "from_label": stem.replace("_", " ").title(),
            "to_label":   target_stem.replace("_", " ").title(),
            "confidence": min(0.95, round(score / 100, 2)),
            "rel_type_suggestion": "extends",
            "reason":     f"semantic overlap score={score}, shared={link.get('shared', [])[:4]}",
            "shared_keywords": link.get("shared", [])[:6],
        })

    return suggestions[:5]  # top 5 suggestions per thread


# ── Graph statistics ──────────────────────────────────────────────────────────

def graph_stats() -> dict[str, Any]:
    """Summary statistics for dashboard and briefing."""
    graph = load_graph()
    total_entities = len(graph)
    total_relations = sum(len(e.relations) for e in graph.values())

    kind_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for e in graph.values():
        kind_counts[e.kind] = kind_counts.get(e.kind, 0) + 1
        for r in e.relations:
            type_counts[r.rel_type] = type_counts.get(r.rel_type, 0) + 1

    most_connected = sorted(
        [(e.entity_id, e.label, len(e.relations)) for e in graph.values()],
        key=lambda x: x[2], reverse=True,
    )[:5]

    return {
        "total_entities":  total_entities,
        "total_relations": total_relations,
        "by_kind":         kind_counts,
        "by_relation_type": type_counts,
        "most_connected":  [
            {"entity_id": eid, "label": lbl, "relation_count": cnt}
            for eid, lbl, cnt in most_connected
        ],
        "graph_file": str(GRAPH_FILE.relative_to(ROOT)) if GRAPH_FILE.is_relative_to(ROOT) else str(GRAPH_FILE),
    }
