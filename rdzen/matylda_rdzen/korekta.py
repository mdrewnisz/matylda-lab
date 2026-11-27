"""Ponowny przebieg S-0 i S-0b po poprawkach z recenzji (POST HOC, odstępstwo od prerejestracji, jawnie).

Poprawki: (1) W+ i W+S dopasowują ŁĄCZNĄ liczbę świeżych magm do liczby unikalnych kontrprzykładów;
(2) S-los nie proponuje krawędzi wynikających z wiedzy. Dodana miara z recenzji: pokrycie przy RÓWNYM,
faktycznie zużytym budżecie (b = min(wywołania x, wywołania y, B) na ziarno), bo pętla kończy się, gdy
ramię nie ma kandydatów, i miara przy stałym B nagradza samo wydawanie budżetu.

    python -m matylda_rdzen.korekta   # zapis do rdzen/wyniki/KOREKTA_RAPORT.md i korekta_wyniki.json
"""
from __future__ import annotations

from .intuicja import HeurystykaOgolnosci  # przypięta linia bazowa: wyniki sprzed 27.11 odtwarzalne

import json
from pathlib import Path

import numpy as np

from .petla import uruchom
from .s0 import ci95
from .swiat import PRAWA_S0

SEEDS = range(20)
RAMIONA = ("A2", "W+", "W+S", "S-los", "S", "S-Ś", "S-K")
KRYTERIA = (
    ("S-0 H-sen: S > W+", 3, 50, "S", "W+"),
    ("S-0: konsolidacja (S > S-K)", 3, 50, "S", "S-K"),
    ("S-0: sen > szum (S > S-los)", 3, 50, "S", "S-los"),
    ("G1 rząd 4: S > W+", 4, 50, "S", "W+"),
    ("G2 rząd 4: S > W+S (powtórka > świeże)", 4, 50, "S", "W+S"),
    ("P1 rząd 3: S > W+S", 3, 50, "S", "W+S"),
    ("P2 rząd 4: W+S > W+", 4, 50, "W+S", "W+"),
    ("P3 rząd 4: S > S-Ś (śmiałość)", 4, 50, "S", "S-Ś"),
    ("P4 rząd 4: S > S-los przy B=100", 4, 100, "S", "S-los"),
)
ROOT = Path(__file__).resolve().parents[1]


def pokr(krzywa, b):
    best = 0
    for c, cov, _ in krzywa:
        if c <= b:
            best = cov
    return best


def main():
    run = {}
    for rz in (3, 4):
        for H in PRAWA_S0:
            for seed in SEEDS:
                for r in RAMIONA:
                    pr = uruchom(H, seed, r, budzet=100, rzad=rz, intuicja=HeurystykaOgolnosci())
                    run[(rz, H, seed, r)] = (pr.wywolania, pr.cykle, pr.dziennik.krzywa)
    out = {}
    for nazwa, rz, B, x, y in KRYTERIA:
        stal, rown, per = [], [], {}
        for H in PRAWA_S0:
            d1, d2 = [], []
            for s in SEEDS:
                cx, _, kx = run[(rz, H, s, x)]; cy, _, ky = run[(rz, H, s, y)]
                d1.append(pokr(kx, B) - pokr(ky, B))
                b = min(cx, cy, B)
                d2.append(pokr(kx, b) - pokr(ky, b))
            a1, a2 = ci95(np.array(d1, float)), ci95(np.array(d2, float))
            per[H] = {"staly_B": a1, "rowny_budzet": a2}
            stal += [H] * (a1[1] > 0); rown += [H] * (a2[1] > 0)
        neg = [H for H in PRAWA_S0 if per[H]["rowny_budzet"][2] < 0]
        out[nazwa] = {"staly_B_TAK": len(stal) >= 3, "staly_B_prawa": stal,
                      "rowny_budzet_TAK": len(rown) >= 3, "rowny_budzet_prawa": rown,
                      "rowny_budzet_istotnie_ujemne": neg, "per": per}
    wyw = {f"{rz}|{r}": float(np.mean([run[(rz, H, s, r)][0] for H in PRAWA_S0 for s in SEEDS]))
           for rz in (3, 4) for r in RAMIONA}
    cyk = {f"{rz}|{r}": float(np.mean([run[(rz, H, s, r)][1] for H in PRAWA_S0 for s in SEEDS]))
           for rz in (3, 4) for r in RAMIONA}
    (ROOT / "wyniki" / "korekta_wyniki.json").write_text(
        json.dumps({"kryteria": out, "srednie_wywolania": wyw, "srednie_cykle": cyk}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    L = ["# S-0 i S-0b po poprawkach z recenzji (POST HOC)", "",
         "Kryterium jak w prerejestracjach: dolna granica 95% CI > 0 w ≥ 3 z 5 praw. Dwie miary: przy stałym B "
         "(jak w prerejestracji) i przy równym faktycznie zużytym budżecie (miara z recenzji).", "",
         "| Kryterium | stały B | równy budżet | równy budżet: CI całkiem < 0 |", "|---|---|---|---|"]
    for k, v in out.items():
        L.append(f"| {k} | {'TAK' if v['staly_B_TAK'] else 'NIE'} ({len(v['staly_B_prawa'])}/5) | "
                 f"{'TAK' if v['rowny_budzet_TAK'] else 'NIE'} ({len(v['rowny_budzet_prawa'])}/5) | "
                 f"{', '.join(v['rowny_budzet_istotnie_ujemne']) or '—'} |")
    L += ["", "## Szczegóły: średnia różnica [95% CI]", "", "| Kryterium | Prawo | stały B | równy budżet |", "|---|---|---|---|"]
    for k, v in out.items():
        for H, d in v["per"].items():
            f = lambda t: f"{t[0]:+.2f} [{t[1]:+.2f}, {t[2]:+.2f}]"  # noqa: E731
            L.append(f"| {k} | {H} | {f(d['staly_B'])} | {f(d['rowny_budzet'])} |")
    L += ["", "## Średnie zużycie wywołań (B = 100) i cykli", "", "| Rząd | " + " | ".join(RAMIONA) + " |",
          "|---|" + "---|" * len(RAMIONA)]
    for rz in (3, 4):
        L.append(f"| {rz} | " + " | ".join(f"{wyw[f'{rz}|{r}']:.0f} ({cyk[f'{rz}|{r}']:.0f} c.)" for r in RAMIONA) + " |")
    (ROOT / "wyniki" / "KOREKTA_RAPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    for k, v in main().items():
        print(k, "| stały B:", v["staly_B_TAK"], len(v["staly_B_prawa"]), "| równy:", v["rowny_budzet_TAK"],
              len(v["rowny_budzet_prawa"]), "| ujemne:", v["rowny_budzet_istotnie_ujemne"])
