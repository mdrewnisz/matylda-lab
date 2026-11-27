"""Walidacja heurystyki przyrostu pokrycia z nową bramką (PREREJESTRACJA_PRZYROST.md). Jedno uruchomienie, czyste drzewo, bez nadpisywania.

    python -m matylda_rdzen.przyrost_walidacja
"""
from __future__ import annotations

import json
import subprocess

import numpy as np

from .heur4_walidacja import _koniec, _okno, kategoria
from .heurystyki import HeurystykaGrafu
from .heurystyki_przyrostu import HeurystykaPrzyrostu
from .intuicja import HeurystykaOgolnosci, IntuicjaLosowa, IntuicjaWyroczniaPokrycia
from .petla import uruchom
from .s0 import ci95
from .s1 import CEX, ROOT, SLOWNIK, SWIATY, U4_SHA, _sha
from .s1b import BUDZET_DNIA, BUDZET_SNU, PROG_WAZNOSCI, roznice, waznosc
from .swiat import zbuduj_swiat
from .wyrocznie import IntuicjaWyroczniaPrzyrostu

PRAWA = ("L:(y*(y*y))=((x*(y*x))*(y*y))", "L:(x*(z*(x*x)))=(z*(x*x))", "L:(((z*x)*x)*x)=((x*z)*x)", "L:(((x*z)*x)*(z*x))=x",
         "L:((y*x)*(y*x))=((y*x)*(y*y))")        # przyrost_wybor_praw, ziarno 9292 (klasa większych termów)
SEEDS = range(1920, 1980)
M = 1
RAMIONA = ("losowa", "heurystyka", "heur_grafu", "heur_przyrostu", "wyrocznia_przyrostu", "wyrocznia_pokrycia")
SHA = {"heurystyki.py": "", "heurystyki_przyrostu.py": "", "wyrocznie.py": ""}   # sha256, wpisywane przy zamrożeniu


def intuicja(r, s, sw):
    return {"losowa": lambda: IntuicjaLosowa(s), "heurystyka": HeurystykaOgolnosci,
            "heur_grafu": lambda: HeurystykaGrafu("oa+ob+kara"), "heur_przyrostu": lambda: HeurystykaPrzyrostu(M),
            "wyrocznia_przyrostu": lambda: IntuicjaWyroczniaPrzyrostu(sw),
            "wyrocznia_pokrycia": lambda: IntuicjaWyroczniaPokrycia(sw)}[r]()


def _komorka(arg):
    swiat, H, seeds = arg
    rz = SWIATY[swiat]
    sw = zbuduj_swiat(H, rz, SLOWNIK)
    run = {}
    for s in seeds:
        for r in RAMIONA:
            pr = uruchom(H, s, "S", budzet=BUDZET_DNIA, budzet_snu=BUDZET_SNU, rzad=rz, slownik=SLOWNIK, cex_cap=CEX,
                         intuicja=intuicja(r, s, sw))
            run[(swiat, H, s, r)] = dict(wyw=pr.wywolania, krzywa=pr.dziennik.krzywa, d1=pr.dziennik.koniec_dnia1,
                                         pula=bool(pr.dziennik.pula_snu1))
    return run


def zbierz(prawa, seeds, procesy=4):
    """Komórki (świat, prawo) równolegle; każdy przebieg deterministyczny (ziarno), więc wynik nie zależy od liczby procesów."""
    from multiprocessing import Pool
    run = {}
    with Pool(procesy) as p:
        for r in p.map(_komorka, [(sw, H, list(seeds)) for sw in SWIATY for H in prawa]):
            run.update(r)
    return run


KONTRASTY = (("heur_przyrostu", "heur_grafu"), ("wyrocznia_przyrostu", "heur_grafu"), ("heur_przyrostu", "heurystyka"),
             ("heur_przyrostu", "losowa"), ("heur_grafu", "heurystyka"), ("wyrocznia_przyrostu", "wyrocznia_pokrycia"),
             ("wyrocznia_przyrostu", "heur_przyrostu"))


def analiza(run, prawa, seeds):
    out = {"kontrasty": {}, "per_swiat": {}, "waznosc": {}}
    for swiat in SWIATY:
        wazne = []
        for H in prawa:
            sen, lim = waznosc(run, swiat, H, seeds)
            out["waznosc"][f"{swiat}|{H}"] = {"pula_snu1": sen, "dzien_na_limicie": lim}
            if sen >= PROG_WAZNOSCI:
                wazne.append(H)
        q = {"prawa_wazne": wazne, "bramka_prawa": [], "lepsza": [], "gorsza": [], "ulamek_luki_okno": {}}
        for H in wazne:
            for x, y in KONTRASTY:
                k = f"{swiat}|{x}-{y}|{H}"
                out["kontrasty"][k + "|pole"] = ci95(roznice(run, swiat, H, x, y, seeds))
                out["kontrasty"][k + "|stale_okno"] = _okno(run, swiat, H, x, y, seeds)
                out["kontrasty"][k + "|koncowe"] = _koniec(run, swiat, H, x, y, seeds)
            m, lo, hi = out["kontrasty"][f"{swiat}|heur_przyrostu-heur_grafu|{H}|pole"]
            _, glo, _ = out["kontrasty"][f"{swiat}|wyrocznia_przyrostu-heur_grafu|{H}|pole"]
            if glo > 0:
                q["bramka_prawa"].append(H)
            mo = out["kontrasty"][f"{swiat}|heur_przyrostu-heur_grafu|{H}|stale_okno"][0]
            go = out["kontrasty"][f"{swiat}|wyrocznia_przyrostu-heur_grafu|{H}|stale_okno"][0]
            q["ulamek_luki_okno"][H] = mo / go if go else None
            (q["lepsza"] if lo > 0 else q["gorsza"] if hi < 0 else []).append(H)
        q["kategoria"] = kategoria(q["lepsza"], q["gorsza"], wazne, q["bramka_prawa"])
        out["per_swiat"][swiat] = q
    k3, k4 = out["per_swiat"]["T1"]["kategoria"], out["per_swiat"]["T1-4"]["kategoria"]
    if k3 == "lepsza" and k4 == "lepsza":
        g = "WYNIK: heurystyka przyrostu lepsza od heurystyki grafu w rzędzie 3 i 4"
    elif "gorsza" in (k3, k4):
        g = "WYNIK NEGATYWNY: heurystyka przyrostu gorsza w co najmniej jednym rzędzie"
    elif "nieinformatywny" in (k3, k4) and "lepsza" not in (k3, k4):
        g = "NIEINFORMATYWNY"
    elif "lepsza" in (k3, k4):
        g = "WYNIK CZĘŚCIOWY: lepsza tylko w jednym rzędzie"
    else:
        g = "WYNIK NEGATYWNY: brak przewagi"
    out["G"] = g + f" (T1: {k3}; T1-4: {k4})"
    return out


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "."], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"drzewo rdzen/ ma niezacommitowane zmiany:\n{dirty}")
    wyj = ROOT / "wyniki" / "przyrost_walidacja.json"
    if wyj.exists():
        raise SystemExit(f"{wyj} już istnieje, nie nadpisuję.")
    if not PRAWA or not all(SHA.values()):
        raise SystemExit("prerejestracja niezamrożona (brak praw lub hashy)")
    from .uniwersum4 import PLIK, sha256 as u4sha
    if u4sha(np.load(PLIK)) != U4_SHA:
        raise SystemExit("zły hash U4")
    for f, h in SHA.items():
        if _sha(ROOT / "matylda_rdzen" / f) != h:
            raise SystemExit(f"{f} zmieniony po zamrożeniu")
    run = zbierz(PRAWA, SEEDS)
    w = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
         "prerejestracja_sha256": _sha(ROOT / "PREREJESTRACJA_PRZYROST.md"), "m": M, **analiza(run, PRAWA, SEEDS)}
    wyj.write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: w[k] for k in ("per_swiat", "G")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
