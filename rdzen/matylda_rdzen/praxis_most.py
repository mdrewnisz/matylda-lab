"""Most do Praxis: seedy z przebudzenia stają się rekordami hipotez w stanie SEED.

Praxis jest bramą przebudzenia: sen tylko proponuje, status może zmienić weryfikator lub człowiek.
Praxis jest zależnością opcjonalną; bez niego seedy zapisuje się jako JSON.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .fazy import Seed


def praxis_dostepny() -> bool:
    try:
        import matylda_praxis.domain.models  # noqa: F401
        return True
    except ImportError:
        return False


def do_praxis(seedy: list[Seed]):
    """Zwraca listę HypothesisRecord (stan SEED). Wymaga zainstalowanego matylda_praxis."""
    from matylda_praxis.domain.models import HypothesisRecord
    return [HypothesisRecord.seed(s.tytul) for s in seedy]


def do_json(seedy: list[Seed], sciezka: str | Path) -> Path:
    sciezka = Path(sciezka)
    sciezka.write_text(json.dumps([{**asdict(s), "status": "seed"} for s in seedy],
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    return sciezka
