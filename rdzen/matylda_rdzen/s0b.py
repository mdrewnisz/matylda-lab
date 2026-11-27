"""S-0b: silniejsza kontrola i trudniejszy świat. Uruchamiać dopiero po zamrożeniu PREREJESTRACJA_S0B.md.

    python -m matylda_rdzen.s0b      # zapis do rdzen/wyniki/s0b_wyniki.json i S0B_RAPORT.md
"""
from __future__ import annotations

from .intuicja import HeurystykaOgolnosci  # przypięta linia bazowa: wyniki sprzed 27.11 odtwarzalne

import hashlib
import json
from pathlib import Path

import numpy as np

from .petla import RAMIONA_S0B, uruchom
from .s0 import ci95
from .swiat import PRAWA_S0, zbuduj_swiat
from .uniwersum4 import sha256 as sha_u4, wczytaj

SEEDS = range(20)
RZEDY = (3, 4)
BUDZETY = (25, 50, 100)
KONTRASTY = (("S", "W+S"), ("S", "W+"), ("W+S", "W+"), ("S", "S-Ś"), ("S", "S-los"), ("S", "A2"))
# (nazwa, rząd, B, x, y): prerejestrowane kryteria; spełnione, gdy dolna granica CI > 0 w >= 3 z 5 praw
KRYTERIA = (
    ("G1 replikacja S-0 w rzędzie 4: S > W+", 4, 50, "S", "W+"),
    ("G2 silna kontrola: powtórka porażek > świeże epizody (S > W+S)", 4, 50, "S", "W+S"),
    ("P1 to samo w rzędzie 3 (S > W+S)", 3, 50, "S", "W+S"),
    ("P2 generator snu na świeżych danych > zwykły dzień (W+S > W+)", 4, 50, "W+S", "W+"),
    ("P3 śmiałe przeczucia pomagają (S > S-Ś)", 4, 50, "S", "S-Ś"),
    ("P4 sen podnosi sufit ponad losowy przegląd (S > S-los przy B=100)", 4, 100, "S", "S-los"),
)
ROOT = Path(__file__).resolve().parents[1]


def main(out_dir: Path = ROOT / "wyniki") -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    prereg = (ROOT / "PREREJESTRACJA_S0B.md").read_bytes()
    wiersze = []
    for rz in RZEDY:
        for H in PRAWA_S0:
            sw = zbuduj_swiat(H, rz)
            for seed in SEEDS:
                for r in RAMIONA_S0B:
                    pr = uruchom(H, seed, r, budzet=max(BUDZETY), rzad=rz, intuicja=HeurystykaOgolnosci())
                    dz = pr.dziennik
                    wiersze.append({
                        "rzad": rz, "H": H, "seed": seed, "ramie": r, "TR": len(sw.TR),
                        "TR_podlozone": len(sw.TR_planted), "wywolania": pr.wywolania, "cykle": pr.cykle,
                        "pokrycie": {B: pr.pokrycie_przy(B)[0] for B in BUDZETY},
                        "pokrycie_podlozone": {B: pr.pokrycie_przy(B)[1] for B in BUDZETY},
                        "ze_snu_sprawdzone": dz.ze_snu_sprawdzone, "ze_snu_prawdziwe": dz.ze_snu_prawdziwe,
                    })
    kontr = {}
    for rz in RZEDY:
        for H in PRAWA_S0:
            for B in BUDZETY:
                for x, y in set(KONTRASTY) | {(k[3], k[4]) for k in KRYTERIA}:
                    vx = {w["seed"]: w["pokrycie"][B] for w in wiersze if (w["rzad"], w["H"], w["ramie"]) == (rz, H, x)}
                    vy = {w["seed"]: w["pokrycie"][B] for w in wiersze if (w["rzad"], w["H"], w["ramie"]) == (rz, H, y)}
                    kontr[f"{rz}|{H}|{B}|{x}-{y}"] = ci95(np.array([vx[s] - vy[s] for s in SEEDS], dtype=float))
    werdykt = {}
    for nazwa, rz, B, x, y in KRYTERIA:
        dod = [H for H in PRAWA_S0 if kontr[f"{rz}|{H}|{B}|{x}-{y}"][1] > 0]
        werdykt[nazwa] = {"spelnione": len(dod) >= 3, "prawa_z_dolna_granica_powyzej_0": dod}
    wynik = {"prerejestracja_sha256": hashlib.sha256(prereg).hexdigest(), "u4_sha256": sha_u4(wczytaj().astype(np.uint8)),
             "wiersze": wiersze, "kontrasty": kontr, "werdykt": werdykt}
    (out_dir / "s0b_wyniki.json").write_text(json.dumps(wynik, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "S0B_RAPORT.md").write_text(raport(wynik), encoding="utf-8")
    return wynik


def raport(w: dict) -> str:
    L = ["# S-0b: wynik (generowany automatycznie przez matylda_rdzen.s0b)", "",
         f"Prerejestracja sha256: `{w['prerejestracja_sha256']}`; uniwersum U4 sha256: `{w['u4_sha256']}`", "",
         "## Werdykt wg prerejestracji (kryterium: dolna granica 95% CI > 0 w ≥ 3 z 5 praw)", ""]
    for k, v in w["werdykt"].items():
        L.append(f"- **{k}**: {'TAK' if v['spelnione'] else 'NIE'} ({len(v['prawa_z_dolna_granica_powyzej_0'])}/5: "
                 f"{', '.join(v['prawa_z_dolna_granica_powyzej_0']) or '—'})")
    for rz in RZEDY:
        L += ["", f"## Rząd {rz}: średnie pokrycie redukcji przechodniej (20 ziaren)", "",
              "| Prawo | |TR| | B | " + " | ".join(RAMIONA_S0B) + " | śr. wywołania S / W+S / W+ |",
              "|---|---|---|" + "---|" * len(RAMIONA_S0B) + "---|"]
        for H in PRAWA_S0:
            rows = [x for x in w["wiersze"] if x["rzad"] == rz and x["H"] == H]
            calls = " / ".join(f"{np.mean([x['wywolania'] for x in rows if x['ramie'] == r]):.0f}" for r in ("S", "W+S", "W+"))
            for B in BUDZETY:
                cells = [f"{np.mean([x['pokrycie'][B] for x in rows if x['ramie'] == r]):.1f}" for r in RAMIONA_S0B]
                L.append(f"| {H} | {rows[0]['TR']} | {B} | " + " | ".join(cells) + f" | {calls if B == 100 else ''} |")
        L += ["", f"### Rząd {rz}, B = 50: kontrasty sparowane, średnia [95% CI]", "",
              "| Prawo | " + " | ".join(f"{x}−{y}" for x, y in KONTRASTY) + " |", "|---|" + "---|" * len(KONTRASTY)]
        for H in PRAWA_S0:
            cells = []
            for x, y in KONTRASTY:
                m, lo, hi = w["kontrasty"][f"{rz}|{H}|50|{x}-{y}"]
                cells.append(f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]")
            L.append(f"| {H} | " + " | ".join(cells) + " |")
        L += ["", f"### Rząd {rz}: trafność kandydatur ze snu (przetrwały weryfikator)", "",
              "| Prawo | S | S-Ś | W+S | S-los |", "|---|---|---|---|---|"]
        for H in PRAWA_S0:
            cells = []
            for r in ("S", "S-Ś", "W+S", "S-los"):
                rows = [x for x in w["wiersze"] if x["rzad"] == rz and x["H"] == H and x["ramie"] == r]
                s = sum(x["ze_snu_sprawdzone"] for x in rows); t = sum(x["ze_snu_prawdziwe"] for x in rows)
                cells.append(f"{t}/{s}" + (f" ({100 * t / s:.0f}%)" if s else ""))
            L.append(f"| {H} | " + " | ".join(cells) + " |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    print(json.dumps(main()["werdykt"], ensure_ascii=False, indent=1))
