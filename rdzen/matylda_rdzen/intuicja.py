"""Port „Intuicja”: miejsce LMM w pętli badacza.

LMM jest intuicją Matyldy: działa na tokenach zależności (strukturze tego, co z czego wynika),
a nie na surowym tekście lub kodzie, i wskazuje, którą kandydaturę warto obudzić.
Do czasu wyników LMM v2 (V0/V1/V2) port wypełnia prosta heurystyka.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .pamiec import Konsolidacja


@dataclass(frozen=True)
class Kandydat:
    a: str
    b: str
    zrodlo: str          # np. "okno", "sen:powtorka", "sen:smiale", "sen:losowy", "dzien+"
    wsparcie: int        # na ilu znanych magmach przesłanka A zachodzi (bez kontrprzykładu)


@dataclass(frozen=True)
class KontekstIntuicji:
    konsolidacja: Konsolidacja   # tokeny zależności: konsolidacja.macierz_zaleznosci
    liczba_znanych_magm: int


class Intuicja(Protocol):
    nazwa: str

    def ocen(self, kandydaci: list[Kandydat], kontekst: KontekstIntuicji) -> np.ndarray:
        """Zwraca ocenę każdej kandydatury (większa = obudzić wcześniej). Nie ma dostępu do weryfikatora."""


class HeurystykaOgolnosci:
    """Ocena = wsparcie przesłanki wśród znanych magm (ogólność); śmiałe przeczucia dostają karę."""

    nazwa = "heurystyka_ogolnosci"

    def ocen(self, kandydaci, kontekst):
        n = max(kontekst.liczba_znanych_magm, 1)
        return np.array([k.wsparcie / n - (1.0 if k.zrodlo == "sen:smiale" else 0.0) for k in kandydaci])


class IntuicjaLMM:
    """Miejsce na LMM. Wejście: kontekst.konsolidacja.macierz_zaleznosci (bool N × N, porządek częściowy)
    plus para klas (A, B); wyjście: ocena kandydatury.

    Nie podpinamy prawdziwego modelu przed S-0 i przed wynikami V0/V1/V2 (Masterplan, rozdz. 0 i 9).
    Planowany adapter: koder bsd2.PosetEncoder z repo lmm, osadzenia klas → ocena krawędzi A ⇒ B.
    """

    nazwa = "lmm"

    def __init__(self, sciezka_wag: str | None = None):
        self.sciezka_wag = sciezka_wag

    def ocen(self, kandydaci, kontekst):
        raise NotImplementedError(
            "IntuicjaLMM: adapter LMM nie jest jeszcze podpięty (czeka na S-0 i V0/V1/V2). "
            "Użyj HeurystykaOgolnosci.")
