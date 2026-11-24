"""Losowe prawa równościowe jako źródło wielu światów treningowych dla intuicji LMM (v3).

Prawo zapisujemy jako nazwę „L:<lewy>=<prawy>”, np. „L:(x*(y*x))=((x*y)*y)”. `zbuduj_swiat` rozpoznaje ten prefiks
i liczy maskę prawa na danym uniwersum. Termy: zmienne x, y, z; 1–3 działania na stronę, łącznie ≤ 4.
"""
from __future__ import annotations

import itertools
import random

import numpy as np

ZMIENNE = ("x", "y", "z")


def losuj_term(rng: random.Random, ops: int):
    if ops == 0:
        return rng.choice(ZMIENNE)
    lewe = rng.randint(0, ops - 1)
    return (losuj_term(rng, lewe), losuj_term(rng, ops - 1 - lewe))


def napis(t) -> str:
    return t if isinstance(t, str) else f"({napis(t[0])}*{napis(t[1])})"


def parsuj(s: str):
    s = s.strip()
    if s in ZMIENNE:
        return s
    assert s[0] == "(" and s[-1] == ")", s
    g, i = 0, 1
    for i in range(1, len(s) - 1):
        g += {"(": 1, ")": -1}.get(s[i], 0)
        if g == 0 and s[i] == "*":
            break
    return (parsuj(s[1:i]), parsuj(s[i + 1:-1]))


def _zm(t, acc):
    if isinstance(t, str):
        acc.add(t)
    else:
        _zm(t[0], acc); _zm(t[1], acc)
    return acc


def maska_prawa(nazwa: str, U: np.ndarray) -> np.ndarray:
    """Które tablice U (liczba, n, n) spełniają prawo „L:l=r”."""
    l, r = (parsuj(x) for x in nazwa[2:].split("="))
    vs = sorted(_zm(l, set()) | _zm(r, set()))
    n, NM = U.shape[1], len(U)
    I = np.arange(NM)[:, None]
    X = np.array(list(itertools.product(range(n), repeat=len(vs))))
    env = {v: X[:, i][None].repeat(NM, 0) for i, v in enumerate(vs)}

    def ev(t):
        return env[t] if isinstance(t, str) else U[I, ev(t[0]), ev(t[1])]
    return (ev(l) == ev(r)).all(1)


def losuj_prawa(liczba: int, ziarno: int) -> list[str]:
    rng = random.Random(ziarno)
    out, widziane = [], set()
    while len(out) < liczba:
        a = rng.randint(1, 3)
        b = rng.randint(0, min(3, 4 - a))
        l, r = losuj_term(rng, a), losuj_term(rng, b)
        if l == r:
            continue
        s = f"L:{napis(l)}={napis(r)}"
        if s not in widziane:
            widziane.add(s); out.append(s)
    return out


def swiaty_z_praw(liczba=2000, ziarno=31337):
    """Odtwarza dane/swiaty_v3.json: (prawo, uniwersum, |świat|, |TR|) dla ≥ 20 magm i |TR| ≥ 15, bez duplikatów światów."""
    from .swiat import zbuduj_swiat
    out, widziane = [], set()
    for H in losuj_prawa(liczba, ziarno):
        for rz in ("3T", "4T"):
            sw = zbuduj_swiat(H, rz, "literaly")
            k = (rz, tuple(sw.world))
            if len(sw.world) >= 20 and len(sw.TR) >= 15 and k not in widziane:
                widziane.add(k)
                out.append((H, rz, len(sw.world), len(sw.TR)))
    return out


if __name__ == "__main__":      # python -m matylda_rdzen.prawa_losowe > dane/swiaty_v3.json  (~11 min)
    import json
    print(json.dumps(swiaty_z_praw(), ensure_ascii=False))
