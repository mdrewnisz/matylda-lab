"""Kalibracja trudności świata (projekt T1, SWIAT_T1_PROJEKT.md). Nie porównuje ramion.

    python -m matylda_rdzen.trudnosc   # zapis do wyniki/T1_KALIBRACJA.md i t1_kalibracja.json
"""
from __future__ import annotations

from .intuicja import HeurystykaOgolnosci  # przypięta linia bazowa: wyniki sprzed 27.11 odtwarzalne

import itertools
import json
from pathlib import Path

import numpy as np

from .fazy import MIN_SUPPORT, kandydaci_z_obserwacji
from .petla import uruchom
from .swiat import PRAWA_S0, TOP, zbuduj_swiat

SEEDS = range(20)
CEX = (50, 5, 1)
SLOWNIKI = ("baza", "negacje", "literaly", "tylko_literaly")
RZEDY = (3, 4)
B = 50
ROOT = Path(__file__).resolve().parents[1]


def pomiar(H, seed, rzad, slownik, cex_cap):
    sw = zbuduj_swiat(H, rzad, slownik)
    pr = uruchom(H, seed, "A2", budzet=B, rzad=rzad, slownik=slownik, cex_cap=cex_cap, intuicja=HeurystykaOgolnosci())
    p = pr.pamiec
    kons = p.konsolidacja()
    W = sw.world
    prawda = lambda a, b: not (sw.concepts[a][W] & ~sw.concepts[b][W]).any()  # noqa: E731
    pusta = lambda a: not sw.concepts[a][W].any()  # noqa: E731

    def otwarta(a, b):
        return not p.rozstrzygnieta(a, b) and not kons.wynika(a, b) and not p.obalona_za_darmo(a, b)

    los = [(a, b) for a, b in itertools.permutations(p.names, 2) if b != TOP and otwarta(a, b)]
    znane = list(dict.fromkeys(list(p.obserwacje) + list(p.kontrprzyklady)))
    rng = np.random.default_rng(0)
    sm = [(c.a, c.b) for c in kandydaci_z_obserwacji(p, znane, rng, "s", min_support=1)
          if c.wsparcie == 1 and otwarta(c.a, c.b)]
    pw = [(c.a, c.b) for c in kandydaci_z_obserwacji(p, znane, rng, "s", min_support=MIN_SUPPORT)
          if otwarta(c.a, c.b)]
    trafn = lambda L: (sum(prawda(a, b) for a, b in L) / len(L)) if L else float("nan")  # noqa: E731
    cov = pr.pokrycie_przy(B)[0]
    return {"p_los": trafn(los), "p_los_bez_pustych": trafn([e for e in los if not pusta(e[0])]),
            "p_sm": trafn(sm), "p_pow": trafn(pw), "n_los": len(los), "n_sm": len(sm), "n_pow": len(pw),
            "TR": len(sw.TR), "pokrycie_dnia": cov / max(len(sw.TR), 1), "wywolania_dnia": pr.wywolania}


def main():
    wyn = {}
    for rz, sl, cx in itertools.product(RZEDY, SLOWNIKI, CEX):
        rows = [pomiar(H, s, rz, sl, cx) for H in PRAWA_S0 for s in SEEDS]
        agg = {k: float(np.nanmean([r[k] for r in rows])) for k in rows[0]}
        per = {H: {k: float(np.nanmean([r[k] for r in rows[i * 20:(i + 1) * 20]])) for k in ("p_los", "p_sm", "n_sm", "pokrycie_dnia")}
               for i, H in enumerate(PRAWA_S0)}
        ok = (agg["p_los"] <= 0.30 and agg["p_sm"] <= 0.50 and agg["p_sm"] >= 0.05 and agg["n_sm"] >= 20
              and agg["pokrycie_dnia"] <= 0.60 and agg["TR"] >= 15)
        wyn[f"rzad={rz}|slownik={sl}|cex={cx}"] = {"srednie": agg, "per_prawo": per, "spelnia": ok}
        print(rz, sl, cx, {k: round(v, 2) for k, v in agg.items()}, ok, flush=True)
    (ROOT / "wyniki" / "t1_kalibracja.json").write_text(json.dumps(wyn, ensure_ascii=False, indent=1), encoding="utf-8")
    L = ["# Kalibracja świata T1 (generowane przez matylda_rdzen.trudnosc)", "",
         "Średnie po 5 prawach × 20 ziarnach, po czuwaniu 1 (B = 50). Kryteria: p_los ≤ 0,30; 0,05 ≤ p_śm ≤ 0,50; pula śmiałych ≥ 20; "
         "pokrycie dnia ≤ 0,60; |TR| ≥ 15.", "",
         "| Rząd | Słownik | cex | p_los | p_los bez pustych | p_śm | p_pow | pula śm. | pula los. | |TR| | pokrycie dnia | spełnia |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in wyn.items():
        rz, sl, cx = (x.split("=")[1] for x in k.split("|")); a = v["srednie"]
        L.append(f"| {rz} | {sl} | {cx} | {a['p_los']:.2f} | {a['p_los_bez_pustych']:.2f} | {a['p_sm']:.2f} | {a['p_pow']:.2f} | "
                 f"{a['n_sm']:.0f} | {a['n_los']:.0f} | {a['TR']:.0f} | {a['pokrycie_dnia']:.2f} | {'TAK' if v['spelnia'] else 'nie'} |")
    (ROOT / "wyniki" / "T1_KALIBRACJA.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
