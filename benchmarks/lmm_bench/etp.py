"""Filtr dokładny względem listy Equational Theories Project (ETP).

Lista: dane/etp_equations.txt (4694 prawa, ≤ 4 operacje, z ETP; hash sprawdzany przy wczytaniu).
Prawo jest „w ETP”, gdy jego postać kanoniczna (przemianowanie, orientacja, dualność) pokrywa się
z postacią kanoniczną któregoś prawa z listy. Dualność włączona celowo: prawo dualne do znanego
uznajemy za wyciek (model mógł je widzieć w lustrzanej postaci).
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from .terms import Law, canonical, parse_law

PATH = Path(__file__).resolve().parent.parent / "dane" / "etp_equations.txt"
SHA256 = "e30e1a6735011ff36fdb228d37b232eb7cda9d4a836cbbefc69c07e6871c8010"


@lru_cache(maxsize=1)
def etp_canonical() -> dict:
    raw = PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise RuntimeError("dane/etp_equations.txt ma inny hash niż zapisany: lista ETP zmieniona")
    out = {}
    for i, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        out.setdefault(canonical(parse_law(line.replace("◇", "*"))), []).append(i)
    return out


def in_etp(law: Law) -> bool:
    return canonical(law) in etp_canonical()


def etp_ids(law: Law) -> list:
    """Numery równań ETP (od 1, jak w pliku) równoważnych prawu z dokładnością do symetrii i dualności."""
    return etp_canonical().get(canonical(law), [])
