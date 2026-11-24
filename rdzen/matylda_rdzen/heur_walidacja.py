"""Walidacja heurystyki grafu (PLAN_HEURYSTYKA_GRAFU.md). Jedno uruchomienie, bez nadpisywania, czyste drzewo.

    python -m matylda_rdzen.heur_walidacja
"""
from __future__ import annotations

import json
import subprocess

import numpy as np

from .heurystyki import HeurystykaGrafu
from .intuicja import HeurystykaOgolnosci, IntuicjaLosowa, IntuicjaWyroczniaPokrycia
from .petla import uruchom
from .s0 import ci95
from .s1 import CEX, PRAWA_MOCY, ROOT, SLOWNIK, SWIATY, _sha
from .s1b import BUDZET_DNIA, BUDZET_SNU, PROG_WAZNOSCI, roznice, waznosc
from .swiat import zbuduj_swiat

SEEDS = range(1640, 1680)
WZOR = "oa+ob+kara"
RAMIONA = ("losowa", "heurystyka", "heur_grafu", "wyrocznia_pokrycia")


def zbierz(prawa, seeds):
    run = {}
    for swiat, rz in SWIATY.items():
        for H in prawa:
            sw = zbuduj_swiat(H, rz, SLOWNIK)
            for s in seeds:
                for r in RAMIONA:
                    it = {"losowa": lambda: IntuicjaLosowa(s), "heurystyka": HeurystykaOgolnosci,
                          "heur_grafu": lambda: HeurystykaGrafu(WZOR), "wyrocznia_pokrycia": lambda: IntuicjaWyroczniaPokrycia(sw)}[r]()
                    pr = uruchom(H, s, "S", budzet=BUDZET_DNIA, budzet_snu=BUDZET_SNU, rzad=rz, slownik=SLOWNIK, cex_cap=CEX, intuicja=it)
                    run[(swiat, H, s, r)] = dict(wyw=pr.wywolania, krzywa=pr.dziennik.krzywa, d1=pr.dziennik.koniec_dnia1,
                                                 pula=bool(pr.dziennik.pula_snu1))
    return run


def analiza(run, prawa, seeds):
    out = {"kontrasty": {}, "per_swiat": {}}
    for swiat in SWIATY:
        wazne = [H for H in prawa if waznosc(run, swiat, H, seeds)[0] >= PROG_WAZNOSCI]
        q = {"prawa_wazne": wazne, "lepsza": [], "gorsza": [], "luka": {}, "ulamek_luki": {}}
        for H in wazne:
            for x, y in (("heur_grafu", "heurystyka"), ("wyrocznia_pokrycia", "heurystyka"), ("heur_grafu", "losowa"),
                         ("heurystyka", "losowa")):
                out["kontrasty"][f"{swiat}|{x}-{y}|{H}"] = ci95(roznice(run, swiat, H, x, y, seeds))
            m, lo, hi = out["kontrasty"][f"{swiat}|heur_grafu-heurystyka|{H}"]
            g = out["kontrasty"][f"{swiat}|wyrocznia_pokrycia-heurystyka|{H}"][0]
            q["luka"][H], q["ulamek_luki"][H] = g, (m / g if g else None)
            if lo > 0:
                q["lepsza"].append(H)
            if hi < 0:
                q["gorsza"].append(H)
        out["per_swiat"][swiat] = q
    t4, t3 = out["per_swiat"]["T1-4"], out["per_swiat"]["T1"]
    g = ("WYNIK: heurystyka grafu lepsza w rzędzie 4" if len(t4["lepsza"]) >= 3 else "WYNIK NEGATYWNY w rzędzie 4 (kryterium główne)")
    g += "; T1: " + ("szkodzi (WYNIK NEGATYWNY dla rzędu 3)" if len(t3["gorsza"]) >= 3 else
                     "lepsza w ≥ 3/5" if len(t3["lepsza"]) >= 3 else "bez rozstrzygnięcia (oczekiwane ≈ 0)")
    out["G"] = g
    return out


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "."], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"drzewo rdzen/ ma niezacommitowane zmiany:\n{dirty}")
    wyj = ROOT / "wyniki" / "heur_grafu_walidacja.json"
    if wyj.exists():
        raise SystemExit(f"{wyj} już istnieje, nie nadpisuję.")
    run = zbierz(PRAWA_MOCY, SEEDS)
    w = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
         "plan_sha256": _sha(ROOT / "PLAN_HEURYSTYKA_GRAFU.md"), "wzor": WZOR, **analiza(run, PRAWA_MOCY, SEEDS)}
    wyj.write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: w[k] for k in ("per_swiat", "G")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
