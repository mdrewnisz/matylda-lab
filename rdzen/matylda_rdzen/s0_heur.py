"""Test heurystyki grafu na prawach S-0 (PREREJESTRACJA_S0_HEUR.md). Ziarna 600–679, jedno uruchomienie.

    python -m matylda_rdzen.s0_heur
Odmawia przy brudnym drzewie, istniejącym wyniku, złym hashu U4 lub zmienionej regule (sha256 heurystyki.py).
"""
from __future__ import annotations

import json
import subprocess

import numpy as np

from .heur_walidacja import RAMIONA, WZOR, zbierz
from .s0 import ci95
from .s1 import ROOT, SWIATY, U4_SHA, _sha, pokr
from .s1b import BUDZET_SNU, PROG_WAZNOSCI, roznice, waznosc
from .swiat import PRAWA_S0

SEEDS = range(600, 680)
HEUR_SHA = "bbbf3a71c2da07d94391a35c8f865ba0c99f12d53f60e7510d0075bca5ed8931"   # heurystyki.py, zamrożone
KOD = ("s0_heur.py", "heur_walidacja.py", "heurystyki.py", "intuicja.py", "fazy.py", "petla.py", "pamiec.py", "swiat.py",
       "s0.py", "s1.py", "s1b.py", "uniwersum4.py")


def _okno(run, swiat, H, x, y, seeds):
    d = []
    for s in seeds:
        rx, ry = run[(swiat, H, s, x)], run[(swiat, H, s, y)]
        d1 = rx["d1"]
        f = lambda r: float(np.mean([pokr(r["krzywa"], t) for t in range(d1, d1 + BUDZET_SNU + 1)]))  # noqa: E731
        d.append(f(rx) - f(ry))
    return ci95(np.array(d))


def _koniec(run, swiat, H, x, y, seeds):
    return ci95(np.array([run[(swiat, H, s, x)]["krzywa"][-1][1] - run[(swiat, H, s, y)]["krzywa"][-1][1] for s in seeds], float))


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
            for x, y in (("heur_grafu", "heurystyka"), ("wyrocznia_pokrycia", "heurystyka"), ("heur_grafu", "losowa"), ("heurystyka", "losowa")):
                k = f"{swiat}|{x}-{y}|{H}"
                out["kontrasty"][k + "|pole"] = ci95(roznice(run, swiat, H, x, y, seeds))
                out["kontrasty"][k + "|stale_okno"] = _okno(run, swiat, H, x, y, seeds)
                out["kontrasty"][k + "|koncowe"] = _koniec(run, swiat, H, x, y, seeds)
            m, lo, hi = out["kontrasty"][f"{swiat}|heur_grafu-heurystyka|{H}|pole"]
            g, glo, _ = out["kontrasty"][f"{swiat}|wyrocznia_pokrycia-heurystyka|{H}|pole"]
            if glo > 0:
                q["bramka_prawa"].append(H)
            q["ulamek_luki"][H] = m / g if g else None
            (q["lepsza"] if lo > 0 else q["gorsza"] if hi < 0 else []).append(H)
        q["bramka"] = len(q["bramka_prawa"]) >= 3
        q["kategoria"] = ("nieinformatywny" if not q["bramka"] or len(wazne) < 3 else
                          "lepsza" if len(q["lepsza"]) >= 3 else "gorsza" if len(q["gorsza"]) >= 3 else "nierozstrzygnieta")
        out["per_swiat"][swiat] = q
    k = [out["per_swiat"][s]["kategoria"] for s in SWIATY]
    if all(c == "lepsza" for c in k):
        g = "WYNIK: heurystyka grafu lepsza na S-0 w obu światach"
    elif "gorsza" in k:
        g = "WYNIK NEGATYWNY: heurystyka grafu gorsza na S-0 w " + ", ".join(s for s in SWIATY if out["per_swiat"][s]["kategoria"] == "gorsza")
    elif all(c == "nieinformatywny" for c in k):
        g = "NIEINFORMATYWNY"
    elif "lepsza" in k:
        g = "WYNIK CZĘŚCIOWY: lepsza tylko w " + ", ".join(s for s in SWIATY if out["per_swiat"][s]["kategoria"] == "lepsza")
    else:
        g = "WYNIK NEGATYWNY: brak przewagi na S-0 (" + ", ".join(f"{s}: {c}" for s, c in zip(SWIATY, k)) + ")"
    out["G"] = g
    return out


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "."], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"drzewo rdzen/ ma niezacommitowane zmiany:\n{dirty}")
    wyj = ROOT / "wyniki" / "s0_heur_wyniki.json"
    if wyj.exists():
        raise SystemExit(f"{wyj} już istnieje, nie nadpisuję.")
    from .uniwersum4 import PLIK, sha256 as u4sha
    if u4sha(np.load(PLIK)) != U4_SHA:
        raise SystemExit("zły hash U4")
    if _sha(ROOT / "matylda_rdzen" / "heurystyki.py") != HEUR_SHA:
        raise SystemExit("reguła zmieniona po zamrożeniu (sha256 heurystyki.py)")
    run = zbierz(PRAWA_S0, SEEDS)
    w = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
         "prerejestracja_sha256": _sha(ROOT / "PREREJESTRACJA_S0_HEUR.md"), "wzor": WZOR, "ramiona": RAMIONA,
         "kod_sha256": {f: _sha(ROOT / "matylda_rdzen" / f) for f in KOD}, **analiza(run, PRAWA_S0, SEEDS)}
    wyj.write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: w[k] for k in ("per_swiat", "G")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
