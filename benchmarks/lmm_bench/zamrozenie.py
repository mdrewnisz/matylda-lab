"""Zamrożony sprawdzacz metryki głównej NPH* (decyzja Michała, 2026-11-28).

Metryka główna = GÓRNA granica NPH* z wynikaniem, dolna zawsze obok (decyzja z 2026-11-23).
Od 2026-11-28 zamrożone są też parametry sprawdzacza, którym te granice się liczy:

- PARAMETRY: argumenty basis.nph_star_laws_entail;
- TWEE_SHA256: wersja dowodnika zewnętrznego (twee 2.4.2) – bez niego metryka jest niedostępna,
  bo górna granica byłaby słabsza (to nie byłaby ta sama metryka);
- KOD_SHA256: hash kodu sprawdzacza (moduły z MODULY). Każda zmiana tych plików wymaga
  świadomego ponownego zamrożenia (nowa wersja WERSJA i nowy hash) – inaczej nph_zamrozone
  odmawia działania.

Każdy runner benchmarku ma liczyć NPH* przez nph_zamrozone() i zapisywać opis() w wyniku.
"""
import hashlib
import os

WERSJA = "NPH-1 (2026-11-28)"

PARAMETRY = dict(
    sizes=(2, 4, 5),          # rozmiary kontrmodeli SAT
    node_limit=50000,         # limit węzłów własnego dowodnika
    packing=True,             # pakowanie kontrmodeli (dolna granica)
    fill_free=True,           # podstawienia zmiennych wolnych w dowodniku
    extra_ops=(2, 4),         # harmonogram: wąski dowodnik, potem twee, potem szeroki
    pairs=False,              # pary kontrmodeli wyłączone (WYNIK NEGATYWNY: +0,07 za 10× koszt)
    use_twee=True,
    twee_timeout=3.0,         # sekundy na jedno prawo
    cegar=True,               # dolna granica przez pętlę kontrprzykładów (max_iter=60 w basis.py)
)

MODULY = ("terms.py", "proofcheck.py", "entail.py", "basis.py", "twee.py")
KOD_SHA256 = "8ece1804866dfde32518429aa3ab41c9ca6d8ef00e768d66bf7504285db746b1"


class ZamrozenieNaruszone(RuntimeError):
    pass


def hash_kodu() -> str:
    h = hashlib.sha256()
    d = os.path.dirname(__file__)
    for m in MODULY:
        with open(os.path.join(d, m), "rb") as f:
            h.update(m.encode() + b"\0" + f.read() + b"\0")
    return h.hexdigest()


def sprawdz() -> None:
    """Sprawdza PRZED liczeniem, że kod i twee są te same co w zamrożeniu."""
    from . import twee
    if hash_kodu() != KOD_SHA256:
        raise ZamrozenieNaruszone(
            f"kod sprawdzacza zmienił się od zamrożenia {WERSJA} (hash {hash_kodu()[:12]}…); "
            "potrzebne ponowne zamrożenie")
    if twee.TWEE_SHA256 != "75e69a47166f7f5c54facde4a8c71a33552b4cb20bdac8b7ece9536f94e07e6e":
        raise ZamrozenieNaruszone("inna wersja twee niż zamrożona")
    if twee.binary() is None:
        raise ZamrozenieNaruszone("brak twee 2.4.2 (sh narzedzia/pobierz_twee.sh); metryka niedostępna")


def nph_zamrozone(accepted: list, initial: list = ()):
    """(dolna, górna) NPH* zamrożonym sprawdzaczem. Górna = metryka główna."""
    from . import basis
    sprawdz()
    return basis.nph_star_laws_entail(accepted, initial, **PARAMETRY)


def opis() -> dict:
    return dict(wersja=WERSJA, parametry={k: list(v) if isinstance(v, tuple) else v
                                           for k, v in PARAMETRY.items()},
                kod_sha256=KOD_SHA256, twee="2.4.2")
