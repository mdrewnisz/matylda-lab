"""Dewelopment: (1) czy wyrocznia przyrostu przechodzi jako bramka na typowych światach, (2) warianty heurystyki przyrostu.
Losowe prawa (bez praw S-0 i walidacyjnych z nazwy), rząd 4 na U4 (światy 20–39 i 60–79 z heur4_dev.swiaty_dev; światy 0–119 były już widziane w dev HEUR4)
oraz rząd 3 (generator ziarno 4446). Ziarna 1900–1909 (dev), --potw: 1910–1919 na kolejnych światach.
    python -m matylda_rdzen.przyrost_dev [--potw]
"""
from __future__ import annotations

import json
import sys
from multiprocessing import Pool

import numpy as np

from .heur4_dev import swiaty_dev
from .heurystyki import HeurystykaGrafu
from .heurystyki_przyrostu import HeurystykaPrzyrostu
from .intuicja import HeurystykaOgolnosci, IntuicjaWyroczniaPokrycia
from .petla import uruchom
from .prawa_losowe import losuj_prawa
from .s0 import ci95
from .s1 import CEX, ROOT, SLOWNIK, pole
from .s1b import BUDZET_DNIA, BUDZET_SNU
from .swiat import zbuduj_swiat
from .wyrocznie import IntuicjaWyroczniaPrzyrostu

POTW = "--potw" in sys.argv
PILOT = "--pilot" in sys.argv   # B2 recenzji: pilot na klasie większych termów (prawa z przyrost_wybor_praw --pilot), m = 1 zamrożone
RUNDA2 = "--r2" in sys.argv     # druga runda wariantów na tych samych światach/ziarnach dev
SEEDS = range(2000, 2010) if PILOT else range(1910, 1920) if POTW else range(1900, 1910)


def swiaty_dev3(liczba, ziarno=4446):
    out, widziane = [], set()
    for H in losuj_prawa(3000, ziarno):
        sw = zbuduj_swiat(H, 3, SLOWNIK)
        k = tuple(sw.world)
        if len(sw.world) >= 20 and len(sw.TR) >= 15 and k not in widziane:
            widziane.add(k)
            out.append(H)
            if len(out) >= liczba:
                break
    return out


def ramiona(sw):
    if PILOT or POTW:      # potwierdzenie wybranego wariantu (m = 1, bez wag) na nowych światach i ziarnach
        return {"heur": HeurystykaOgolnosci(), "grafu": HeurystykaGrafu("oa+ob+kara"), "wyr": IntuicjaWyroczniaPokrycia(sw),
                "wyr_prz": IntuicjaWyroczniaPrzyrostu(sw), "prz_m1": HeurystykaPrzyrostu(1)}
    if RUNDA2:
        return {"heur": HeurystykaOgolnosci(), "grafu": HeurystykaGrafu("oa+ob+kara"), "prz_m1": HeurystykaPrzyrostu(1),
                "prz_m2": HeurystykaPrzyrostu(2), "prz_m2w5": HeurystykaPrzyrostu(2, waga_smialych=0.5),
                "prz_m1w5": HeurystykaPrzyrostu(1, waga_smialych=0.5)}
    return {"heur": HeurystykaOgolnosci(), "grafu": HeurystykaGrafu("oa+ob+kara"), "wyr": IntuicjaWyroczniaPokrycia(sw),
            "wyr_prz": IntuicjaWyroczniaPrzyrostu(sw), "prz_m2": HeurystykaPrzyrostu(2), "prz_m3": HeurystykaPrzyrostu(3),
            "prz_m2K": HeurystykaPrzyrostu(2, True)}


def jeden(arg):
    H, rz = arg
    sw = zbuduj_swiat(H, rz, SLOWNIK)
    out = {}
    for s in SEEDS:
        res = {nm: uruchom(H, s, "S", budzet=BUDZET_DNIA, budzet_snu=BUDZET_SNU, rzad=rz, slownik=SLOWNIK, cex_cap=CEX, intuicja=it)
               for nm, it in ramiona(sw).items()}
        d1 = res["heur"].dziennik.koniec_dnia1
        b = min(r.wywolania for r in res.values())
        out[s] = {nm: pole(r.dziennik.krzywa, d1, b) for nm, r in res.items()}
        out[s]["_pula"] = bool(res["grafu"].dziennik.pula_snu1)
    return H, rz, out


if __name__ == "__main__":
    n4, n3 = 20, 20
    if PILOT:
        L4 = L3 = [H for H, _ in json.loads((ROOT / "wyniki" / "przyrost_pilot_prawa.json").read_text(encoding="utf-8"))]
    else:
        L4 = swiaty_dev(60 + n4)[60:] if POTW else swiaty_dev(40)[20:]
        L3 = swiaty_dev3(2 * n3)[n3:] if POTW else swiaty_dev3(n3)
    with Pool(4) as p:
        R = p.map(jeden, [(H, 4) for H in L4] + [(H, 3) for H in L3])
    (ROOT / "wyniki" / ("przyrost_pilot.json" if PILOT else "przyrost_dev_potw.json" if POTW else "przyrost_dev_r2.json" if RUNDA2 else "przyrost_dev.json")).write_text(json.dumps(R, ensure_ascii=False), encoding="utf-8")
    for rz in (4, 3):
        RR = [(H, o) for H, r, o in R if r == rz]
        print(f"--- rząd {rz}: {len(RR)} światów")
        for x in [k for k in RR[0][1][SEEDS[0]] if not k.startswith("_") and k != "grafu"]:
            per, plus, minus = [], 0, 0
            for _, o in RR:
                d = np.array([o[s][x] - o[s]["grafu"] for s in SEEDS])
                _, lo, hi = ci95(d)
                per.append(d.mean()); plus += lo > 0; minus += hi < 0
            per = np.array(per)
            print(f"{x:8s} − grafu: śr {per.mean():+.3f} med {np.median(per):+.3f}  istotnie > {plus}  < {minus}")
