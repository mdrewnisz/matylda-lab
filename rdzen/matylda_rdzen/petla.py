"""Pętla badacza: czuwanie → sen → przebudzenie → czuwanie … aż do wyczerpania budżetu weryfikatora."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .fazy import (DzienDodatkowy, Dziennik, GeneratorSnuNaSwiezych, Sen, SenBezKonsolidacji,
                   SenBezSmialosci, SenLosowy, SenPelny, Seed, czuwanie, kandydaci_z_obserwacji,
                   przebudzenie)
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
            "S": SenPelny(), "S-K": SenBezKonsolidacji(), "S-Ś": SenBezSmialosci(),
            "W+S": GeneratorSnuNaSwiezych(natura_swiata(sw))}[nazwa]


RAMIONA = ("A2", "W+", "S-los", "S", "S-K")             # S-0
RAMIONA_S0B = ("A2", "W+", "W+S", "S-los", "S", "S-Ś")  # S-0b


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
            intuicja: Intuicja | None = None, k: int = ILE_INTUICJI, rzad: int = 3,
            slownik: str = "baza", cex_cap: int = CEX_CAP, budzet_snu: int | None = None) -> Przebieg:
    """budzet_snu (S-1b): jeśli podany, czuwanie 1 ma limit `budzet`, a fazy po nim dostają osobno `budzet_snu` wywołań
    (łączny limit = wywołania po dniu 1 + budzet_snu). Domyślnie (None) jeden wspólny budżet, jak w S-0/S-0b/S-1."""
    sw = zbuduj_swiat(H, rzad, slownik)
    intuicja = intuicja or HeurystykaOgolnosci()
    sen = ramie(nazwa_ramienia, sw)

    # Czuwanie 1: identyczne we wszystkich ramionach i zgodne z ramieniem A2 z KG-0b.
    rng = np.random.default_rng(seed)
    okno = [int(x) for x in rng.choice(sw.world, size=min(K_WINDOW, len(sw.world)), replace=False)]
    p = Pamiec(names=list(sw.names), concepts=sw.concepts, obserwacje=list(okno))
    wer = Weryfikator(sw, cex_cap=cex_cap)
    dz = Dziennik()
    czuwanie(p, wer, kandydaci_z_obserwacji(p, okno, rng, "okno"), budzet, sw.pokrycie, dz)
    dz.koniec_dnia1 = wer.wywolania
    if budzet_snu is not None:
        budzet = wer.wywolania + budzet_snu

    rng_sen = np.random.default_rng([seed, 1])   # osobny strumień: nie zmienia czuwania 1
    seedy: list[Seed] = []
    cykl = 0
    while wer.wywolania < budzet and cykl < MAX_CYKLI:
        cykl += 1
        przed = wer.wywolania
        kandydaci = sen(p, rng_sen, intuicja, k)          # sen: bez weryfikatora
        assert wer.wywolania == przed, "sen nie może wywoływać weryfikatora"
        if cykl == 1:
            dz.pula_snu1 = list(getattr(sen, "ostatnia_pula", []))
            dz.wybrane_snu1 = list(kandydaci)
        if not kandydaci:
            break
        nowe = przebudzenie(kandydaci, H, cykl)
        seedy.extend(nowe)
        czuwanie(p, wer, kandydaci, budzet, sw.pokrycie, dz, pomijaj_wynikajace=sen.pomijaj_wynikajace)
    return Przebieg(H, seed, nazwa_ramienia, wer.wywolania, cykl, dz, p, seedy)
