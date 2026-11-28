"""Klasa D1': nowe pojęcia i niezmienniki (sprawdzacz przed modelem).

Zadanie: rodzina F (20 magm rozmiaru 5–7) i lista pojęć podanych G (prawa z nazwami).
Model zgłasza (i) definicję nowej własności jako prawa w DSL oraz (ii) implikacje
„koniunkcja pojęć ⇒ pojęcie” z jej udziałem, nad klasą światów.

Warunki zaliczenia nowego pojęcia (spec 2.0, sekcja Klasy zadań):
  (a) składnia: jedno działanie, ≤ 3 zmienne, termy głębokości ≤ 4;
  (b) na F i na rodzinie odłożonej H sygnatura (w których światach prawo zachodzi) różni się
      od sygnatury każdego pojęcia z G oraz każdej koniunkcji i alternatywy dwóch pojęć z G;
  (c) pojęcie występuje w co najmniej jednej NIETRYWIALNEJ implikacji o statusie
      NIEOBALONA_W_ZAKRESIE na F ∪ H.
Doprecyzowania tej implementacji (PROPOZYCJA, do zatwierdzenia razem ze spec):
  * pojęcie stałe na F ∪ H (zachodzi wszędzie albo nigdzie) nie przechodzi (b);
  * implikacja jest trywialna, gdy poprzednik nie zachodzi w żadnym świecie, następnik zachodzi
    we wszystkich, następnik jest w poprzedniku, albo następnik jest podstawieniem prawa z poprzednika;
  * implikacja dowodliwa równaniowo (entail.prove) dostaje dodatkowo zakres U i status PROVED.
Wariant N: pojęcie spoza listy ETP (etp.in_etp == False).

Ziarna rodzin D1' w pilocie: od 2100 (2000–2099 zajęte przez pilot D1-W i serię rdzenia).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from . import basis, entail, etp, worlds
from .status import Status
from .terms import Law, canonical, depth, holds, law_variables, parse_law, show_law

PILOT_SEEDS_FROM = 2100
MAX_VARS = 3
MAX_DEPTH = 4

GIVEN = {                                   # lista pojęć podanych (G)
    "przemienność": "x*y = y*x",
    "łączność": "(x*y)*z = x*(y*z)",
    "idempotentność": "x*x = x",
    "lewa_projekcja": "x*y = x",
    "prawa_projekcja": "x*y = y",
    "lewa_dystrybutywność": "x*(y*z) = (x*y)*(x*z)",
    "medialność": "(x*y)*(z*w) = (x*z)*(y*w)",
    "inwolucyjność_lewa": "x*(x*y) = y",
}
GIVEN_LAWS = {k: parse_law(v) for k, v in GIVEN.items()}

KINDS = (worlds.affine_magma, worlds.isotope_magma, worlds.unary_magma, worlds.random_magma)


def make_family(seed: int, size: int = 20) -> list:
    """Rodzina światów: mieszanka rodzajów, rozmiary 5–7, wszystko z jednego ziarna bazowego."""
    rng = np.random.default_rng(seed)
    fam = []
    for i in range(size):
        kind = KINDS[i % len(KINDS)]
        n = int(rng.integers(5, 8))
        fam.append(kind(n, seed * 100 + i))
    return fam


def signature(law: Law, fam: list) -> tuple:
    return tuple(holds(law, w.table) for w in fam)


@dataclass
class ConceptVerdict:
    law: Law
    ok_syntax: bool
    ok_new: bool
    reason: str
    in_etp: bool
    sig: tuple = field(default=())


def check_concept(law: Law, fam: list, held: list, given=GIVEN_LAWS) -> ConceptVerdict:
    in_e = etp.in_etp(law)
    if len(law_variables(law)) > MAX_VARS or max(depth(law[0]), depth(law[1])) > MAX_DEPTH:
        return ConceptVerdict(law, False, False, "składnia: > 3 zmienne albo głębokość > 4", in_e)
    allw = list(fam) + list(held)
    sig = np.array(signature(law, allw))
    if sig.all() or not sig.any():
        return ConceptVerdict(law, True, False, "stałe na F ∪ H", in_e, tuple(sig))
    gs = {k: np.array(signature(g, allw)) for k, g in given.items()}
    for k, g in gs.items():
        if (g == sig).all():
            return ConceptVerdict(law, True, False, f"równoważne pojęciu {k} na F ∪ H", in_e, tuple(sig))
    for (k1, g1), (k2, g2) in combinations(gs.items(), 2):
        if ((g1 & g2) == sig).all():
            return ConceptVerdict(law, True, False, f"równoważne {k1} ∧ {k2}", in_e, tuple(sig))
        if ((g1 | g2) == sig).all():
            return ConceptVerdict(law, True, False, f"równoważne {k1} ∨ {k2}", in_e, tuple(sig))
    return ConceptVerdict(law, True, True, "nowe", in_e, tuple(sig))


@dataclass
class ImplicationVerdict:
    antecedent: tuple
    consequent: Law
    status: Status
    trivial: bool
    reason: str
    proved: bool = False
    certificate: object = None


def check_implication(antecedent: list, consequent: Law, fam: list, held: list,
                      node_limit: int = 5000) -> ImplicationVerdict:
    allw = list(fam) + list(held)
    a = np.array([all(holds(l, w.table) for l in antecedent) for w in allw])
    b = np.array(signature(consequent, allw))
    ant = tuple(antecedent)
    bad = np.flatnonzero(a & ~b)
    if bad.size:
        return ImplicationVerdict(ant, consequent, Status.DISPROVED, False,
                                  "kontrprzykład w rodzinie", certificate=int(bad[0]))
    c = canonical(consequent)
    if not a.any():
        triv, why = True, "poprzednik nie zachodzi nigdzie"
    elif b.all():
        triv, why = True, "następnik zachodzi wszędzie"
    elif any(canonical(x) == c for x in antecedent):
        triv, why = True, "następnik jest w poprzedniku"
    elif any(basis.is_instance(consequent, x) for x in antecedent):
        triv, why = True, "następnik jest podstawieniem prawa z poprzednika"
    else:
        triv, why = False, "nietrywialna"
    steps = entail.prove(list(antecedent), consequent, node_limit=node_limit)
    return ImplicationVerdict(ant, consequent, Status.NIEOBALONA_W_ZAKRESIE, triv, why,
                              proved=steps is not None, certificate=steps)


def score(concepts: list, implications: list, fam: list, held: list, variant_N: bool = False) -> dict:
    """concepts: lista praw (nowe pojęcia); implications: lista (poprzednik: list[Law], następnik: Law).

    Zalicza pojęcie, gdy spełnia (a), (b) i (c). Pojęcia o tej samej sygnaturze na F ∪ H są jednym atomem
    (inna składnia tej samej własności nie daje punktu). NPH* = baza reguł Horna nad atomami dla dobrych
    implikacji z udziałem nowego pojęcia; wiedza początkowa = implikacje między pojęciami G na F ∪ H."""
    allw = list(fam) + list(held)

    def atom(l):                       # pojęcia równoważne na F ∪ H to jeden atom
        return "".join("1" if b else "0" for b in signature(l, allw))

    cv = [check_concept(l, fam, held) for l in concepts]
    new = {}
    for v in cv:
        if v.ok_new and (v.in_etp is False or not variant_N):
            new.setdefault(atom(v.law), v)          # duplikaty semantyczne liczą się raz
    iv = [check_implication(a, c, fam, held) for a, c in implications]
    good = [v for v in iv if v.status is Status.NIEOBALONA_W_ZAKRESIE and not v.trivial]
    used, rules = set(), []
    for v in good:
        atoms = [atom(l) for l in list(v.antecedent) + [v.consequent]]
        hit = [a for a in atoms if a in new]
        if hit:
            used.update(hit)
            rules.append((frozenset(atoms[:-1]), atoms[-1]))
    nph = basis.nph_star_rules(rules, initial=initial_rules(fam, held, atom))
    return {"pojecia_zgloszone": len(concepts), "pojecia_nowe": len(new), "pojecia_zaliczone": len(used),
            "implikacje_zgloszone": len(implications), "implikacje_dobre": len(good),
            "implikacje_dowiedzione": sum(v.proved for v in good), "nph_star_reguly": len(nph),
            "werdykty_pojec": cv, "werdykty_implikacji": iv}


def initial_rules(fam: list, held: list, atom) -> list:
    """Wiedza początkowa: implikacje g1 ⇒ g2 między pojęciami podanymi, nieobalone na F ∪ H
    (atomy = sygnatury, jak w score)."""
    allw = list(fam) + list(held)
    sig = {k: np.array(signature(g, allw)) for k, g in GIVEN_LAWS.items()}
    out = []
    for k1, s1 in sig.items():
        for k2, s2 in sig.items():
            if k1 != k2 and s1.any() and not (s1 & ~s2).any():
                out.append((frozenset([atom(GIVEN_LAWS[k1])]), atom(GIVEN_LAWS[k2])))
    return out


# ---------- pilot D1' bez modelu (ramiona widzą tylko F; H służy wyłącznie do oceny) ----------
K = 20


def _given_list():
    return list(GIVEN_LAWS.values())


def arm_E(K=K, pool=None):
    """Enumerator: k-te prawo puli jako pojęcie, implikacja pojęcie ⇒ kolejne pojęcie z G (cyklicznie)."""
    from . import controls
    pool = list(controls.law_pool(4)) if pool is None else pool
    g = _given_list()
    return [(pool[k], ([pool[k]], g[k % len(g)])) for k in range(K)]


def arm_R0(seed, K=K, pool=None):
    from . import controls
    pool = list(controls.law_pool(4)) if pool is None else pool
    rng = np.random.default_rng(seed + 20_000_000)
    g = _given_list()
    out = []
    for i in rng.choice(len(pool), K, replace=False):
        c, t = pool[int(i)], g[int(rng.integers(len(g)))]
        out.append((c, ([c], t) if rng.integers(2) else ([t], c)))
    return out


def arm_C(fam, K=K, pool=None):
    """Pętla symboliczna: pojęcie z puli nowe NA F (bez H), dobierane z najmniejszych;
    implikacja z G, prawdziwa na F i nietrywialna na F, w obu kierunkach; pierwsza znaleziona."""
    from . import controls
    pool = list(controls.law_pool(4)) if pool is None else pool
    out, seen_sig = [], set()
    for law in pool:
        if len(out) >= K:
            break
        v = check_concept(law, fam, [])
        if not v.ok_new or v.sig in seen_sig:
            continue
        sig = np.array(v.sig)
        for gname, g in GIVEN_LAWS.items():
            gs = np.array(signature(g, fam))
            if not (sig & ~gs).any() and not gs.all():
                out.append((law, ([law], g)))
                break
            if gs.any() and not (gs & ~sig).any():
                out.append((law, ([g], law)))
                break
        else:
            continue
        seen_sig.add(v.sig)
    return out


def pool_variant_N(max_ops=5):
    """Pula dla wariantu N: prawa ≤ max_ops operacji, ≤ 3 zmienne, SPOZA listy ETP, od najmniejszych."""
    from . import controls
    return [l for l in controls.law_pool(max_ops) if not etp.in_etp(l)]


def run_pilot(n_families=5, first_seed=PILOT_SEEDS_FROM):
    pool_N = pool_variant_N()
    rows = []
    for i in range(n_families):
        fs, hs = first_seed + 2 * i, first_seed + 2 * i + 1
        F, H = make_family(fs), make_family(hs)
        rec = {"F": fs, "H": hs}
        arms = (("E", arm_E(), False), ("R0", arm_R0(fs), False), ("C", arm_C(F), False),
                ("E_N", arm_E(pool=pool_N), True), ("R0_N", arm_R0(fs, pool=pool_N), True),
                ("C_N", arm_C(F, pool=pool_N), True))
        for name, subs, variant in arms:
            r = score([c for c, _ in subs], [imp for _, imp in subs], F, H, variant_N=variant)
            rec[name] = {k: v for k, v in r.items() if not k.startswith("werdykty")}
        rows.append(rec)
    return rows


if __name__ == "__main__":
    import json
    import sys
    json.dump(run_pilot(int(sys.argv[1]) if len(sys.argv) > 1 else 5), sys.stdout, ensure_ascii=False, indent=1)
