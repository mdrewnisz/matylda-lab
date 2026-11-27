"""Wyrocznia przyrostu pokrycia TR: ramię KALIBRACYJNE (bramka), nie intuicja. Zastępuje `IntuicjaWyroczniaPokrycia`
jako bramkę w nowych prerejestracjach (rekomendacja recenzji HEUR4, wyniki/HEUR4_RECENZJA_PO.md §4). Starej wyroczni nie ruszamy:
używały jej wcześniejsze testy.

Zachłanna sekwencyjnie w paczce K = 10 (tyle budzi jeden sen, petla.ILE_INTUICJI): spośród PRAWDZIWYCH kandydatur bierze tę
o największym przyroście pokrycia TR świata (ta sama miara co `Swiat.pokrycie`, liczona względem domknięcia krawędzi już
potwierdzonych przez badacza), dodaje ją hipotetycznie i powtarza. Remisy (także zysk 0) rozstrzyga ocena heurystyki grafu.
Fałszywe kandydatury idą na koniec. Nie jest optimum (jeden krok w przód, nie modeluje kolejnych pul snu ani kontrprzykładów):
jest dolnym oszacowaniem sufitu. Plik zamrażany hashem przed każdą prerejestracją, która go używa.
"""
from __future__ import annotations

import numpy as np

from .heurystyki import HeurystykaGrafu
from .swiat import closure

K_PACZKI = 10
WYSOKO = 1e6


def zachlanny_przyrost(names, potwierdzone, TR, a_list, b_list, remis, k=K_PACZKI, waga=None):
    """Kolejność zachłanna: indeksy (w a_list/b_list) w kolejności wyboru, najwyżej k. TR: pary nazw (x, y).
    Przyrost dla A ⇒ B: liczba par (x, y) z TR jeszcze niepokrytych, dla których x ⇒ A i B ⇒ y w bieżącym domknięciu.
    waga (opcjonalnie, tylko heurystyki): mnożnik przyrostu dla każdej kandydatury; wyrocznia go nie używa."""
    if not a_list or not TR:
        return []
    R, idx = closure(names, potwierdzone)
    X = np.array([idx[x] for x, _ in TR])
    Y = np.array([idx[y] for _, y in TR])
    ai = np.array([idx[a] for a in a_list])
    bi = np.array([idx[b] for b in b_list])
    remis = np.asarray(remis, float)
    wolne = np.ones(len(ai), bool)
    wybor = []
    for _ in range(min(k, len(ai))):
        nie = ~R[X, Y]
        zysk = (nie[:, None] & R[X][:, ai] & R[bi][:, Y].T).sum(0).astype(float)
        if waga is not None:
            zysk = zysk * np.asarray(waga, float)
        klucz = np.where(wolne, zysk * 1e3 + remis / (1.0 + np.abs(remis).max()), -np.inf)
        j = int(np.argmax(klucz))
        wybor.append(j)
        wolne[j] = False
        a, b = ai[j], bi[j]
        R |= np.outer(R[:, a], R[b, :])
    return wybor


def oceny_z_kolejnosci(n, wybor, remis):
    """Wybrane w kolejności dostają najwyższe oceny, reszta: ocena remisowa (z ewentualnymi karami)."""
    sc = np.asarray(remis, float).copy()
    for pos, j in enumerate(wybor):
        sc[j] = WYSOKO * (1 + len(wybor) - pos)
    return sc


class IntuicjaWyroczniaPrzyrostu:
    """Ramię kalibracyjne: zna prawdę i TR świata. Patrz docstring modułu."""

    nazwa = "wyrocznia_przyrostu"

    def __init__(self, swiat):
        self._sw = swiat
        self._g = HeurystykaGrafu("oa+ob+kara")

    def ocen(self, kandydaci, ctx):
        sw = self._sw
        W, c = sw.world, sw.concepts
        g = self._g.ocen(kandydaci, ctx)
        prawdziwe = [i for i, k in enumerate(kandydaci) if not (c[k.a][W] & ~c[k.b][W]).any()]
        wybor = zachlanny_przyrost(sw.names, ctx.pamiec.prawdziwe, sorted(sw.TR),
                                   [kandydaci[i].a for i in prawdziwe], [kandydaci[i].b for i in prawdziwe], g[prawdziwe])
        remis = g.copy()
        falsz = np.ones(len(kandydaci), bool)
        falsz[prawdziwe] = False
        remis[falsz] -= 2 * WYSOKO * (K_PACZKI + 2)
        return oceny_z_kolejnosci(len(kandydaci), [prawdziwe[j] for j in wybor], remis)
