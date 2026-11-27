"""Walidacja wariantu ze wsparciem (PREREJESTRACJA_HEUR4.md). Jedno uruchomienie, czyste drzewo, bez nadpisywania.

    python -m matylda_rdzen.heur4_walidacja
"""
from __future__ import annotations

import json
import subprocess

import numpy as np

from .heurystyki import HeurystykaGrafu
from .heurystyki4 import HeurystykaGrafuWsparcie
from .intuicja import HeurystykaOgolnosci, IntuicjaLosowa, IntuicjaWyroczniaPokrycia
from .petla import uruchom
from .s0 import ci95
from .s1 import CEX, ROOT, SLOWNIK, SWIATY, U4_SHA, _sha, pokr
from .s1b import BUDZET_DNIA, BUDZET_SNU, PROG_WAZNOSCI, roznice, waznosc
from .swiat import zbuduj_swiat

PRAWA = ("L:(x*(x*x))=(y*(y*y))", "L:(x*(x*(y*x)))=x", "L:((y*z)*y)=((z*y)*z)", "L:(y*(x*(x*y)))=y", "L:((z*(z*x))*x)=x")
SEEDS = range(1820, 1880)
LAMBDA = 1.0
RAMIONA = ("losowa", "heurystyka", "heur_grafu", "heur_grafu_wsp", "wyrocznia_pokrycia")
H4_SHA = "dcb0a4b225a2ceccfcbe5a331cc0d25fc25afb21e47351c918b40aa2a1ddd706"   # heurystyki4.py, zamrożone
HEUR_SHA = "bbbf3a71c2da07d94391a35c8f865ba0c99f12d53f60e7510d0075bca5ed8931"   # heurystyki.py (heur_grafu, jak w S-0)
PROG_UDZIALU = 0.6


def zbierz(prawa, seeds):
    run = {}
    for swiat, rz in SWIATY.items():
        for H in prawa:
            sw = zbuduj_swiat(H, rz, SLOWNIK)
            for s in seeds:
                for r in RAMIONA:
                    it = {"losowa": lambda: IntuicjaLosowa(s), "heurystyka": HeurystykaOgolnosci,
                          "heur_grafu": lambda: HeurystykaGrafu("oa+ob+kara"), "heur_grafu_wsp": lambda: HeurystykaGrafuWsparcie(LAMBDA),
                          "wyrocznia_pokrycia": lambda: IntuicjaWyroczniaPokrycia(sw)}[r]()
                    pr = uruchom(H, s, "S", budzet=BUDZET_DNIA, budzet_snu=BUDZET_SNU, rzad=rz, slownik=SLOWNIK, cex_cap=CEX, intuicja=it)
                    run[(swiat, H, s, r)] = dict(wyw=pr.wywolania, krzywa=pr.dziennik.krzywa, d1=pr.dziennik.koniec_dnia1,
                                                 pula=bool(pr.dziennik.pula_snu1))
    return run


def _okno(run, swiat, H, x, y, seeds):
    f = lambda r: float(np.mean([pokr(r["krzywa"], t) for t in range(r["d1"], r["d1"] + BUDZET_SNU + 1)]))  # noqa: E731
    return ci95(np.array([f(run[(swiat, H, s, x)]) - f(run[(swiat, H, s, y)]) for s in seeds]))


def _koniec(run, swiat, H, x, y, seeds):
    return ci95(np.array([run[(swiat, H, s, x)]["krzywa"][-1][1] - run[(swiat, H, s, y)]["krzywa"][-1][1] for s in seeds], float))


def kategoria(lepsza, gorsza, wazne, bramka):
    """Szkoda („gorsza”) jest rozpoznawana NIEZALEŻNIE od bramki (poprawka B1 recenzji przed zamrożeniem)."""
    n = len(wazne)
    if n < 4:
        return "nieinformatywny"
    if len(gorsza) >= PROG_UDZIALU * n:
        return "gorsza"
    if len(bramka) < PROG_UDZIALU * n:
        return "nieinformatywny"
    if len(lepsza) >= PROG_UDZIALU * n:
        return "lepsza"
    return "nierozstrzygnieta"


def analiza(run, prawa, seeds):
    out = {"kontrasty": {}, "per_swiat": {}, "waznosc": {}}
    for swiat in SWIATY:
        wazne = []
        for H in prawa:
            sen, lim = waznosc(run, swiat, H, seeds)
            out["waznosc"][f"{swiat}|{H}"] = {"pula_snu1": sen, "dzien_na_limicie": lim}
            if sen >= PROG_WAZNOSCI:
                wazne.append(H)
        q = {"prawa_wazne": wazne, "bramka_prawa": [], "lepsza": [], "gorsza": [], "ulamek_luki": {}}
        for H in wazne:
            for x, y in (("heur_grafu_wsp", "heur_grafu"), ("wyrocznia_pokrycia", "heur_grafu"), ("heur_grafu", "heurystyka"),
                         ("heur_grafu_wsp", "heurystyka"), ("heur_grafu_wsp", "losowa")):
                k = f"{swiat}|{x}-{y}|{H}"
                out["kontrasty"][k + "|pole"] = ci95(roznice(run, swiat, H, x, y, seeds))
                out["kontrasty"][k + "|stale_okno"] = _okno(run, swiat, H, x, y, seeds)
                out["kontrasty"][k + "|koncowe"] = _koniec(run, swiat, H, x, y, seeds)
            m, lo, hi = out["kontrasty"][f"{swiat}|heur_grafu_wsp-heur_grafu|{H}|pole"]
            g, glo, _ = out["kontrasty"][f"{swiat}|wyrocznia_pokrycia-heur_grafu|{H}|pole"]
            if glo > 0:
                q["bramka_prawa"].append(H)
            q["ulamek_luki"][H] = m / g if g else None
            (q["lepsza"] if lo > 0 else q["gorsza"] if hi < 0 else []).append(H)
        q["kategoria"] = kategoria(q["lepsza"], q["gorsza"], wazne, q["bramka_prawa"])
        out["per_swiat"][swiat] = q
    k4, k3 = out["per_swiat"]["T1-4"]["kategoria"], out["per_swiat"]["T1"]["kategoria"]
    g = {"lepsza": "WYNIK: wariant ze wsparciem lepszy w rzędzie 4", "gorsza": "WYNIK NEGATYWNY: wariant gorszy w rzędzie 4",
         "nierozstrzygnieta": "WYNIK NEGATYWNY: brak przewagi w rzędzie 4", "nieinformatywny": "NIEINFORMATYWNY w rzędzie 4"}[k4]
    g += f"; T1: {k3}" + (" (szkodzi w rzędzie 3)" if k3 == "gorsza" else "")
    out["G"] = g
    return out


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "."], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"drzewo rdzen/ ma niezacommitowane zmiany:\n{dirty}")
    wyj = ROOT / "wyniki" / "heur4_walidacja.json"
    if wyj.exists():
        raise SystemExit(f"{wyj} już istnieje, nie nadpisuję.")
    from .uniwersum4 import PLIK, sha256 as u4sha
    if u4sha(np.load(PLIK)) != U4_SHA:
        raise SystemExit("zły hash U4")
    if _sha(ROOT / "matylda_rdzen" / "heurystyki4.py") != H4_SHA:
        raise SystemExit("wariant zmieniony po zamrożeniu (sha256 heurystyki4.py)")
    if _sha(ROOT / "matylda_rdzen" / "heurystyki.py") != HEUR_SHA:
        raise SystemExit("heurystyka grafu zmieniona (sha256 heurystyki.py)")
    run = zbierz(PRAWA, SEEDS)
    w = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
         "prerejestracja_sha256": _sha(ROOT / "PREREJESTRACJA_HEUR4.md"), "lambda": LAMBDA, **analiza(run, PRAWA, SEEDS)}
    wyj.write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: w[k] for k in ("per_swiat", "G")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
