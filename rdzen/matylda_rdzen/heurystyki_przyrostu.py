"""Heurystyka przyrostu pokrycia na ZNANYM porządku (HIPOTEZA 13 recenzji HEUR4). Bez prawdy świata, bez weryfikatora.

Badacz szacuje porządek świata z tego, co widział: Ê = {A ⇒ B : brak kontrprzykładu wśród znanych magm, wsparcie A ≥ m}
(znane magmy = obserwacje + kontrprzykłady; m chroni przed implikacjami pustymi). Z Ê liczy klasy i redukcję przechodnią TR̂,
potem wybiera zachłannie (jak wyrocznia przyrostu) kandydatury o największym przyroście pokrycia TR̂ względem domknięcia
krawędzi już potwierdzonych. Remisy: heurystyka grafu. Śmiałe przeczucia mogą dostać karę (wariant dev).
"""
from __future__ import annotations

import numpy as np

from .heurystyki import HeurystykaGrafu
from .swiat import TOP, closure, klasy_i_redukcja
from .wyrocznie import WYSOKO, K_PACZKI, oceny_z_kolejnosci, zachlanny_przyrost


def porzadek_empiryczny(names, concepts, znane, m):
    zn = np.asarray(znane, dtype=np.int64)
    M = np.array([concepts[a][zn] for a in names])          # pojęcia × znane magmy
    sup = M.sum(1)
    imp = ~(M[:, None, :] & ~M[None, :, :]).any(2)            # imp[a, b]: brak kontrprzykładu
    E = [(names[i], names[j]) for i in range(len(names)) for j in range(len(names))
         if i != j and sup[i] >= m and sup[j] >= m and imp[i, j] and names[j] != TOP]
    return E


class HeurystykaPrzyrostu:
    def __init__(self, m=1, kara_smialych=False, waga_smialych=1.0):
        self.m, self.kara, self.ws = m, kara_smialych, waga_smialych
        self.nazwa = f"heur_przyrostu[m={m}{',K' if kara_smialych else ''}{f',ws={waga_smialych}' if waga_smialych != 1.0 else ''}]"
        self._g = HeurystykaGrafu("oa+ob+kara")

    def ocen(self, kandydaci, ctx):
        p = ctx.pamiec
        g = self._g.ocen(kandydaci, ctx)
        E = porzadek_empiryczny(p.names, p.concepts, ctx.znane_magmy, self.m)
        R, idx = closure(p.names, set(E) | set(p.prawdziwe))     # Z9: domknięcie (dla m ≥ 2 suma nie musi być przechodnia)
        D = {(a, b) for a in p.names for b in p.names if a != b and R[idx[a], idx[b]]}
        _, TRh = klasy_i_redukcja(p.names, D)
        dozw = [i for i, k in enumerate(kandydaci) if g[i] > -1e5 and not (self.kara and k.zrodlo == "sen:smiale")]
        wybor = zachlanny_przyrost(p.names, p.prawdziwe, sorted(TRh),
                                   [kandydaci[i].a for i in dozw], [kandydaci[i].b for i in dozw], g[dozw],
                                   waga=[self.ws if kandydaci[i].zrodlo == "sen:smiale" else 1.0 for i in dozw])
        return oceny_z_kolejnosci(len(kandydaci), [dozw[j] for j in wybor], g)
