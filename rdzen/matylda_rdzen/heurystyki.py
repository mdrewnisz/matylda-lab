"""Wzmocnione heurystyki portu Intuicja (po odłożeniu LMM, decyzja Michała 24.11).

Bez uczenia. Dwie zmiany względem `HeurystykaOgolnosci` (wskazane przez recenzję LMM v3):
1. deduplikacja: z kandydatur o tej samej parze klas (po konsolidacji) liczy się tylko najlepsza, reszta spada na koniec;
2. kwota śmiałych: q najlepszych śmiałych przeczuć (wg wiarygodności f_b − f_a, częstości pojęć na znanych magmach)
   trafia przed powtórkę; pozostałe śmiałe jak dotąd z karą.
"""
from __future__ import annotations

import numpy as np


class HeurystykaPlus:
    def __init__(self, dedup=True, kwota=0, smiale_ocena="fb-fa"):
        self.dedup, self.kwota, self.smiale_ocena = dedup, kwota, smiale_ocena
        self.nazwa = f"heur+{'D' if dedup else ''}Q{kwota}{'' if kwota == 0 else smiale_ocena}"

    def _f(self, ctx, nazwa):
        z = np.asarray(ctx.znane_magmy, dtype=np.int64)
        return float(ctx.pamiec.concepts[nazwa][z].mean()) if len(z) and ctx.pamiec is not None else 0.5

    def ocen(self, kandydaci, ctx):
        n = max(ctx.liczba_znanych_magm, 1)
        sc = np.array([k.wsparcie / n - (1.0 if k.zrodlo == "sen:smiale" else 0.0) for k in kandydaci], float)
        if self.kwota:
            sm = [i for i, k in enumerate(kandydaci) if k.zrodlo == "sen:smiale"]
            if sm:
                if self.smiale_ocena == "fb-fa":
                    w = np.array([self._f(ctx, kandydaci[i].b) - self._f(ctx, kandydaci[i].a) for i in sm])
                else:  # "fb"
                    w = np.array([self._f(ctx, kandydaci[i].b) for i in sm])
                w = (w + 1) / 3                                 # do [0, 2/3)
                for r, j in enumerate(np.argsort(-w, kind="stable")):
                    i = sm[j]
                    sc[i] = (2.0 + w[j]) if r < self.kwota else (-1.0 + w[j])
        if self.dedup:
            cls = ctx.konsolidacja.cls
            best = {}
            for i, k in enumerate(kandydaci):
                key = (cls[k.a], cls[k.b])
                if key not in best or sc[i] > sc[best[key]]:
                    best[key] = i
            keep = set(best.values())
            sc = np.array([s if i in keep else s - 10.0 for i, s in enumerate(sc)])
        return sc


class HeurystykaGrafu:
    """Ocena z tokenów zależności (bez uczenia): stopnie klas w znanym porządku.
    outa = ile klas wynika z klasy a, outb = ile klas wynika z klasy b, inb = ile klas implikuje b.
    Wzór wybrany na światach deweloperskich (losowe prawa, 3T/4T), nie na prawach walidacyjnych."""

    WZORY = {"oa+ob": lambda oa, ob, ib, s, sm: oa + ob,
             "oa+ob+ib": lambda oa, ob, ib, s, sm: oa + ob + ib,
             "sup+ob": lambda oa, ob, ib, s, sm: s + ob / 20,
             "oa+ob+kara": lambda oa, ob, ib, s, sm: oa + ob - (3.0 if sm else 0.0),
             "oa+ob+ib+kara": lambda oa, ob, ib, s, sm: oa + ob + ib - (3.0 if sm else 0.0)}

    def __init__(self, wzor="oa+ob", dedup=True):
        self.wzor, self.dedup = wzor, dedup
        self.nazwa = f"heur_grafu[{wzor}{',D' if dedup else ''}]"

    def ocen(self, kandydaci, ctx):
        kons = ctx.konsolidacja
        F = kons.macierz_zaleznosci
        ri = {r: i for i, r in enumerate(kons.reprezentanci)}
        out, inn = F.sum(1), F.sum(0)
        n = max(ctx.liczba_znanych_magm, 1)
        f = self.WZORY[self.wzor]
        sc = np.array([f(out[ri[kons.cls[k.a]]], out[ri[kons.cls[k.b]]], inn[ri[kons.cls[k.b]]], k.wsparcie / n,
                         k.zrodlo == "sen:smiale") for k in kandydaci], float)
        sc = sc + 1e-3 * np.array([k.wsparcie / n for k in kandydaci])      # remisy: wsparcie
        if self.dedup:
            best = {}
            for i, k in enumerate(kandydaci):
                key = (kons.cls[k.a], kons.cls[k.b])
                if key not in best or sc[i] > sc[best[key]]:
                    best[key] = i
            keep = set(best.values())
            sc = np.array([s if i in keep else s - 1e6 for i, s in enumerate(sc)])
        return sc
