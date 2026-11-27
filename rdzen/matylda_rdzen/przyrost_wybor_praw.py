"""Wybór nowych praw walidacyjnych dla testu heurystyki przyrostu (reguła jak w HEUR4, wyniki/heur4_wybor_praw_kod.py.txt),
z listą zakazaną poszerzoną o prawa walidacyjne HEUR4 i światy deweloperskie przyrost_dev.
Próba 1: losuj_prawa (≤ 4 działania), ziarno 9191 → 0 praw (odtworzenie z licznikami odrzuceń: --proba9191, zapis wyniki/przyrost_wybor_praw.json).
Próba 2 (użyta): klasa większych termów, ziarno 9292 → 5 praw.  Pilot tej klasy (B2 recenzji): ziarno 9393, --pilot.
    python -m matylda_rdzen.przyrost_wybor_praw [--proba9191 | --pilot]
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
# Generator ziarno 9191 z regułą HEUR4 dał 0 praw (pula praw ≤ 4 działań wyczerpana: 2872/5000 odpada na Jaccardzie lub nadzbiorze w rzędzie 3,
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


def main(liczba=5, generator=None, liczniki=None, zakaz_dodatkowy=()):
    L3 = [H for H, *_ in json.load(open(ROOT / "dane" / "swiaty_v3.json"))]
    spent = list(dict.fromkeys(list(PRAWA_S0) + list(PRAWA_MOCY) + _L + _S + L3 + swiaty_dev(120) + list(PRAWA_HEUR4)
                               + swiaty_dev3(40) + list(zakaz_dodatkowy)))
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
    for H in (generator or losuj_prawa_duze(5000, ZIARNO_DUZE)):
        if H in spent:
            if liczniki is not None:
                liczniki["na_liscie"] = liczniki.get("na_liscie", 0) + 1
            continue
        ok, info = True, []
        for rz in (3, 4):
            a, at, sw = zb(H, rz)
            powod = "rozmiar" if len(sw.world) < 20 or len(sw.TR) < 15 else "jaccard_lub_nadzbior" if zly(a, at, rz) else None
            if powod:
                if liczniki is not None:
                    liczniki[f"{powod}_rz{rz}"] = liczniki.get(f"{powod}_rz{rz}", 0) + 1
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
    import sys
    if "--proba9191" in sys.argv:
        lic = {}
        out = main(generator=losuj_prawa(5000, ZIARNO), liczniki=lic)
        (ROOT / "wyniki" / "przyrost_wybor_praw.json").write_text(json.dumps({"ziarno": ZIARNO, "prawa": out, "odrzucenia": lic},
                                                                             ensure_ascii=False, indent=1), encoding="utf-8")
        print(out, lic)
    elif "--pilot" in sys.argv:
        from .przyrost_walidacja import PRAWA
        print(json.dumps(main(liczba=10, generator=losuj_prawa_duze(5000, 9393), zakaz_dodatkowy=PRAWA), ensure_ascii=False))
    else:
        print(json.dumps(main(), ensure_ascii=False))
