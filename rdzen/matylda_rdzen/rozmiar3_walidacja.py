"""Test rzędu 3 według rozmiaru świata (PREREJESTRACJA_ROZMIAR3.md). Jedno uruchomienie, czyste drzewo, bez nadpisywania.
Runner sprawdza przed startem: hashe plików z KOD (SHA niżej) i WŁASNY hash względem linii „RUNNER_SHA256:” w prerejestracji.

    python -m matylda_rdzen.rozmiar3_walidacja [--hashe]
"""
from __future__ import annotations

import json
import re
import subprocess

import numpy as np

from .heur4_walidacja import _koniec, _okno, kategoria
from .heurystyki import HeurystykaGrafu
from .heurystyki_przyrostu import HeurystykaPrzyrostu
from .intuicja import HeurystykaOgolnosci, IntuicjaLosowa
from .petla import uruchom
from .s0 import ci95
from .s1 import CEX, ROOT, SLOWNIK, _sha
from .s1b import BUDZET_DNIA, BUDZET_SNU, PROG_WAZNOSCI, roznice, waznosc
from .swiat import zbuduj_swiat
from .wyrocznie import IntuicjaWyroczniaPrzyrostu

SWIAT = "T1"
RZAD = 3
SEEDS = range(2010, 2070)
RAMIONA = ("losowa", "heurystyka", "heur_grafu", "heur_przyrostu", "wyrocznia_przyrostu")
PRAWA_PLIK = ROOT / "wyniki" / "rozmiar3_prawa.json"
KOD = ("heurystyki.py", "heurystyki_przyrostu.py", "wyrocznie.py", "heur4_walidacja.py", "s1b.py", "s1.py", "s0.py", "intuicja.py",
       "fazy.py", "petla.py", "pamiec.py", "swiat.py", "prawa_losowe.py", "rozmiar3_wybor_praw.py", "przyrost_wybor_praw.py")
SHA = {}
BOOT, BOOT_ZIARNO = 10000, 12345


def prawa():
    w = json.loads(PRAWA_PLIK.read_text(encoding="utf-8"))
    return {g: [x[0] for x in w["prawa"][g]] for g in ("male", "duze")}


def intuicja(r, s, sw):
    return {"losowa": lambda: IntuicjaLosowa(s), "heurystyka": HeurystykaOgolnosci,
            "heur_grafu": lambda: HeurystykaGrafu("oa+ob+kara"), "heur_przyrostu": lambda: HeurystykaPrzyrostu(1),
            "wyrocznia_przyrostu": lambda: IntuicjaWyroczniaPrzyrostu(sw)}[r]()


def _komorka(arg):
    H, seeds = arg
    sw = zbuduj_swiat(H, RZAD, SLOWNIK)
    run = {}
    for s in seeds:
        for r in RAMIONA:
            pr = uruchom(H, s, "S", budzet=BUDZET_DNIA, budzet_snu=BUDZET_SNU, rzad=RZAD, slownik=SLOWNIK, cex_cap=CEX,
                         intuicja=intuicja(r, s, sw))
            run[(SWIAT, H, s, r)] = dict(wyw=pr.wywolania, krzywa=pr.dziennik.krzywa, d1=pr.dziennik.koniec_dnia1,
                                         pula=bool(pr.dziennik.pula_snu1))
    return run


def zbierz(lista, seeds, procesy=4):
    from multiprocessing import Pool
    run = {}
    with Pool(procesy) as p:
        for r in p.map(_komorka, [(H, list(seeds)) for H in lista]):
            run.update(r)
    return run


def interakcja(run, P, seeds, wazne):
    """Średnia po prawach (M1: przyrost − graf) w małych minus w dużych; bootstrap dwupoziomowy: prawa w grupie, potem ziarna."""
    d = {g: [roznice(run, SWIAT, H, "heur_przyrostu", "heur_grafu", seeds) for H in P[g] if H in wazne] for g in P}
    if not d["male"] or not d["duze"]:
        return None
    est = float(np.mean([x.mean() for x in d["male"]]) - np.mean([x.mean() for x in d["duze"]]))
    rng = np.random.default_rng(BOOT_ZIARNO)
    bs = []
    for _ in range(BOOT):
        m = []
        for g in ("male", "duze"):
            L = d[g]
            wyb = [L[i] for i in rng.integers(0, len(L), len(L))]
            m.append(np.mean([x[rng.integers(0, len(x), len(x))].mean() for x in wyb]))
        bs.append(m[0] - m[1])
    return est, float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))


def werdykt(km, kd, inter):
    if km == "nieinformatywny":
        g = "NIEINFORMATYWNY (małe światy)"
    elif km == "gorsza":
        g = "WYNIK NEGATYWNY: heurystyka przyrostu gorsza w małych światach"
    elif km == "nierozstrzygnieta":
        g = "WYNIK NEGATYWNY dla hipotezy moderacji: brak przewagi w małych światach"
    elif inter is not None and inter[1] > 0:
        g = "WYNIK: lepsza w małych światach i efekt większy niż w dużych (moderacja rozmiarem)"
    else:
        g = "WYNIK: lepsza w małych światach; moderacja rozmiarem niewykazana"
    return g + f" (małe: {km}; duże: {kd})"


def analiza(run, P, seeds):
    out = {"kontrasty": {}, "grupy": {}, "waznosc": {}}
    wazne_all = []
    for g, lista in P.items():
        wazne = []
        for H in lista:
            sen, lim = waznosc(run, SWIAT, H, seeds)
            out["waznosc"][H] = {"pula_snu1": sen, "dzien_na_limicie": lim}
            if sen >= PROG_WAZNOSCI:
                wazne.append(H)
        q = {"prawa_wazne": wazne, "bramka_prawa": [], "lepsza": [], "gorsza": []}
        for H in wazne:
            for x, y in (("heur_przyrostu", "heur_grafu"), ("wyrocznia_przyrostu", "heur_grafu"), ("heur_przyrostu", "heurystyka"),
                         ("heur_przyrostu", "losowa"), ("heur_grafu", "heurystyka")):
                k = f"{g}|{x}-{y}|{H}"
                out["kontrasty"][k + "|pole"] = ci95(roznice(run, SWIAT, H, x, y, seeds))
                out["kontrasty"][k + "|stale_okno"] = _okno(run, SWIAT, H, x, y, seeds)
                out["kontrasty"][k + "|koncowe"] = _koniec(run, SWIAT, H, x, y, seeds)
            _, lo, hi = out["kontrasty"][f"{g}|heur_przyrostu-heur_grafu|{H}|pole"]
            if out["kontrasty"][f"{g}|wyrocznia_przyrostu-heur_grafu|{H}|pole"][1] > 0:
                q["bramka_prawa"].append(H)
            (q["lepsza"] if lo > 0 else q["gorsza"] if hi < 0 else []).append(H)
        q["kategoria"] = kategoria(q["lepsza"], q["gorsza"], wazne, q["bramka_prawa"])
        out["grupy"][g] = q
        wazne_all += wazne
    out["interakcja_male_minus_duze"] = interakcja(run, P, seeds, set(wazne_all))
    out["G"] = werdykt(out["grupy"]["male"]["kategoria"], out["grupy"]["duze"]["kategoria"], out["interakcja_male_minus_duze"])
    return out


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "."], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"drzewo rdzen/ ma niezacommitowane zmiany:\n{dirty}")
    wyj = ROOT / "wyniki" / "rozmiar3_walidacja.json"
    if wyj.exists():
        raise SystemExit(f"{wyj} już istnieje, nie nadpisuję.")
    prer = (ROOT / "PREREJESTRACJA_ROZMIAR3.md").read_text(encoding="utf-8")
    m = re.search(r"RUNNER_SHA256: `?([0-9a-f]{64})", prer)
    if not m or m.group(1) != _sha(ROOT / "matylda_rdzen" / "rozmiar3_walidacja.py"):
        raise SystemExit("runner niezgodny z hashem w prerejestracji")
    if set(SHA) != set(KOD) or "ZAMROŻONA" not in prer:
        raise SystemExit("prerejestracja niezamrożona")
    for f, h in SHA.items():
        if _sha(ROOT / "matylda_rdzen" / f) != h:
            raise SystemExit(f"{f} zmieniony po zamrożeniu")
    if "PRAWA_SHA256: " + _sha(PRAWA_PLIK) not in prer:
        raise SystemExit("lista praw niezgodna z prerejestracją")
    P = prawa()
    run = zbierz(P["male"] + P["duze"], SEEDS)
    w = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
         "prerejestracja_sha256": _sha(ROOT / "PREREJESTRACJA_ROZMIAR3.md"),
         "kod_sha256": {f: _sha(ROOT / "matylda_rdzen" / f) for f in KOD + ("rozmiar3_walidacja.py",)}, **analiza(run, P, SEEDS)}
    wyj.write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: w[k] for k in ("grupy", "interakcja_male_minus_duze", "G")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    import sys
    if "--hashe" in sys.argv:
        print(json.dumps({f: _sha(ROOT / "matylda_rdzen" / f) for f in KOD}, indent=1))
    else:
        main()
