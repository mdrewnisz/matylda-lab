"""Pamięć badacza (graf wiedzy) i weryfikator.

Granica epistemiczna (jak w KG-0): weryfikator umie tylko obalać. Krawędź, która przetrwała,
ma status SKONTROWANA(<=|W_H|), nigdy WYNIK w sensie ogólnym. Sen nie ma dostępu do weryfikatora
i nie zmienia statusów: może tylko proponować.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .swiat import Swiat, closure

SKONTROWANA = "skontrowana"
OBALONA = "obalona"


class Weryfikator:
    """Wyczerpujące sprawdzenie A ⇒ B w świecie W_H. Koszt = 1 wywołanie. Zwraca kontrprzykłady."""

    def __init__(self, swiat: Swiat, cex_cap: int = 50):
        self._s = swiat
        self.cex_cap = cex_cap
        self.wywolania = 0

    def sprawdz(self, a: str, b: str) -> list[int]:
        self.wywolania += 1
        c = self._s.concepts
        cx = self._s.world[c[a][self._s.world] & ~c[b][self._s.world]]
        return [int(m) for m in cx[: self.cex_cap]]


@dataclass
class Pamiec:
    """Wszystko, co badacz wie. Pojęcia może oceniać tylko na magmach, które zaobserwował
    (okno, dodatkowe obserwacje dnia) albo dostał od weryfikatora jako kontrprzykłady."""

    names: list
    concepts: dict
    obserwacje: list = field(default_factory=list)
    kontrprzyklady: list = field(default_factory=list)
    status: dict = field(default_factory=dict)        # (a, b) -> SKONTROWANA | OBALONA
    genealogia: dict = field(default_factory=dict)    # (a, b) -> skąd przyszła kandydatura

    # --- percepcja: tylko na znanych magmach ---
    def maska(self, a: str, magmy) -> np.ndarray:
        return self.concepts[a][np.asarray(magmy, dtype=np.int64)]

    @property
    def prawdziwe(self) -> set:
        return {e for e, s in self.status.items() if s == SKONTROWANA}

    def rozstrzygnieta(self, a: str, b: str) -> bool:
        return (a, b) in self.status

    def obalona_za_darmo(self, a: str, b: str) -> bool:
        """Czy któryś zapamiętany kontrprzykład już obala A ⇒ B (bez wywołania weryfikatora)."""
        if not self.kontrprzyklady:
            return False
        m = np.asarray(self.kontrprzyklady, dtype=np.int64)
        return bool((self.concepts[a][m] & ~self.concepts[b][m]).any())

    def wynika(self, a: str, b: str) -> bool:
        pt = self.prawdziwe
        if not pt:
            return False
        R, idx = closure(self.names, pt)
        return bool(R[idx[a], idx[b]])

    def zapisz(self, a: str, b: str, cex: list[int], zrodlo: str) -> None:
        self.genealogia[(a, b)] = zrodlo
        if cex:
            self.status[(a, b)] = OBALONA
            known = set(self.kontrprzyklady)
            self.kontrprzyklady.extend(m for m in cex if m not in known)
        else:
            self.status[(a, b)] = SKONTROWANA

    # --- konsolidacja (sen) ---
    def konsolidacja(self) -> "Konsolidacja":
        pt = self.prawdziwe
        R, idx = closure(self.names, pt)
        cls = {a: min((b for b in self.names if R[idx[a], idx[b]] and R[idx[b], idx[a]]),
                      key=self.names.index) for a in self.names}
        reps = sorted(set(cls.values()), key=self.names.index)
        ri = {r: i for i, r in enumerate(reps)}
        M = np.zeros((len(reps), len(reps)), dtype=bool)
        for a in reps:
            for b in reps:
                if a != b and R[idx[a], idx[b]]:
                    M[ri[a], ri[b]] = True
        return Konsolidacja(cls=cls, reprezentanci=reps, macierz_zaleznosci=M, R=R, idx=idx)


@dataclass
class Konsolidacja:
    """Graf wiedzy po konsolidacji: klasy równoważności pojęć i ścisły porządek częściowy między nimi.
    macierz_zaleznosci[i, j] = True  ⇔  klasa i ⇒ klasa j (i ≠ j). To są „tokeny zależności”:
    ten sam format (bool N × N, porządek częściowy), który czyta koder LMM (bsd2.PosetEncoder)."""

    cls: dict
    reprezentanci: list
    macierz_zaleznosci: np.ndarray
    R: np.ndarray
    idx: dict

    def wynika(self, a: str, b: str) -> bool:
        return bool(self.R[self.idx[a], self.idx[b]])
