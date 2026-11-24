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
    pamiec: object = None        # (od ramienia LMM) pamięć badacza tylko do odczytu: statusy, obalenia; bez weryfikatora
    znane_magmy: tuple = ()      # magmy, na których badacz może oceniać pojęcia (obserwacje + kontrprzykłady)


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
    """Miejsce na LMM; implementacja w `lmm_intuicja.IntuicjaLMM` (wymaga torch i pliku wag)."""

    nazwa = "lmm"

    def __init__(self, sciezka_wag: str | None = None):
        self.sciezka_wag = sciezka_wag
        self._impl = None
        if sciezka_wag is not None:
            from .lmm_intuicja import IntuicjaLMM as _Impl
            self._impl = _Impl(sciezka_wag)

    def ocen(self, kandydaci, kontekst):
        if self._impl is None:
            raise NotImplementedError("IntuicjaLMM: brak wag (podaj sciezka_wag); zob. lmm_intuicja.py")
        return self._impl.ocen(kandydaci, kontekst)


class IntuicjaLosowa:
    """S-1, ramię kontrolne: ocena losowa (wybór przeczuć na ślepo). Własny strumień losowy na przebieg."""

    nazwa = "losowa"

    def __init__(self, ziarno: int):
        self._rng = np.random.default_rng([ziarno, 2])

    def ocen(self, kandydaci, kontekst):
        return self._rng.random(len(kandydaci))


class IntuicjaWyrocznia:
    """S-1, ramię KALIBRACYJNE (nie intuicja!): wyrocznia TRAFNOŚCI. Zna prawdę świata i ocenia 1 krawędzie prawdziwe,
    0 fałszywe. To NIE jest górna granica pokrycia: prawdziwa krawędź może nie dokładać nic do TR (recenzja S-1, uwaga 4)."""

    nazwa = "wyrocznia_trafnosci"

    def __init__(self, swiat):
        self._sw = swiat

    def ocen(self, kandydaci, kontekst):
        W, c = self._sw.world, self._sw.concepts
        return np.array([float(not (c[k.a][W] & ~c[k.b][W]).any()) for k in kandydaci])


class IntuicjaWyroczniaPokrycia:
    """S-1, ramię KALIBRACYJNE (bramka): zna prawdę świata; najpierw budzi prawdziwe krawędzie leżące na redukcji
    przechodniej (para klas w TR), potem pozostałe prawdziwe, na końcu fałszywe. Mierzy, czy dobry wybór w ogóle się opłaca."""

    nazwa = "wyrocznia_pokrycia"

    def __init__(self, swiat):
        self._sw = swiat

    def ocen(self, kandydaci, kontekst):
        sw = self._sw
        W, c = sw.world, sw.concepts
        out = []
        for k in kandydaci:
            prawdziwa = not (c[k.a][W] & ~c[k.b][W]).any()
            out.append(0.0 if not prawdziwa else 2.0 if (sw.cls[k.a], sw.cls[k.b]) in sw.TR else 1.0)
        return np.array(out)
