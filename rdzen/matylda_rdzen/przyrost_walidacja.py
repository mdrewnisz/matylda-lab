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
from .s1 import CEX, ROOT, SLOWNIK, SWIATY, U4_SHA, _sha, pokr
from .s1b import BUDZET_DNIA, BUDZET_SNU, PROG_WAZNOSCI, roznice, waznosc
from .swiat import zbuduj_swiat
from .wyrocznie import IntuicjaWyroczniaPrzyrostu

PRAWA = ("L:(y*(y*y))=((x*(y*x))*(y*y))", "L:(x*(z*(x*x)))=(z*(x*x))", "L:(((z*x)*x)*x)=((x*z)*x)", "L:(((x*z)*x)*(z*x))=x",
         "L:((y*x)*(y*x))=((y*x)*(y*y))")        # przyrost_wybor_praw, ziarno 9292 (klasa większych termów)
SEEDS = range(1920, 1980)
M = 1
RAMIONA = ("losowa", "heurystyka", "heur_grafu", "heur_przyrostu", "wyrocznia_przyrostu", "wyrocznia_pokrycia")
# B1 recenzji: chronione hashem są wszystkie pliki, od których zależy przebieg i werdykt (poza samym runnerem, którego hash
# jest w prerejestracji i w wyniku). SHA wpisywane przy zamrożeniu (przyrost_walidacja --hashe).
KOD = ("heurystyki.py", "heurystyki_przyrostu.py", "wyrocznie.py", "heur4_walidacja.py", "s1b.py", "s1.py", "s0.py", "intuicja.py",
       "fazy.py", "petla.py", "pamiec.py", "swiat.py", "prawa_losowe.py", "uniwersum4.py")
SHA = {
 "heurystyki.py": "bbbf3a71c2da07d94391a35c8f865ba0c99f12d53f60e7510d0075bca5ed8931",
 "heurystyki_przyrostu.py": "fec8b2f092591414fa2f5a6eee50497974bbac992ec630cf22efa66cadfd1250",
 "wyrocznie.py": "9618877d6cbe1f032242625e49ea5a1edc0998580adc6606db11cdda59afa951",
 "heur4_walidacja.py": "3c3b8b1c54e2749241493ee56bf7aa968b4f1e365d417ce0a528f97f031da6b8",
 "s1b.py": "d35676bb28bea2ec6be210dd28cde0370c48665f327ba7d70ee9401d4fb8e3df",
 "s1.py": "9c65b6eac392b1c67f20937f225dee4291980c266b1e411bf91891d4c53b1422",
 "s0.py": "e0120cefe32f25f887b2b85cb5e62766d9d783d10d0011bbf169a951d38dc5f2",
 "intuicja.py": "47f4277862a8731acc5edc7bc50aa2ae837aabecd51f433b60c4253a79a25a2c",
 "fazy.py": "b581c4157a91993a8532bd6a31277dc5b157503cd02a30528e64ea4a5831d363",
 "petla.py": "52187ef6949ef41016449f3a690bfbd5b3224feaac1a775649c9bf464e48d2e1",
 "pamiec.py": "d945cfbeb5a5e826227361a6ea6b8e455bc8df203fc85baa262c7e1516c2576b",
 "swiat.py": "f762475c1fbf7e3ba9293940f88f55a5404a9758b773b4b964cb9361f41ba103",
 "prawa_losowe.py": "8bc523cf33f01ebf75713f69533ad3b48f932a99544dbb25d89825f955c31ed1",
 "uniwersum4.py": "2b3466444a1798b2675bfa0077f874da2312254b44c35d52e39e729ecedb27d1",
}


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


def werdykt(k3, k4):
    """Pełna tabela par kategorii (Z1 recenzji). Kategorie: lepsza / gorsza / nierozstrzygnieta / nieinformatywny."""
    k = {"T1 (rząd 3)": k3, "T1-4 (rząd 4)": k4}
    if k3 == k4 == "lepsza":
        g = "WYNIK: heurystyka przyrostu lepsza od heurystyki grafu w rzędzie 3 i 4"
    elif "gorsza" in (k3, k4):
        g = "WYNIK NEGATYWNY: gorsza w " + ", ".join(s for s, v in k.items() if v == "gorsza")
    elif "lepsza" in (k3, k4):
        g = "WYNIK CZĘŚCIOWY: lepsza tylko w " + ", ".join(s for s, v in k.items() if v == "lepsza")
    elif k3 == k4 == "nieinformatywny":
        g = "NIEINFORMATYWNY w obu rzędach"
    elif "nieinformatywny" in (k3, k4):
        g = ("WYNIK NEGATYWNY (brak przewagi) w " + ", ".join(s for s, v in k.items() if v == "nierozstrzygnieta")
             + "; NIEINFORMATYWNY w " + ", ".join(s for s, v in k.items() if v == "nieinformatywny"))
    else:
        g = "WYNIK NEGATYWNY: brak przewagi w obu rzędach"
    return g + f" (T1: {k3}; T1-4: {k4})"


def _okno_per_ziarno(run, swiat, H, x, y, seeds):
    f = lambda r: float(np.mean([pokr(r["krzywa"], t) for t in range(r["d1"], r["d1"] + BUDZET_SNU + 1)]))  # noqa: E731
    return np.array([f(run[(swiat, H, s, x)]) - f(run[(swiat, H, s, y)]) for s in seeds])


def ulamek_luki(run, swiat, H, seeds, boot=10000, ziarno=12345):
    """Część luki do zachłannej wyroczni przyrostu na stałym oknie: mean(prz − G) / mean(wyr_prz − G), CI z bootstrapu ziaren (Z2)."""
    a = _okno_per_ziarno(run, swiat, H, "heur_przyrostu", "heur_grafu", seeds)
    b = _okno_per_ziarno(run, swiat, H, "wyrocznia_przyrostu", "heur_grafu", seeds)
    if b.mean() <= 0:
        return None
    rng = np.random.default_rng(ziarno)
    idx = rng.integers(0, len(a), size=(boot, len(a)))
    mb = b[idx].mean(1)
    r = a[idx].mean(1)[mb > 0] / mb[mb > 0]
    return float(a.mean() / b.mean()), float(np.quantile(r, 0.025)), float(np.quantile(r, 0.975))


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
            q["ulamek_luki_okno"][H] = ulamek_luki(run, swiat, H, seeds)
            (q["lepsza"] if lo > 0 else q["gorsza"] if hi < 0 else []).append(H)
        q["kategoria"] = kategoria(q["lepsza"], q["gorsza"], wazne, q["bramka_prawa"])
        out["per_swiat"][swiat] = q
    k3, k4 = out["per_swiat"]["T1"]["kategoria"], out["per_swiat"]["T1-4"]["kategoria"]
    out["G"] = werdykt(k3, k4)
    return out


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "."], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"drzewo rdzen/ ma niezacommitowane zmiany:\n{dirty}")
    wyj = ROOT / "wyniki" / "przyrost_walidacja.json"
    if wyj.exists():
        raise SystemExit(f"{wyj} już istnieje, nie nadpisuję.")
    if not PRAWA or set(SHA) != set(KOD):
        raise SystemExit("prerejestracja niezamrożona (brak praw lub hashy)")
    from .uniwersum4 import PLIK, sha256 as u4sha
    if u4sha(np.load(PLIK)) != U4_SHA:
        raise SystemExit("zły hash U4")
    for f, h in SHA.items():
        if _sha(ROOT / "matylda_rdzen" / f) != h:
            raise SystemExit(f"{f} zmieniony po zamrożeniu")
    run = zbierz(PRAWA, SEEDS)
    w = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
         "prerejestracja_sha256": _sha(ROOT / "PREREJESTRACJA_PRZYROST.md"), "m": M,
         "kod_sha256": {f: _sha(ROOT / "matylda_rdzen" / f) for f in KOD + ("przyrost_walidacja.py",)}, **analiza(run, PRAWA, SEEDS)}
    wyj.write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: w[k] for k in ("per_swiat", "G")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    import sys
    if "--hashe" in sys.argv:          # do wpisania w SHA przy zamrożeniu
        print(json.dumps({f: _sha(ROOT / "matylda_rdzen" / f) for f in KOD}, indent=1))
    else:
        main()
