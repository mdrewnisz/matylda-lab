"""Wybór nowych praw walidacyjnych dla testu heurystyki przyrostu (reguła jak w HEUR4, wyniki/heur4_wybor_praw_kod.py.txt),
z listą zakazaną poszerzoną o prawa walidacyjne HEUR4 i światy deweloperskie przyrost_dev. Jedyne ziarno generatora: 9191.
    python -m matylda_rdzen.przyrost_wybor_praw
"""
import json

import numpy as np

from .heur4_dev import swiaty_dev
from .heur4_walidacja import PRAWA as PRAWA_HEUR4
from .lmm_trening import _L, _S
from .prawa_losowe import losuj_prawa
from .przyrost_dev import swiaty_dev3
from .s1 import PRAWA_MOCY, ROOT
from .swiat import PRAWA_S0, _tablice, zbuduj_swiat

ZIARNO = 9191
# Generator ziarno 9191 z regułą HEUR4 dał 0 praw (pula praw ≤ 4 działań wyczerpana: 2762/5000 odpada na Jaccardzie w rzędzie 3,
# 1864 na rozmiarze). Dlatego prawa walidacyjne z KLASY WIĘKSZYCH TERMÓW: 2–4 działania po lewej, łącznie ≤ 6 (ziarno 9292).
ZIARNO_DUZE = 9292


def losuj_prawa_duze(liczba, ziarno):
    import random
    from .prawa_losowe import losuj_term, napis
    rng = random.Random(ziarno)
    out, widziane = [], set()
    while len(out) < liczba:
        a = rng.randint(2, 4)
        b = rng.randint(0, min(4, 6 - a))
        l, r = losuj_term(rng, a), losuj_term(rng, b)
        if l == r:
            continue
        s = f"L:{napis(l)}={napis(r)}"
        if s not in widziane:
            widziane.add(s); out.append(s)
    return out


def zb(H, rz):
    sw = zbuduj_swiat(H, rz, "literaly")
    U = _tablice(rz)[sw.world].astype(np.uint8)
    return {m.tobytes() for m in U}, {np.ascontiguousarray(m.T).tobytes() for m in U}, sw


def main(liczba=5):
    L3 = [H for H, *_ in json.load(open(ROOT / "dane" / "swiaty_v3.json"))]
    spent = list(dict.fromkeys(list(PRAWA_S0) + list(PRAWA_MOCY) + _L + _S + L3 + swiaty_dev(120) + list(PRAWA_HEUR4)
                               + swiaty_dev3(40)))
    TESTOWANE = set(PRAWA_S0) | set(PRAWA_MOCY) | set(PRAWA_HEUR4)
    ref = {rz: [] for rz in (3, 4)}
    for H in spent:
        for rz in (3, 4):
            a, at, _ = zb(H, rz)
            if a:
                ref[rz].append((H, a, at))

    def zly(a, at, rz):
        for H, b, bt in ref[rz]:
            for x in (a, at):
                if len(x & b) / len(x | b) >= 0.5 or (H in TESTOWANE and b <= x):
                    return H
        return None

    out = []
    for H in losuj_prawa_duze(5000, ZIARNO_DUZE):
        if H in spent:
            continue
        ok, info = True, []
        for rz in (3, 4):
            a, at, sw = zb(H, rz)
            if len(sw.world) < 20 or len(sw.TR) < 15 or zly(a, at, rz):
                ok = False
                break
            info += [len(sw.world), len(sw.TR)]
        if ok:
            out.append((H, info))
            for rz in (3, 4):
                a, at, _ = zb(H, rz)
                ref[rz].append((H, a, at))
        if len(out) >= liczba:
            break
    return out


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False))
