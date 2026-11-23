"""Trzy fazy pętli badacza: czuwanie, sen, przebudzenie.

Czuwanie ma weryfikator i (w wariancie „więcej dnia”) dostęp do nowych obserwacji.
Sen dostaje WYŁĄCZNIE pamięć: nie ma weryfikatora, świata ani prawdy podstawowej.
Przebudzenie zamienia kandydatury ze snu w seedy z genealogią; statusu nie zmienia.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .intuicja import Intuicja, Kandydat, KontekstIntuicji
from .pamiec import Pamiec, Weryfikator
from .swiat import TOP

MIN_SUPPORT = 2


# ---------------------------------------------------------------- proponujący (czuwanie)

def kandydaci_z_obserwacji(p: Pamiec, magmy, rng: np.random.Generator, zrodlo: str,
                           min_support: int = MIN_SUPPORT) -> list[Kandydat]:
    """A ⇒ B bez kontrprzykładu wśród `magmy`, wsparcie A ≥ min_support; kolejność: najogólniejsze A,
    remisy losowo. Dla okna odtwarza dokładnie proponującego z KG-0b."""
    cand = []
    for a in p.names:
        for b in p.names:
            if a == b or b == TOP:
                continue
            aw, bw = p.maska(a, magmy), p.maska(b, magmy)
            if aw.sum() >= min_support and not (aw & ~bw).any():
                cand.append((a, b, int(aw.sum())))
    tie = rng.random(len(cand))
    order = [c for _, c in sorted(zip(tie, cand), key=lambda z: (-z[1][2], z[0]))]
    return [Kandydat(a, b, zrodlo, s) for a, b, s in order]


# ---------------------------------------------------------------- czuwanie

@dataclass
class Dziennik:
    krzywa: list = field(default_factory=list)          # (wywołania, pokrycie TR, pokrycie TR podłożonych)
    obalone_za_darmo: int = 0
    pominiete_wynikajace: int = 0
    ze_snu_sprawdzone: int = 0
    ze_snu_prawdziwe: int = 0


def czuwanie(p: Pamiec, wer: Weryfikator, kolejka: list[Kandydat], budzet: int,
             ocena_pokrycia: Callable, dz: Dziennik, pomijaj_wynikajace: bool = True) -> None:
    """Sprawdza kolejkę, dopóki starcza budżetu. Pomija to, co pamięć już rozstrzyga za darmo."""
    for k in kolejka:
        if wer.wywolania >= budzet:
            return
        if p.rozstrzygnieta(k.a, k.b):
            continue
        if p.obalona_za_darmo(k.a, k.b):
            dz.obalone_za_darmo += 1
            continue
        if pomijaj_wynikajace and p.wynika(k.a, k.b):
            dz.pominiete_wynikajace += 1
            continue
        cex = wer.sprawdz(k.a, k.b)
        p.zapisz(k.a, k.b, cex, k.zrodlo)
        if k.zrodlo.startswith("sen"):
            dz.ze_snu_sprawdzone += 1
            dz.ze_snu_prawdziwe += int(not cex)
        cov, cov_p = ocena_pokrycia(p.prawdziwe)
        dz.krzywa.append((wer.wywolania, cov, cov_p))


# ---------------------------------------------------------------- sen (i jego kontrole)

class Sen:
    """Strategia fazy offline. Zwraca kandydatury do przebudzenia (najwyżej k)."""
    nazwa = "brak"
    pomijaj_wynikajace = True

    def __call__(self, p: Pamiec, rng, intuicja: Intuicja, k: int) -> list[Kandydat]:
        return []


class SenPelny(Sen):
    """S: konsolidacja → powtórka kontrprzykładów (+ śmiałe przeczucia) → przycinanie → intuicja."""
    nazwa = "S"
    konsolidacja = True
    smiale = True

    def _znane(self, p, rng):
        return list(dict.fromkeys(list(p.obserwacje) + list(p.kontrprzyklady)))

    def __call__(self, p, rng, intuicja, k):
        znane = self._znane(p, rng)
        kons = p.konsolidacja()
        pula = []
        zrodla = (("sen:powtorka", MIN_SUPPORT), ("sen:smiale", 1)) if self.smiale else (("sen:powtorka", MIN_SUPPORT),)
        for zrodlo, ms in zrodla:
            for c in kandydaci_z_obserwacji(p, znane, rng, zrodlo, min_support=ms):
                if zrodlo == "sen:smiale" and c.wsparcie != 1:
                    continue
                if p.rozstrzygnieta(c.a, c.b) or p.obalona_za_darmo(c.a, c.b):
                    continue
                if self.konsolidacja and kons.wynika(c.a, c.b):
                    continue
                pula.append(c)
        if not pula:
            return []
        oc = intuicja.ocen(pula, KontekstIntuicji(kons, len(znane)))
        tie = rng.random(len(pula))
        order = sorted(range(len(pula)), key=lambda i: (-oc[i], tie[i]))
        return [pula[i] for i in order[:k]]


class SenBezSmialosci(SenPelny):
    """S−Ś (S-0b): jak S, ale bez śmiałych przeczuć (tylko powtórka ze wsparciem ≥ 2)."""
    nazwa = "S-Ś"
    smiale = False


class GeneratorSnuNaSwiezych(SenPelny):
    """W+S (S-0b, silna kontrola): TEN SAM generator co S (konsolidacja, śmiałe przeczucia, intuicja),
    ale zamiast powtórki kontrprzykładów dostaje tyle samo świeżych losowych magm ze świata
    (dopisywanych do obserwacji, jak w W+). Izoluje wartość powtórki własnych porażek."""
    nazwa = "W+S"

    def __init__(self, natura):
        self.natura = natura

    def _znane(self, p, rng):
        widziane = set(p.obserwacje) | set(p.kontrprzyklady)
        m = len(set(p.kontrprzyklady) - set(p.obserwacje))
        p.obserwacje.extend(self.natura(m, rng, widziane))
        return list(p.obserwacje)


class SenBezKonsolidacji(SenPelny):
    """S−K: jak S, ale bez konsolidacji (nie pomija krawędzi wynikających z wiedzy, także po przebudzeniu)."""
    nazwa = "S-K"
    konsolidacja = False
    pomijaj_wynikajace = False


class SenLosowy(Sen):
    """S-los: losowe pary pojęć, przycinane tylko pamięcią kontrprzykładów."""
    nazwa = "S-los"

    def __call__(self, p, rng, intuicja, k):
        pary = [(a, b) for a in p.names for b in p.names
                if a != b and b != TOP and not p.rozstrzygnieta(a, b) and not p.obalona_za_darmo(a, b)]
        rng.shuffle(pary)
        return [Kandydat(a, b, "sen:losowy", 0) for a, b in pary[:k]]


class DzienDodatkowy(Sen):
    """W+ (kontrola, NIE sen): zamiast spać, dostaje tyle świeżych losowych magm ze świata,
    ile S mógłby powtórzyć (= liczba zapamiętanych kontrprzykładów spoza obserwacji),
    i proponuje dalej zwykłym proponującym dnia."""
    nazwa = "W+"

    def __init__(self, natura: Callable[[int, np.random.Generator, set], list[int]]):
        self.natura = natura

    def __call__(self, p, rng, intuicja, k):
        widziane = set(p.obserwacje) | set(p.kontrprzyklady)
        m = len(set(p.kontrprzyklady) - set(p.obserwacje))
        nowe = self.natura(m, rng, widziane)
        if not nowe:
            return []
        p.obserwacje.extend(nowe)
        out = []
        for c in kandydaci_z_obserwacji(p, p.obserwacje, rng, "dzien+"):
            if p.rozstrzygnieta(c.a, c.b) or p.obalona_za_darmo(c.a, c.b) or p.wynika(c.a, c.b):
                continue
            out.append(c)
            if len(out) == k:
                break
        return out


# ---------------------------------------------------------------- przebudzenie

@dataclass(frozen=True)
class Seed:
    """Intuicja po przebudzeniu: hipoteza bez domniemania poprawności (Praxis: HypothesisState.SEED)."""
    tytul: str
    a: str
    b: str
    zrodlo: str
    cykl: int
    wsparcie: int


def przebudzenie(kandydaci: list[Kandydat], H: str, cykl: int) -> list[Seed]:
    return [Seed(f"{c.a} ⇒ {c.b} (świat: magmy rzędu 3 z prawem {H})", c.a, c.b, c.zrodlo, cykl, c.wsparcie)
            for c in kandydaci]
