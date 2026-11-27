"""S-1b: S-1 z osobnym budżetem snu (po wyniku S-1: w T1-4 dzień 1 zjadał wspólny budżet 100 i sen się nie odbywał).

Uruchamiać dopiero po zamrożeniu PREREJESTRACJA_S1B.md.

    python -m matylda_rdzen.s1b            # przebieg prerejestrowany (odmawia przy brudnym drzewie lub istniejących wynikach)
    python -m matylda_rdzen.s1b --moc      # analiza mocy na prawach SPOZA S-0 (dozwolona przed zamrożeniem)
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np

from .petla import uruchom
from .s0 import ci95
from .s1 import (CEX, DELTA_UL, PRAWA_MOCY, RAMIONA, ROOT, SLOWNIK, SWIATY, U4_SHA, _sha, intuicja, pokr, pole,
                 prawdziwa, trafnosc_snu1)
from .swiat import PRAWA_S0, zbuduj_swiat

SEEDS = range(800, 880)          # świeże: 100–179 S-1, 500–579 moc S-1, 600–679 LMM, 700–729 recenzja S-1
SEEDS_MOCY = range(500, 580)     # prawa spoza S-0, te same co analiza mocy S-1
BUDZET_DNIA = 300                # limit czuwania 1 (ma nie wiązać; odsetek przebiegów, w których wiąże, raportujemy)
BUDZET_SNU = 50                  # wywołania po dniu 1, osobno
PROG_WAZNOSCI = 0.9              # sen musi się odbyć (niepusta pula 1. snu) w ≥ 90% ziaren danego prawa
KOD = ("s1b.py", "s1.py", "intuicja.py", "fazy.py", "petla.py", "pamiec.py", "swiat.py", "s0.py", "uniwersum4.py")


def zbierz(prawa, seeds, ramiona=RAMIONA, swiaty=SWIATY):
    run = {}
    for swiat, rz in swiaty.items():
        for H in prawa:
            sw = zbuduj_swiat(H, rz, SLOWNIK)
            for s in seeds:
                for r in ramiona:
                    pr = uruchom(H, s, "S", budzet=BUDZET_DNIA, budzet_snu=BUDZET_SNU, rzad=rz, slownik=SLOWNIK,
                                 cex_cap=CEX, intuicja=intuicja(r, s, sw))
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
        b = min(rx["wyw"], ry["wyw"])                 # oba ≤ d1 + BUDZET_SNU
        if miara == "pole":
            d.append(pole(rx["krzywa"], rx["d1"], b) - pole(ry["krzywa"], ry["d1"], b))
        else:
            d.append(pokr(rx["krzywa"], b) - pokr(ry["krzywa"], b))
    return np.array(d, float)


def waznosc(run, swiat, H, seeds):
    """(kryterium) odsetek ziaren z niepustą pulą pierwszego snu (identyczna we wszystkich ramionach);
    (opisowo) odsetek ziaren, w których dzień 1 doszedł do limitu BUDZET_DNIA."""
    sen = float(np.mean([bool(run[(swiat, H, s, "losowa")]["pula"]) for s in seeds]))
    limit = float(np.mean([run[(swiat, H, s, "losowa")]["d1"] >= BUDZET_DNIA for s in seeds]))
    return sen, limit


def analiza(run, prawa, seeds, swiaty=SWIATY):
    out = {"kontrasty": {}, "per_swiat": {}, "trafnosc_snu1": {}, "wywolania": {}, "waznosc": {}}
    K = out["kontrasty"]
    for swiat in swiaty:
        wazne = []
        for H in prawa:
            sen, limit = waznosc(run, swiat, H, seeds)
            out["waznosc"][f"{swiat}|{H}"] = {"sen_odbyl_sie": sen, "dzien1_na_limicie": limit}
            if sen >= PROG_WAZNOSCI:
                wazne.append(H)
            for r in RAMIONA:   # opisowo: jak często budżet snu wiąże (M1 mierzy wtedy tempo w pierwszych 50 wywołaniach snu)
                out["waznosc"][f"{swiat}|{H}"][f"na_limicie_snu|{r}"] = float(np.mean(
                    [run[(swiat, H, s, r)]["wyw"] - run[(swiat, H, s, r)]["d1"] >= BUDZET_SNU for s in seeds]))
        for x, y in (("wyrocznia_pokrycia", "losowa"), ("heurystyka", "losowa"), ("wyrocznia_trafnosci", "losowa")):
            for miara in ("pole", "koniec"):
                for H in prawa:
                    K[f"{swiat}|{x}-{y}|{miara}|{H}"] = ci95(roznice(run, swiat, H, x, y, seeds, miara))
        P = lambda x, H, i: K[f"{swiat}|{x}-losowa|pole|{H}"][i]   # noqa: E731
        bram = [H for H in wazne if P("wyrocznia_pokrycia", H, 1) > 0]
        delta = DELTA_UL * float(np.mean([P("wyrocznia_pokrycia", H, 0) for H in wazne])) if wazne else float("nan")
        g_plus = [H for H in wazne if P("heurystyka", H, 1) > 0]
        g_pomij = [H for H in wazne if P("heurystyka", H, 2) < delta]
        g_ujem = [H for H in prawa if P("heurystyka", H, 2) < 0]
        g_ujem_koniec = [H for H in prawa if K[f"{swiat}|heurystyka-losowa|koniec|{H}"][2] < 0]
        kat = ("lepsza" if len(g_plus) >= 3 else "pomijalna" if len(g_pomij) >= 3 else "nierozstrzygnieta")
        out["per_swiat"][swiat] = {"prawa_wazne": wazne, "bramka_prawa": bram, "bramka": len(bram) >= 3, "delta": delta,
                                   "heur_dolna>0": g_plus, "heur_gorna<delta": g_pomij, "heur_istotnie_ujemne": g_ujem,
                                   "heur_istotnie_ujemne_koniec(opisowo)": g_ujem_koniec,
                                   "heur_ulamek_wyroczni": {H: P("heurystyka", H, 0) / P("wyrocznia_pokrycia", H, 0)
                                                            if P("wyrocznia_pokrycia", H, 0) else None for H in prawa},
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
    P_ = out["per_swiat"]
    if not all(P_[s]["bramka"] for s in swiaty):
        g = "NIEINFORMATYWNY: bramka nie przeszła w " + ", ".join(
            f"{s} (ważne prawa: {len(P_[s]['prawa_wazne'])}/5, bramka: {len(P_[s]['bramka_prawa'])})" for s in swiaty if not P_[s]["bramka"])
    elif all(P_[s]["kategoria_heurystyki"] == "lepsza" for s in swiaty):
        g = "WYNIK: heurystyka lepsza od losowej w obu światach"
    elif any(P_[s]["kategoria_heurystyki"] == "pomijalna" for s in swiaty):
        g = "WYNIK NEGATYWNY: efekt heurystyki pomijalny (górna granica < δ, poniżej ćwierci efektu wyroczni pokrycia) w " + ", ".join(
            f"{s} (δ = {P_[s]['delta']:.2f}; prawa z dolną granicą > 0: {P_[s]['heur_dolna>0']})"
            for s in swiaty if P_[s]["kategoria_heurystyki"] == "pomijalna")
    else:
        g = "NIEROZSTRZYGNIĘTY: " + "; ".join(f"{s}: {P_[s]['kategoria_heurystyki']}" for s in swiaty)
    out["G"] = g
    return out


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "."], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"S-1b: drzewo rdzen/ ma niezacommitowane zmiany, przebieg odmówiony:\n{dirty}")
    wyj = ROOT / "wyniki" / "s1b_wyniki.json"
    if wyj.exists():
        raise SystemExit(f"S-1b: {wyj} już istnieje, nie nadpisuję.")
    from .uniwersum4 import PLIK, sha256 as u4sha
    u4 = u4sha(np.load(PLIK))
    if u4 != U4_SHA:
        raise SystemExit(f"S-1b: uniwersum U4 ma inny hash ({u4}), przebieg odmówiony.")
    run = zbierz(PRAWA_S0, SEEDS)
    wynik = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
             "prerejestracja_sha256": _sha(ROOT / "PREREJESTRACJA_S1B.md"), "u4_sha256": u4,
             "kod_sha256": {f: _sha(ROOT / "matylda_rdzen" / f) for f in KOD},
             **analiza(run, PRAWA_S0, SEEDS)}
    wyj.write_text(json.dumps(wynik, ensure_ascii=False, indent=1), encoding="utf-8")
    return wynik


def moc(n_list=(20, 40, 80), powt=200):
    run = zbierz(PRAWA_MOCY, SEEDS_MOCY)
    rng = np.random.default_rng(7)
    seeds = list(SEEDS_MOCY)
    out = {}
    for swiat in SWIATY:
        for H in PRAWA_MOCY:
            out[f"{swiat}|{H}|waznosc(sen,limit_dnia)"] = waznosc(run, swiat, H, seeds)
            out[f"{swiat}|{H}|po_dniu1"] = float(np.mean([run[(swiat, H, s, "losowa")]["wyw"] - run[(swiat, H, s, "losowa")]["d1"]
                                                          for s in seeds]))
        D = {(x, H): roznice(run, swiat, H, x, "losowa", seeds) for x in ("wyrocznia_pokrycia", "heurystyka") for H in PRAWA_MOCY}
        for (x, H), d in D.items():
            out[f"{swiat}|{x}|{H}|srednia,sd"] = [float(d.mean()), float(d.std())]
        for n in n_list:
            for x in ("wyrocznia_pokrycia", "heurystyka"):
                ok = 0
                for _ in range(powt):
                    idx = rng.choice(len(seeds), n, replace=False)
                    ok += sum(ci95(D[(x, H)][idx])[1] > 0 for H in PRAWA_MOCY) >= 3
                out[f"{swiat}|{x}|n={n}|P(>=3/5)"] = ok / powt
    return out


if __name__ == "__main__":
    if "--moc" in sys.argv:
        print(json.dumps(moc(), ensure_ascii=False, indent=1))
    else:
        w = main()
        print(json.dumps({k: w[k] for k in ("per_swiat", "waznosc", "G", "wywolania")}, ensure_ascii=False, indent=1))
