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
       "fazy.py", "petla.py", "pamiec.py", "swiat.py", "prawa_losowe.py", "rozmiar3_wybor_praw.py", "przyrost_wybor_praw.py",
       "heur4_dev.py", "przyrost_dev.py", "przyrost_walidacja.py", "lmm_trening.py", "heurystyki4.py")   # Z5 recenzji
NA_ANALIZE = 5      # B4: pierwsze 5 WAŻNYCH praw przedziału w kolejności generatora (z 7 prerejestrowanych)
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
 "petla.py": "45aeb52f3a31617805f380cc0c5d8e81e56e1e1d5bd45656bf50cf12d04ccac7",
 "pamiec.py": "d945cfbeb5a5e826227361a6ea6b8e455bc8df203fc85baa262c7e1516c2576b",
 "swiat.py": "f762475c1fbf7e3ba9293940f88f55a5404a9758b773b4b964cb9361f41ba103",
 "prawa_losowe.py": "8bc523cf33f01ebf75713f69533ad3b48f932a99544dbb25d89825f955c31ed1",
 "rozmiar3_wybor_praw.py": "451c355776e2134fd7c46b3a3ec65e8bfcd280c99bc7e7e54317dd2a4777a138",
 "przyrost_wybor_praw.py": "1d0b81609247516cd6a669426c0ccde5f34794d7b59214b709a152bfeb9404f0",
 "heur4_dev.py": "1cd4349bb6f8fc1569073bce935f9568959ce5faea689dc48f4edc7f605710c2",
 "przyrost_dev.py": "26dcd6113bd0d567d7f7dbe0b99a6039575c67036a2d8617f2003807480e8068",
 "przyrost_walidacja.py": "9b5ad1a80181ad022e1bc90b5ee6987eebad5318f0165dfa59317a7ef3d84506",
 "lmm_trening.py": "f234146422ea92bd2468de112826a4301a13bb9f8900dc418af44b73e69f01bb",
 "heurystyki4.py": "dcb0a4b225a2ceccfcbe5a331cc0d25fc25afb21e47351c918b40aa2a1ddd706"
}
BOOT, BOOT_ZIARNO = 10000, 12345


def status_zamrozona(tekst):
    """B1 recenzji: tylko linia statusu się liczy, nie wzmianki w tekście."""
    return re.search(r"^Status: \*\*ZAMROŻONA\*\*", tekst, flags=re.M) is not None


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


def _d(run, H, seeds):
    return roznice(run, SWIAT, H, "heur_przyrostu", "heur_grafu", seeds)


def interakcja(run, A, seeds):
    """I = średnia po prawach M1(przyrost − graf) w MAŁYCH − w DUŻYCH (A: prawa do analizy).
    (1) dokładny test permutacyjny na poziomie praw, jednostronny (I > 0), wszystkie podziały C(n_m + n_d, n_m) — kryterium (Z2);
    (2) bootstrap dwupoziomowy (prawa w przedziale, potem ziarna) — opisowo."""
    from itertools import combinations
    d = {g: [_d(run, H, seeds) for H in A[g]] for g in A}
    if not d["male"] or not d["duze"]:
        return None
    mu = {g: [x.mean() for x in d[g]] for g in d}
    est = float(np.mean(mu["male"]) - np.mean(mu["duze"]))
    wsz, nm = mu["male"] + mu["duze"], len(mu["male"])
    stat = [np.mean([wsz[i] for i in c]) - np.mean([wsz[i] for i in range(len(wsz)) if i not in c])
            for c in combinations(range(len(wsz)), nm)]
    p_perm = float(np.mean([x >= est - 1e-12 for x in stat]))
    rng = np.random.default_rng(BOOT_ZIARNO)
    bs = []
    for _ in range(BOOT):
        m = []
        for g in ("male", "duze"):
            L = d[g]
            wyb = [L[i] for i in rng.integers(0, len(L), len(L))]
            m.append(np.mean([x[rng.integers(0, len(x), len(x))].mean() for x in wyb]))
        bs.append(m[0] - m[1])
    return {"I": est, "p_perm": p_perm, "n_podzialow": len(stat), "boot_ci95": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))]}


ALFA = 0.05


def werdykt(km, kd, inter):
    """Pełna tabela km × kd × interakcja (B2, B3 recenzji). Moderacja = p_perm < ALFA."""
    mod = inter is not None and inter["p_perm"] < ALFA
    if km == "nieinformatywny":
        g = "NIEINFORMATYWNY (małe światy)"
    elif km == "gorsza":
        g = "WYNIK NEGATYWNY: heurystyka przyrostu gorsza w małych światach"
    elif km == "nierozstrzygnieta":
        g = "H_mod NIEPOTWIERDZONA: brak przewagi w małych światach"
    elif kd == "lepsza":
        g = ("WYNIK: lepsza w małych i w dużych; efekt większy w małych" if mod
             else "WYNIK: lepsza w małych i w dużych; różnica wielkości niewykazana")
    elif kd == "nieinformatywny":
        g = "WYNIK: lepsza w małych; duże nieinformatywne, moderacja niewykazana"
    elif mod:
        g = "WYNIK: lepsza w małych, nie w dużych, efekt większy w małych (moderacja rozmiarem)"
    else:
        g = "WYNIK: lepsza w małych; moderacja niewykazana"
    return g + f" (małe: {km}; duże: {kd})"


def analiza(run, P, seeds):
    out = {"kontrasty": {}, "grupy": {}, "waznosc": {}, "roznice_per_ziarno": {}}
    A = {}
    for g, lista in P.items():
        wazne_all = []
        for H in lista:
            sen, lim = waznosc(run, SWIAT, H, seeds)
            out["waznosc"][H] = {"pula_snu1": sen, "dzien_na_limicie": lim}
            if sen >= PROG_WAZNOSCI:
                wazne_all.append(H)
        wazne = wazne_all[:NA_ANALIZE]                 # B4: pierwsze 5 ważnych w kolejności generatora
        A[g] = wazne
        q = {"prawa_wazne": wazne, "rezerwowe_niewykorzystane": [H for H in lista if H not in wazne],
             "bramka_prawa": [], "lepsza": [], "gorsza": []}
        for H in wazne:
            for x, y in (("heur_przyrostu", "heur_grafu"), ("wyrocznia_przyrostu", "heur_grafu"), ("heur_przyrostu", "heurystyka"),
                         ("heur_przyrostu", "losowa"), ("heur_grafu", "heurystyka")):
                k = f"{g}|{x}-{y}|{H}"
                out["kontrasty"][k + "|pole"] = ci95(roznice(run, SWIAT, H, x, y, seeds))
                out["kontrasty"][k + "|stale_okno"] = _okno(run, SWIAT, H, x, y, seeds)
                out["kontrasty"][k + "|koncowe"] = _koniec(run, SWIAT, H, x, y, seeds)
            out["roznice_per_ziarno"][H] = [float(v) for v in _d(run, H, seeds)]       # Z3
            _, lo, hi = out["kontrasty"][f"{g}|heur_przyrostu-heur_grafu|{H}|pole"]
            if out["kontrasty"][f"{g}|wyrocznia_przyrostu-heur_grafu|{H}|pole"][1] > 0:
                q["bramka_prawa"].append(H)
            (q["lepsza"] if lo > 0 else q["gorsza"] if hi < 0 else []).append(H)
        # kategoria liczona na n = 5 analizowanych (lub mniej, jeśli ważnych < 5 → nieinformatywny przy n < 4)
        q["kategoria"] = kategoria(q["lepsza"], q["gorsza"], wazne, q["bramka_prawa"])
        out["grupy"][g] = q
    out["interakcja_male_minus_duze"] = interakcja(run, A, seeds)
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
    if set(SHA) != set(KOD) or not status_zamrozona(prer):
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
