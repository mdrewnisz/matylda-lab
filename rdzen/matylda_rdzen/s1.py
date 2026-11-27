"""S-1: czy intuicja wybiera lepsze przeczucia niż przypadek? Uruchamiać dopiero po zamrożeniu PREREJESTRACJA_S1.md.

Ramiona różnią się WYŁĄCZNIE portem Intuicja (ranking kandydatur snu S). Światy T1 i T1-4 (SWIAT_T1_PROJEKT.md).

    python -m matylda_rdzen.s1            # przebieg prerejestrowany (odmawia, jeśli drzewo rdzen/ nie jest czyste)
    python -m matylda_rdzen.s1 --moc      # analiza mocy na prawach SPOZA S-0 (dozwolona przed zamrożeniem)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from .intuicja import HeurystykaOgolnosci, IntuicjaLosowa, IntuicjaWyrocznia, IntuicjaWyroczniaPokrycia
from .petla import uruchom
from .s0 import ci95
from .swiat import PRAWA_S0, zbuduj_swiat

SEEDS = range(100, 180)               # 80 ziaren na prawo; kalibracja T1 używała 0–19
SWIATY = {"T1": 3, "T1-4": 4}
SLOWNIK, CEX = "literaly", 1
B = 100
RAMIONA = ("losowa", "heurystyka", "wyrocznia_pokrycia", "wyrocznia_trafnosci")
DELTA_UL = 0.25                       # próg „efekt pomijalny” jako ułamek efektu wyroczni pokrycia (średnia po prawach)
U4_SHA = "dca6e9968ef62587d7e2c4f274771753da81800a635a71b9c9e5fbc275001e37"   # uint8, jak w PREREJESTRACJA_S0B
PRAWA_MOCY = ("elastyczna x(yx)=(xy)x", "lewa samodystr.", "prawa samodystr.", "x(xy)=xy", "(yx)x=y")
ROOT = Path(__file__).resolve().parents[1]
KOD = ("s1.py", "intuicja.py", "fazy.py", "petla.py", "pamiec.py", "swiat.py", "s0.py", "uniwersum4.py")


def intuicja(nazwa: str, seed: int, sw):
    return {"losowa": lambda: IntuicjaLosowa(seed), "heurystyka": HeurystykaOgolnosci,
            "wyrocznia_pokrycia": lambda: IntuicjaWyroczniaPokrycia(sw),
            "wyrocznia_trafnosci": lambda: IntuicjaWyrocznia(sw)}[nazwa]()


def pokr(krzywa, t):
    best = 0
    for c, cov, _ in krzywa:
        if c <= t:
            best = cov
    return best


def pole(krzywa, od, do):
    """Średnie pokrycie TR na wywołanie w przedziale [od, do] (pole pod krzywą / długość). Gdy do ≤ od: pokrycie w punkcie."""
    if do <= od:
        return float(pokr(krzywa, do))
    return float(np.mean([pokr(krzywa, t) for t in range(od, do + 1)]))


def prawdziwa(sw, a, b):
    W, c = sw.world, sw.concepts
    return not (c[a][W] & ~c[b][W]).any()


def zbierz(prawa, seeds, ramiona=RAMIONA, swiaty=SWIATY):
    run = {}
    for swiat, rz in swiaty.items():
        for H in prawa:
            sw = zbuduj_swiat(H, rz, SLOWNIK)
            for s in seeds:
                for r in ramiona:
                    pr = uruchom(H, s, "S", budzet=B, rzad=rz, slownik=SLOWNIK, cex_cap=CEX, intuicja=intuicja(r, s, sw))
                    dz = pr.dziennik
                    run[(swiat, H, s, r)] = dict(
                        wyw=pr.wywolania, krzywa=dz.krzywa, d1=dz.koniec_dnia1,
                        wybrane=[(k.zrodlo, prawdziwa(sw, k.a, k.b)) for k in dz.wybrane_snu1],
                        pula=[(k.zrodlo, prawdziwa(sw, k.a, k.b)) for k in dz.pula_snu1])
    return run


def roznice(run, swiat, H, x, y, seeds, miara="pole"):
    d = []
    for s in seeds:
        rx, ry = run[(swiat, H, s, x)], run[(swiat, H, s, y)]
        assert rx["d1"] == ry["d1"], "czuwanie 1 musi być wspólne"
        b = min(rx["wyw"], ry["wyw"], B)
        if miara == "pole":
            d.append(pole(rx["krzywa"], rx["d1"], b) - pole(ry["krzywa"], ry["d1"], b))
        elif miara == "koniec":
            d.append(pokr(rx["krzywa"], b) - pokr(ry["krzywa"], b))
        elif miara == "staly":
            d.append(pokr(rx["krzywa"], B) - pokr(ry["krzywa"], B))
    return np.array(d, float)


def trafnosc_snu1(run, swiat, H, r, seeds, zrodlo=None):
    """M2: trafność k kandydatur obudzonych po PIERWSZYM śnie (pula identyczna we wszystkich ramionach) i trafność całej puli."""
    def tr(lst):
        lst = [t for z, t in lst if zrodlo is None or z == zrodlo]
        return (sum(lst), len(lst))
    w = [tr(run[(swiat, H, s, r)]["wybrane"]) for s in seeds]
    p = [tr(run[(swiat, H, s, r)]["pula"]) for s in seeds]
    sw_, nw = sum(a for a, _ in w), sum(b for _, b in w)
    sp, np_ = sum(a for a, _ in p), sum(b for _, b in p)
    return {"wybrane": [sw_, nw, sw_ / nw if nw else None], "pula": [sp, np_, sp / np_ if np_ else None]}


def analiza(run, prawa, seeds, swiaty=SWIATY):
    out = {"kontrasty": {}, "per_swiat": {}, "trafnosc_snu1": {}, "wywolania": {}}
    K = out["kontrasty"]
    for swiat in swiaty:
        for x, y in (("wyrocznia_pokrycia", "losowa"), ("heurystyka", "losowa"), ("wyrocznia_trafnosci", "losowa")):
            for miara in ("pole", "koniec", "staly"):
                for H in prawa:
                    K[f"{swiat}|{x}-{y}|{miara}|{H}"] = ci95(roznice(run, swiat, H, x, y, seeds, miara))
        bram = [H for H in prawa if K[f"{swiat}|wyrocznia_pokrycia-losowa|pole|{H}"][1] > 0]
        delta = DELTA_UL * float(np.mean([K[f"{swiat}|wyrocznia_pokrycia-losowa|pole|{H}"][0] for H in prawa]))
        g_plus = [H for H in prawa if K[f"{swiat}|heurystyka-losowa|pole|{H}"][1] > 0]
        g_pomij = [H for H in prawa if K[f"{swiat}|heurystyka-losowa|pole|{H}"][2] < delta]
        g_ujem = [H for H in prawa if K[f"{swiat}|heurystyka-losowa|pole|{H}"][2] < 0]
        kat = ("lepsza" if len(g_plus) >= 3 else "pomijalna" if len(g_pomij) >= 3 else "nierozstrzygnieta")
        out["per_swiat"][swiat] = {"bramka_prawa": bram, "bramka": len(bram) >= 3, "delta": delta,
                                   "heur_dolna>0": g_plus, "heur_gorna<delta": g_pomij, "heur_istotnie_ujemne": g_ujem,
                                   "kategoria_heurystyki": kat}
        for H in prawa:
            for r in RAMIONA:
                out["trafnosc_snu1"][f"{swiat}|{H}|{r}"] = {
                    "wszystkie": trafnosc_snu1(run, swiat, H, r, seeds),
                    "smiale": trafnosc_snu1(run, swiat, H, r, seeds, "sen:smiale"),
                    "powtorka": trafnosc_snu1(run, swiat, H, r, seeds, "sen:powtorka")}
        for r in RAMIONA:
            out["wywolania"][f"{swiat}|{r}"] = float(np.mean([run[(swiat, H, s, r)]["wyw"] for H in prawa for s in seeds]))
        out["wywolania"][f"{swiat}|dzien1"] = float(np.mean([run[(swiat, H, s, "losowa")]["d1"] for H in prawa for s in seeds]))
    P = out["per_swiat"]
    if not all(P[s]["bramka"] for s in swiaty):
        g = "NIEINFORMATYWNY: bramka nie przeszła w " + ", ".join(s for s in swiaty if not P[s]["bramka"])
    elif all(P[s]["kategoria_heurystyki"] == "lepsza" for s in swiaty):
        g = "WYNIK: heurystyka lepsza od losowej w obu światach"
    elif any(P[s]["kategoria_heurystyki"] == "pomijalna" for s in swiaty):
        g = "WYNIK NEGATYWNY: efekt heurystyki pomijalny (górna granica < δ, czyli poniżej ćwierci efektu wyroczni pokrycia) w " + ", ".join(
            f"{s} (δ = {P[s]['delta']:.2f}; prawa z dolną granicą > 0: {P[s]['heur_dolna>0']})"
            for s in swiaty if P[s]["kategoria_heurystyki"] == "pomijalna")
    else:
        g = "NIEROZSTRZYGNIĘTY: " + "; ".join(f"{s}: {P[s]['kategoria_heurystyki']}" for s in swiaty)
    out["G"] = g
    return out


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "."], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"S-1: drzewo rdzen/ ma niezacommitowane zmiany, przebieg odmówiony:\n{dirty}")
    wyj = ROOT / "wyniki" / "s1_wyniki.json"
    if wyj.exists():
        raise SystemExit(f"S-1: {wyj} już istnieje, nie nadpisuję.")
    from .uniwersum4 import PLIK, sha256 as u4sha
    u4 = u4sha(np.load(PLIK))
    if u4 != U4_SHA:
        raise SystemExit(f"S-1: uniwersum U4 ma inny hash ({u4}), przebieg odmówiony.")
    run = zbierz(PRAWA_S0, SEEDS)
    wynik = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
             "prerejestracja_sha256": _sha(ROOT / "PREREJESTRACJA_S1.md"), "u4_sha256": u4,
             "kod_sha256": {f: _sha(ROOT / "matylda_rdzen" / f) for f in KOD},
             **analiza(run, PRAWA_S0, SEEDS)}
    wyj.write_text(json.dumps(wynik, ensure_ascii=False, indent=1), encoding="utf-8")
    return wynik


def moc(n_list=(20, 40, 60, 80), seeds=range(500, 580), powt=2000):
    """Analiza mocy na prawach spoza S-0 (ziarna 500–579): jak często kryteria przechodzą dla podprób n ziaren."""
    run = zbierz(PRAWA_MOCY, seeds)
    rng = np.random.default_rng(7)
    seeds = list(seeds)
    out = {}
    for swiat in SWIATY:
        D = {(x, H, m): roznice(run, swiat, H, x, "losowa", seeds, m) for x in ("wyrocznia_pokrycia", "heurystyka")
             for H in PRAWA_MOCY for m in ("pole", "koniec")}
        for (x, H, m), d in D.items():
            out[f"{swiat}|{x}|{m}|{H}|srednia,sd"] = [float(d.mean()), float(d.std())]
        for n in n_list:
            for x in ("wyrocznia_pokrycia", "heurystyka"):
                for m in ("pole", "koniec"):
                    ok3 = 0
                    for _ in range(powt // 10):
                        idx = rng.choice(len(seeds), n, replace=False)
                        ile = sum(ci95(D[(x, H, m)][idx])[1] > 0 for H in PRAWA_MOCY)
                        ok3 += ile >= 3
                    out[f"{swiat}|{x}|{m}|n={n}|P(>=3/5)"] = ok3 / (powt // 10)
    return out


if __name__ == "__main__":
    if "--moc" in sys.argv:
        print(json.dumps(moc(), ensure_ascii=False, indent=1))
    elif "--lmm" in sys.argv:
        raise SystemExit("Ramię LMM wymaga osobnej poprawki do prerejestracji (sekcja 7).")
    else:
        w = main()
        print(json.dumps({k: w[k] for k in ("per_swiat", "G", "wywolania")}, ensure_ascii=False, indent=1))
