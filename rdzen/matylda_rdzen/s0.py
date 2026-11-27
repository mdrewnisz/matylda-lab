"""S-0: pierwszy eksperyment snu. Uruchamiać dopiero po zamrożeniu PREREJESTRACJA_S0.md.

    python -m matylda_rdzen.s0            # pełny przebieg, zapis do rdzen/wyniki/
"""
from __future__ import annotations

from .intuicja import HeurystykaOgolnosci  # przypięta linia bazowa: wyniki sprzed 27.11 odtwarzalne

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from .petla import RAMIONA, uruchom
from .swiat import PRAWA_S0, zbuduj_swiat

SEEDS = range(20)
BUDZETY = (25, 50, 100)
B_GLOWNY = 50
BOOT = 10_000
BOOT_SEED = 12345
KONTRASTY = (("S", "W+"), ("S", "S-K"), ("S", "S-los"), ("S", "A2"), ("W+", "A2"))
ROOT = Path(__file__).resolve().parents[1]


def ci95(d: np.ndarray) -> tuple[float, float, float]:
    rng = np.random.default_rng(BOOT_SEED)
    bs = rng.choice(d, size=(BOOT, len(d)), replace=True).mean(1)
    return float(d.mean()), float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))


def main(out_dir: Path = ROOT / "wyniki") -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    prereg = (ROOT / "PREREJESTRACJA_S0.md").read_bytes()
    wiersze = []
    for H in PRAWA_S0:
        sw = zbuduj_swiat(H)
        for seed in SEEDS:
            for r in RAMIONA:
                pr = uruchom(H, seed, r, budzet=max(BUDZETY), intuicja=HeurystykaOgolnosci())
                dz = pr.dziennik
                wiersze.append({
                    "H": H, "seed": seed, "ramie": r, "TR": len(sw.TR), "TR_podlozone": len(sw.TR_planted),
                    "wywolania": pr.wywolania, "cykle": pr.cykle,
                    "pokrycie": {B: pr.pokrycie_przy(B)[0] for B in BUDZETY},
                    "pokrycie_podlozone": {B: pr.pokrycie_przy(B)[1] for B in BUDZETY},
                    "ze_snu_sprawdzone": dz.ze_snu_sprawdzone, "ze_snu_prawdziwe": dz.ze_snu_prawdziwe,
                    "obalone_za_darmo": dz.obalone_za_darmo, "pominiete_wynikajace": dz.pominiete_wynikajace,
                })
    # kontrasty sparowane po ziarnach
    kontr = {}
    for H in PRAWA_S0:
        for B in BUDZETY:
            for x, y in KONTRASTY:
                vx = {w["seed"]: w["pokrycie"][B] for w in wiersze if w["H"] == H and w["ramie"] == x}
                vy = {w["seed"]: w["pokrycie"][B] for w in wiersze if w["H"] == H and w["ramie"] == y}
                d = np.array([vx[s] - vy[s] for s in SEEDS], dtype=float)
                kontr[f"{H}|{B}|{x}-{y}"] = ci95(d)

    def werdykt(x, y):
        dod = [H for H in PRAWA_S0 if kontr[f"{H}|{B_GLOWNY}|{x}-{y}"][1] > 0]
        return dod, len(dod) >= 3

    glowny_dod, glowny = werdykt("S", "W+")
    wynik = {
        "prerejestracja_sha256": hashlib.sha256(prereg).hexdigest(),
        "wiersze": wiersze, "kontrasty": kontr,
        "werdykt": {
            "H-sen (S > W+ przy B=50, >=3 z 5 praw)": "NIE OBALONA (wsparta w tym świecie)" if glowny else "OBALONA w tym świecie",
            "prawa z dolną granicą CI > 0 (S-W+)": glowny_dod,
            "konsolidacja potrzebna (S > S-K)": werdykt("S", "S-K")[1],
            "sen lepszy od szumu (S > S-los)": werdykt("S", "S-los")[1],
        },
    }
    (out_dir / "s0_wyniki.json").write_text(json.dumps(wynik, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "S0_RAPORT.md").write_text(raport(wynik), encoding="utf-8")
    return wynik


def raport(w: dict) -> str:
    L = ["# S-0: wynik (generowany automatycznie przez matylda_rdzen.s0)", "",
         f"Prerejestracja sha256: `{w['prerejestracja_sha256']}`", "",
         "## Werdykt wg prerejestracji", ""]
    L += [f"- **{k}**: {v}" for k, v in w["werdykt"].items()]
    L += ["", "## Średnie pokrycie redukcji przechodniej (20 ziaren)", "",
          "| Prawo | |TR| | B | " + " | ".join(RAMIONA) + " |",
          "|---|---|---|" + "---|" * len(RAMIONA)]
    for H in PRAWA_S0:
        for B in BUDZETY:
            rows = [x for x in w["wiersze"] if x["H"] == H]
            tr = rows[0]["TR"]
            cells = [f"{np.mean([x['pokrycie'][B] for x in rows if x['ramie'] == r]):.1f}" for r in RAMIONA]
            L.append(f"| {H} | {tr} | {B} | " + " | ".join(cells) + " |")
    L += ["", f"## Kontrasty sparowane przy B = {B_GLOWNY}: średnia [95% CI bootstrap]", "",
          "| Prawo | " + " | ".join(f"{x}−{y}" for x, y in KONTRASTY) + " |", "|---|" + "---|" * len(KONTRASTY)]
    for H in PRAWA_S0:
        cells = []
        for x, y in KONTRASTY:
            m, lo, hi = w["kontrasty"][f"{H}|{B_GLOWNY}|{x}-{y}"]
            cells.append(f"{m:+.2f} [{lo:+.2f}, {hi:+.2f}]")
        L.append(f"| {H} | " + " | ".join(cells) + " |")
    L += ["", "## Trafność intuicji ze snu (odsetek kandydatur ze snu, które przetrwały weryfikator)", "",
          "| Prawo | S | S-K | S-los |", "|---|---|---|---|"]
    for H in PRAWA_S0:
        cells = []
        for r in ("S", "S-K", "S-los"):
            rows = [x for x in w["wiersze"] if x["H"] == H and x["ramie"] == r]
            s = sum(x["ze_snu_sprawdzone"] for x in rows); t = sum(x["ze_snu_prawdziwe"] for x in rows)
            cells.append(f"{t}/{s}" + (f" ({100 * t / s:.0f}%)" if s else ""))
        L.append(f"| {H} | " + " | ".join(cells) + " |")
    L += ["", "## Pokrycie krawędzi podłożonych przy B = 50 (średnio)", "",
          "| Prawo | |TR podł.| | " + " | ".join(RAMIONA) + " |", "|---|---|" + "---|" * len(RAMIONA)]
    for H in PRAWA_S0:
        rows = [x for x in w["wiersze"] if x["H"] == H]
        cells = [f"{np.mean([x['pokrycie_podlozone'][B_GLOWNY] for x in rows if x['ramie'] == r]):.1f}" for r in RAMIONA]
        L.append(f"| {H} | {rows[0]['TR_podlozone']} | " + " | ".join(cells) + " |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    w = main()
    print(json.dumps(w["werdykt"], ensure_ascii=False, indent=1))
    sys.exit(0)
