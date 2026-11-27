"""Dewelopment wariantów pod rząd 4: losowe prawa na U4 (żywe węzły-prawa), ziarna 1800–1809.
Nie używa praw S-0, praw walidacyjnych LMM ani praw walidacji rzędu 4 (_L z lmm_trening).
    python -m matylda_rdzen.heur4_dev [liczba_swiatow]
"""
from __future__ import annotations

import json
import sys
from multiprocessing import Pool

import numpy as np

from .heurystyki import HeurystykaGrafu
from .heurystyki4 import HeurystykaGrafuWsparcie
from .intuicja import HeurystykaOgolnosci, IntuicjaWyroczniaPokrycia
from .petla import uruchom
from .prawa_losowe import losuj_prawa
from .s1 import CEX, ROOT, SLOWNIK, pole
from .s1b import BUDZET_DNIA, BUDZET_SNU
from .swiat import zbuduj_swiat

POTW = "--potw" in sys.argv
SEEDS = range(1810, 1820) if POTW else range(1800, 1810)
LAMBDY = (0.5, 1.0) if POTW else (0.25, 0.5, 1.0, 2.0)


def swiaty_dev(liczba=60, ziarno=4444):
    out, widziane = [], set()
    for H in losuj_prawa(1500, ziarno):
        sw = zbuduj_swiat(H, 4, SLOWNIK)
        k = tuple(sw.world)
        if len(sw.world) >= 20 and len(sw.TR) >= 15 and k not in widziane:
            widziane.add(k)
            out.append(H)
            if len(out) >= liczba:
                break
    return out


def jeden(H):
    sw = zbuduj_swiat(H, 4, SLOWNIK)
    out = {}
    for s in SEEDS:
        ram = {"heur": HeurystykaOgolnosci(), "grafu": HeurystykaGrafu("oa+ob+kara"), "wyr": IntuicjaWyroczniaPokrycia(sw),
               **{f"wsp{l}": HeurystykaGrafuWsparcie(l) for l in LAMBDY},
               **({} if POTW else {"wsp1_bez_oa": HeurystykaGrafuWsparcie(1.0, True)})}
        res = {nm: uruchom(H, s, "S", budzet=BUDZET_DNIA, budzet_snu=BUDZET_SNU, rzad=4, slownik=SLOWNIK, cex_cap=CEX, intuicja=it)
               for nm, it in ram.items()}
        d1 = res["heur"].dziennik.koniec_dnia1
        b = min(r.wywolania for r in res.values())
        out[s] = {nm: pole(r.dziennik.krzywa, d1, b) for nm, r in res.items()}
    return H, out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 60
    L = swiaty_dev(2 * n)[n:] if POTW else swiaty_dev(n)     # potwierdzenie: kolejne n światów, nowe ziarna
    with Pool(4) as p:
        R = p.map(jeden, L)
    (ROOT / "wyniki" / ("heur4_dev_potw.json" if POTW else "heur4_dev.json")).write_text(json.dumps(R, ensure_ascii=False), encoding="utf-8")
    for x in R[0][1][SEEDS[0]]:
        if x == "grafu":
            continue
        per = np.array([np.mean([o[s][x] - o[s]["grafu"] for s in SEEDS]) for _, o in R])
        print(f"{x:12s} − grafu: śr {per.mean():+.3f} med {np.median(per):+.3f} >0 {(per > 0).mean():.2f} <0 {(per < 0).mean():.2f}")
