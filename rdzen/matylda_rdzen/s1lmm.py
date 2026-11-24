"""S-1 LMM: ramię LMM w protokole S-1b. Uruchamiać na ziarnach 600–679 dopiero po zamrożeniu PREREJESTRACJA_S1_LMM.md.

    python -m matylda_rdzen.s1lmm              # przebieg prerejestrowany (prawa S-0, ziarna 600–679)
    python -m matylda_rdzen.s1lmm --walidacja v3  # walidacja wag v3 na prawach spoza S-0, ziarna 1520–1559 (PLAN_LMM_V3.md)
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np

from .intuicja import HeurystykaOgolnosci, IntuicjaLosowa, IntuicjaWyrocznia, IntuicjaWyroczniaPokrycia
from .lmm_intuicja import IntuicjaLMM
from .petla import uruchom
from .s0 import ci95
from .s1 import CEX, PRAWA_MOCY, ROOT, SLOWNIK, SWIATY, U4_SHA, _sha, pokr, pole, prawdziwa, trafnosc_snu1
from .s1b import BUDZET_DNIA, BUDZET_SNU, PROG_WAZNOSCI, roznice, waznosc
from .swiat import PRAWA_S0, zbuduj_swiat

SEEDS = range(600, 680)
SEEDS_WALID = {"v2": range(1440, 1480), "v3": range(1520, 1560)}   # 1300–1339: v0/v1, 1400–1419: recenzent
RAMIONA = ("losowa", "heurystyka", "lmm", "lmm_bez_grafu", "wyrocznia_pokrycia", "wyrocznia_trafnosci")
WAGI = ROOT / "dane" / "lmm_intuicja_v2.pt"
WAGI_ABL = ROOT / "dane" / "lmm_intuicja_v2_bez_grafu.pt"
WAGI_SHA = None       # uzupełniane w commicie zamrożenia
WAGI_ABL_SHA = None
KOD = ("s1lmm.py", "s1b.py", "s1.py", "intuicja.py", "lmm_intuicja.py", "lmm_bsd2_models.py", "lmm_trening.py", "uniwersum4t.py",
       "fazy.py", "petla.py", "pamiec.py", "swiat.py", "s0.py", "uniwersum4.py")


def zbierz(prawa, seeds, lmm, abl):
    run = {}
    for swiat, rz in SWIATY.items():
        for H in prawa:
            sw = zbuduj_swiat(H, rz, SLOWNIK)
            for s in seeds:
                for r in RAMIONA:
                    it = {"losowa": lambda: IntuicjaLosowa(s), "heurystyka": HeurystykaOgolnosci, "lmm": lambda: lmm, "lmm_bez_grafu": lambda: abl,
                          "wyrocznia_pokrycia": lambda: IntuicjaWyroczniaPokrycia(sw),
                          "wyrocznia_trafnosci": lambda: IntuicjaWyrocznia(sw)}[r]()
                    pr = uruchom(H, s, "S", budzet=BUDZET_DNIA, budzet_snu=BUDZET_SNU, rzad=rz, slownik=SLOWNIK,
                                 cex_cap=CEX, intuicja=it)
                    dz = pr.dziennik
                    run[(swiat, H, s, r)] = dict(
                        wyw=pr.wywolania, krzywa=dz.krzywa, d1=dz.koniec_dnia1,
                        wybrane=[(k.zrodlo, prawdziwa(sw, k.a, k.b)) for k in dz.wybrane_snu1],
                        pula=[(k.zrodlo, prawdziwa(sw, k.a, k.b)) for k in dz.pula_snu1])
    return run


def stale_okno(run, swiat, H, x, y, seeds):
    """Opisowo: pole na stałym oknie [d1, d1 + BUDZET_SNU], krzywa płaska po zatrzymaniu."""
    d = []
    for s in seeds:
        rx, ry = run[(swiat, H, s, x)], run[(swiat, H, s, y)]
        d1 = rx["d1"]
        f = lambda r: float(np.mean([pokr(r["krzywa"], t) for t in range(d1, d1 + BUDZET_SNU + 1)]))  # noqa: E731
        d.append(f(rx) - f(ry))
    return ci95(np.array(d))


def analiza(run, prawa, seeds):
    out = {"kontrasty": {}, "per_swiat": {}, "waznosc": {}, "trafnosc_snu1": {}, "wywolania": {}}
    K = out["kontrasty"]
    for swiat in SWIATY:
        wazne = [H for H in prawa if waznosc(run, swiat, H, seeds)[0] >= PROG_WAZNOSCI]
        for H in prawa:
            out["waznosc"][f"{swiat}|{H}"] = waznosc(run, swiat, H, seeds)
            for x, y in (("lmm", "heurystyka"), ("lmm", "losowa"), ("heurystyka", "losowa"),
                         ("lmm", "lmm_bez_grafu"), ("lmm_bez_grafu", "heurystyka"),
                         ("wyrocznia_pokrycia", "losowa"), ("wyrocznia_pokrycia", "heurystyka")):
                K[f"{swiat}|{x}-{y}|pole|{H}"] = ci95(roznice(run, swiat, H, x, y, seeds))
                K[f"{swiat}|{x}-{y}|stale_okno|{H}"] = stale_okno(run, swiat, H, x, y, seeds)
        P = lambda x, y, H, i: K[f"{swiat}|{x}-{y}|pole|{H}"][i]   # noqa: E731
        bram = [H for H in wazne if P("wyrocznia_pokrycia", "heurystyka", H, 1) > 0]
        luka = {H: P("wyrocznia_pokrycia", "heurystyka", H, 0) for H in prawa}
        prog = {H: 0.25 * luka[H] for H in prawa}                       # minimalny istotny efekt, per prawo
        plus = [H for H in wazne if P("lmm", "heurystyka", H, 1) > 0]
        pomij = [H for H in wazne if P("lmm", "heurystyka", H, 2) < prog[H]]
        ujem = [H for H in prawa if P("lmm", "heurystyka", H, 2) < 0]
        kat = "lepsza" if len(plus) >= 3 else "pomijalna" if len(pomij) >= 3 else "nierozstrzygnieta"
        out["per_swiat"][swiat] = {"prawa_wazne": wazne, "bramka_prawa": bram, "bramka": len(bram) >= 3,
                                   "luka_wyrocznia-heurystyka": luka, "prog_0.25_luki": prog,
                                   "lmm_dolna>0": plus, "lmm_gorna<prog": pomij, "lmm_istotnie_gorsza": ujem,
                                   "lmm_ulamek_luki": {H: (P("lmm", "heurystyka", H, 0) / luka[H] if luka[H] else None) for H in prawa},
                                   "lmm_los_dolna>0": [H for H in wazne if P("lmm", "losowa", H, 1) > 0],
                                   "kategoria_lmm": kat}
        for H in prawa:
            for r in RAMIONA:
                out["trafnosc_snu1"][f"{swiat}|{H}|{r}"] = {
                    z or "wszystkie": trafnosc_snu1(run, swiat, H, r, seeds, z) for z in (None, "sen:smiale", "sen:powtorka")}
        for r in RAMIONA:
            out["wywolania"][f"{swiat}|{r}"] = float(np.mean([run[(swiat, H, s, r)]["wyw"] for H in prawa for s in seeds]))
    Q = out["per_swiat"]
    if not all(Q[s]["bramka"] for s in SWIATY):
        g = "NIEINFORMATYWNY: brak luki wyrocznia − heurystyka w " + ", ".join(s for s in SWIATY if not Q[s]["bramka"])
    elif all(Q[s]["kategoria_lmm"] == "lepsza" for s in SWIATY):
        g = "WYNIK: LMM lepsza od heurystyki w obu światach"
    elif any(Q[s]["kategoria_lmm"] == "pomijalna" for s in SWIATY):
        g = "WYNIK NEGATYWNY: zysk LMM ponad heurystykę pomijalny (< 0,25 luki) w " + ", ".join(
            f"{s} (prawa z dolną granicą > 0: {Q[s]['lmm_dolna>0']})" for s in SWIATY if Q[s]["kategoria_lmm"] == "pomijalna")
    else:
        g = "NIEROZSTRZYGNIĘTY: " + "; ".join(f"{s}: {Q[s]['kategoria_lmm']}" for s in SWIATY)
    out["G"] = g
    return out


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "."], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"S-1 LMM: drzewo rdzen/ ma niezacommitowane zmiany:\n{dirty}")
    wyj = ROOT / "wyniki" / "s1lmm_wyniki.json"
    if wyj.exists():
        raise SystemExit(f"{wyj} już istnieje, nie nadpisuję.")
    from .uniwersum4 import PLIK, sha256 as u4sha
    if u4sha(np.load(PLIK)) != U4_SHA:
        raise SystemExit("S-1 LMM: zły hash U4.")
    lmm, abl = IntuicjaLMM(WAGI), IntuicjaLMM(WAGI_ABL)
    if (lmm.sha256, abl.sha256) != (WAGI_SHA, WAGI_ABL_SHA):
        raise SystemExit(f"S-1 LMM: wagi mają inny hash ({lmm.sha256}, {abl.sha256}).")
    run = zbierz(PRAWA_S0, SEEDS, lmm, abl)
    import torch
    wynik = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
             "prerejestracja_sha256": _sha(ROOT / "PREREJESTRACJA_S1_LMM.md"), "wagi_sha256": lmm.sha256, "wagi_bez_grafu_sha256": abl.sha256, "torch": torch.__version__,
             "kod_sha256": {f: _sha(ROOT / "matylda_rdzen" / f) for f in KOD}, **analiza(run, PRAWA_S0, SEEDS)}
    wyj.write_text(json.dumps(wynik, ensure_ascii=False, indent=1), encoding="utf-8")
    return wynik


def walidacja(v="v2"):
    lmm = IntuicjaLMM(ROOT / "dane" / f"lmm_intuicja_{v}.pt")
    abl = IntuicjaLMM(ROOT / "dane" / f"lmm_intuicja_{v}_bez_grafu.pt")
    wyj = ROOT / "wyniki" / f"lmm_walidacja_w_petli_{v}.json"
    if wyj.exists():
        raise SystemExit(f"{wyj} już istnieje, nie nadpisuję.")
    run = zbierz(PRAWA_MOCY, SEEDS_WALID[v], lmm, abl)
    out = {"wagi_sha256": lmm.sha256, "wagi_bez_grafu_sha256": abl.sha256, **analiza(run, PRAWA_MOCY, SEEDS_WALID[v])}
    wyj.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    w = walidacja(sys.argv[-1] if sys.argv[-1].startswith("v") else "v2") if "--walidacja" in sys.argv else main()
    print(json.dumps({k: w[k] for k in ("per_swiat", "G", "wywolania")}, ensure_ascii=False, indent=1))
