"""Eksploracja (python -m matylda_rdzen.heur_dev 120 [--plus]) i potwierdzenie (120 --potw) wariantów heurystyki na światach DEWELOPERSKICH (losowe prawa z dane/swiaty_v3.json, uniwersa 3T/4T), ziarna 1600–1609.
Prawa walidacyjne i S-0 nie są tu używane.   python -m matylda_rdzen.heur_dev
"""
from __future__ import annotations

import json
import sys
from multiprocessing import Pool

import numpy as np

from .heurystyki import HeurystykaGrafu, HeurystykaPlus
from .intuicja import HeurystykaOgolnosci, IntuicjaLosowa, IntuicjaWyroczniaPokrycia
from .lmm_trening import SWIATY_V3
from .petla import uruchom
from .s1 import CEX, ROOT, SLOWNIK, pole
from .s1b import BUDZET_DNIA, BUDZET_SNU
from .swiat import zbuduj_swiat

SEEDS = range(1620, 1630) if "--potw" in sys.argv else range(1600, 1610)
WARIANTY_G = ("sup+ob", "oa+ob+kara") if "--potw" in sys.argv else ("oa+ob", "oa+ob+ib", "sup+ob", "oa+ob+kara", "oa+ob+ib+kara")
WARIANTY = {"D": dict(dedup=True), "Q2": dict(dedup=False, kwota=2), "DQ2": dict(kwota=2), "DQ4": dict(kwota=4),
            "DQ2fb": dict(kwota=2, smiale_ocena="fb"), "DQ4fb": dict(kwota=4, smiale_ocena="fb")}


def jeden(arg):
    H, rz = arg
    sw = zbuduj_swiat(H, rz, SLOWNIK)
    out = {}
    for s in SEEDS:
        ram = {"heur": HeurystykaOgolnosci(), "los": IntuicjaLosowa(s), "wyr": IntuicjaWyroczniaPokrycia(sw),
               **({k: HeurystykaPlus(**v) for k, v in WARIANTY.items()} if "--plus" in sys.argv else {}),
               **{f"G:{w}": HeurystykaGrafu(w) for w in WARIANTY_G}}
        res = {}
        for nm, it in ram.items():
            pr = uruchom(H, s, "S", budzet=BUDZET_DNIA, budzet_snu=BUDZET_SNU, rzad=rz, slownik=SLOWNIK, cex_cap=CEX, intuicja=it)
            res[nm] = (pr.wywolania, pr.dziennik.krzywa, pr.dziennik.koniec_dnia1)
        d1 = res["heur"][2]
        b = min(r[0] for r in res.values())
        out[s] = {nm: pole(r[1], d1, b) for nm, r in res.items()}
    return H, rz, out


if __name__ == "__main__":
    L = [(H, rz) for H, rz, *_ in json.loads(SWIATY_V3.read_text(encoding="utf-8"))]
    rng = np.random.default_rng(1600)
    wyb = rng.choice(len(L), size=int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 60, replace=False)
    if "--potw" in sys.argv:          # potwierdzenie: światy NIEużyte przy wyborze wariantu, nowe ziarna 1620–1629
        L = [L[i] for i in range(len(L)) if i not in set(wyb.tolist())]
    else:
        L = [L[i] for i in sorted(wyb)]
    with Pool(4) as p:
        R = p.map(jeden, L)
    (ROOT / "wyniki" / ("heur_dev_potw.json" if "--potw" in sys.argv else "heur_dev_grafu.json")).write_text(json.dumps(R, ensure_ascii=False), encoding="utf-8")
    nm = list(R[0][2][SEEDS[0]])
    for x in nm:
        if x == "heur":
            continue
        per = np.array([np.mean([o[s][x] - o[s]["heur"] for s in SEEDS]) for _, _, o in R])
        print(f"{x:16s} − heur: średnio {per.mean():+.3f}, światy >0: {(per > 0).mean():.2f}, <0: {(per < 0).mean():.2f}")
