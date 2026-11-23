"""Pętla badacza: czuwanie → sen → przebudzenie → czuwanie … aż do wyczerpania budżetu weryfikatora."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .fazy import (DzienDodatkowy, Dziennik, Sen, SenBezKonsolidacji, SenLosowy, SenPelny, Seed,
                   czuwanie, kandydaci_z_obserwacji, przebudzenie)
from .intuicja import HeurystykaOgolnosci, Intuicja
from .pamiec import Pamiec, Weryfikator
from .swiat import Swiat, zbuduj_swiat

K_WINDOW = 20
CEX_CAP = 50
ILE_INTUICJI = 10       # ile kandydatur budzi się po jednym śnie
MAX_CYKLI = 50


def natura_swiata(sw: Swiat):
    def losuj(m: int, rng: np.random.Generator, widziane: set) -> list[int]:
        pula = np.array([x for x in sw.world if int(x) not in widziane], dtype=np.int64)
        if m <= 0 or len(pula) == 0:
            return []
        return [int(x) for x in rng.choice(pula, size=min(m, len(pula)), replace=False)]
    return losuj


def ramie(nazwa: str, sw: Swiat) -> Sen:
    return {"A2": Sen(), "W+": DzienDodatkowy(natura_swiata(sw)), "S-los": SenLosowy(),
            "S": SenPelny(), "S-K": SenBezKonsolidacji()}[nazwa]


RAMIONA = ("A2", "W+", "S-los", "S", "S-K")


@dataclass
class Przebieg:
    H: str
    seed: int
    ramie: str
    wywolania: int
    cykle: int
    dziennik: Dziennik
    pamiec: Pamiec
    seedy: list = field(default_factory=list)

    def pokrycie_przy(self, B: int) -> tuple[int, int]:
        best = (0, 0)
        for c, cov, cp in self.dziennik.krzywa:
            if c <= B:
                best = (cov, cp)
        return best


def uruchom(H: str, seed: int, nazwa_ramienia: str, budzet: int = 100,
            intuicja: Intuicja | None = None, k: int = ILE_INTUICJI) -> Przebieg:
    sw = zbuduj_swiat(H)
    intuicja = intuicja or HeurystykaOgolnosci()
    sen = ramie(nazwa_ramienia, sw)

    # Czuwanie 1: identyczne we wszystkich ramionach i zgodne z ramieniem A2 z KG-0b.
    rng = np.random.default_rng(seed)
    okno = [int(x) for x in rng.choice(sw.world, size=min(K_WINDOW, len(sw.world)), replace=False)]
    p = Pamiec(names=list(sw.names), concepts=sw.concepts, obserwacje=list(okno))
    wer = Weryfikator(sw, cex_cap=CEX_CAP)
    dz = Dziennik()
    czuwanie(p, wer, kandydaci_z_obserwacji(p, okno, rng, "okno"), budzet, sw.pokrycie, dz)

    rng_sen = np.random.default_rng([seed, 1])   # osobny strumień: nie zmienia czuwania 1
    seedy: list[Seed] = []
    cykl = 0
    while wer.wywolania < budzet and cykl < MAX_CYKLI:
        cykl += 1
        przed = wer.wywolania
        kandydaci = sen(p, rng_sen, intuicja, k)          # sen: bez weryfikatora
        assert wer.wywolania == przed, "sen nie może wywoływać weryfikatora"
        if not kandydaci:
            break
        nowe = przebudzenie(kandydaci, H, cykl)
        seedy.extend(nowe)
        czuwanie(p, wer, kandydaci, budzet, sw.pokrycie, dz, pomijaj_wynikajace=sen.pomijaj_wynikajace)
    return Przebieg(H, seed, nazwa_ramienia, wer.wywolania, cykl, dz, p, seedy)
