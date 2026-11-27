"""Warianty heurystyki grafu pod słabość w rzędzie 4 (osobny plik: heurystyki.py jest zamrożony hashem w s0_heur).

HIPOTEZA z recenzji S-0: w x(xy)=xy (rząd 4) reguła pomija wsparcie i budzi tylko 33% prawdziwych kandydatur.
Wariant: ocena = out(a) + out(b) + λ·m·wsparcie/n − 3·[śmiałe], m = liczba klas (skala stopni), deduplikacja par klas.
"""
from __future__ import annotations

import numpy as np


class HeurystykaGrafuWsparcie:
    def __init__(self, lam=1.0, bez_oa=False):
        self.lam, self.bez_oa = lam, bez_oa
        self.nazwa = f"heur_grafu_wsp[λ={lam}{',bez_oa' if bez_oa else ''}]"

    def ocen(self, kandydaci, ctx):
        kons = ctx.konsolidacja
        F = kons.macierz_zaleznosci
        ri = {r: i for i, r in enumerate(kons.reprezentanci)}
        out = F.sum(1)
        m = max(len(ri), 1)
        n = max(ctx.liczba_znanych_magm, 1)
        sc = np.array([(0 if self.bez_oa else out[ri[kons.cls[k.a]]]) + out[ri[kons.cls[k.b]]] + self.lam * m * k.wsparcie / n
                       - (3.0 if k.zrodlo == "sen:smiale" else 0.0) for k in kandydaci], float)
        best = {}
        for i, k in enumerate(kandydaci):
            key = (kons.cls[k.a], kons.cls[k.b])
            if key not in best or sc[i] > sc[best[key]]:
                best[key] = i
        keep = set(best.values())
        return np.array([s if i in keep else s - 1e6 for i, s in enumerate(sc)])
