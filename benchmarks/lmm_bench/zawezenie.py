"""Pomiar zawężenia przedziału NPH* (ramię C, D1-W) przy mocniejszych ustawieniach sprawdzacza wynikania.

PILOT, NIE TEST: te same światy co pilot 2026-11-23 (ziarna 2000–2059). Porównuje konfiguracje
(rozmiary kontrmodeli, limit węzłów dowodnika) na TYCH SAMYCH zbiorach praw przyjętych.
Rozmiar 3 pominięty (blokada KG-1).
"""
from __future__ import annotations

import json
import sys
import time

from . import basis, controls, worlds
from .pilot import PILOT_SEEDS, arm_C
from .terms import holds

CONFIGS = {   # "bazowa" = dokładnie ustawienia pilota 2026-11-23
    "bazowa":                dict(sizes=(2, 4, 5), node_limit=5000, packing=False, fill_free=False),
    "pakowanie":             dict(sizes=(2, 4, 5), node_limit=5000, packing=True, fill_free=False),
    "pakowanie+podstawienia": dict(sizes=(2, 4, 5), node_limit=5000, packing=True, fill_free=True),
    "wszystko+rozmiar6":     dict(sizes=(2, 4, 5, 6), node_limit=20000, packing=True, fill_free=True),
}

# 2026-11-28: pary kontrmodeli (dolna) i harmonogram szerokości dowodnika (górna)
CONFIGS_2 = {
    "poprzednia":   dict(sizes=(2, 4, 5), node_limit=5000, packing=True, fill_free=True),
    "pary":         dict(sizes=(2, 4, 5), node_limit=5000, packing=True, fill_free=True, pairs=True),
    "harmonogram":  dict(sizes=(2, 4, 5), node_limit=50000, packing=True, fill_free=True, extra_ops=(2, 4)),
    "oba":          dict(sizes=(2, 4, 5), node_limit=50000, packing=True, fill_free=True, extra_ops=(2, 4), pairs=True),
}


def run(n_worlds=30, sizes=(4, 5, 6), kinds=("afiniczna", "losowa"), configs=CONFIGS, first_seed=2000):
    pool = list(controls.law_pool(4))
    seeds = iter(range(first_seed, PILOT_SEEDS.stop))   # kolejność jak w pilocie 2026-11-23
    rows = []
    for kind in kinds:
        for n in sizes:
            for _ in range(n_worlds // len(sizes)):
                s = next(seeds)
                w = (worlds.affine_magma if kind == "afiniczna" else worlds.random_magma)(n, s)
                sub, _ = arm_C(w.table, s, pool)
                acc = [l for l in sub if holds(l, w.table)]
                rec = {"seed": s, "kind": kind, "n": n, "przyjete": len(acc)}
                for name, cfg in configs.items():
                    t0 = time.perf_counter()
                    lo, hi = basis.nph_star_laws_entail(acc, **cfg) if acc else (0, 0)
                    rec[name] = {"lo": lo, "hi": hi, "czas_s": round(time.perf_counter() - t0, 2)}
                rows.append(rec)
                print(json.dumps(rec, ensure_ascii=False), file=sys.stderr, flush=True)
    return rows


def summarize(rows, configs=CONFIGS):
    out = {}
    for name in configs:
        lo = [r[name]["lo"] for r in rows]
        hi = [r[name]["hi"] for r in rows]
        out[name] = {"lo_srednia": sum(lo) / len(lo), "hi_srednia": sum(hi) / len(hi),
                     "swiaty_domkniete": sum(a == b for a, b in zip(lo, hi)),
                     "szerokosc_srednia": sum(b - a for a, b in zip(lo, hi)) / len(lo),
                     "czas_s_suma": round(sum(r[name]["czas_s"] for r in rows), 1)}
    return out


if __name__ == "__main__":
    kinds = tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ("afiniczna", "losowa")
    first = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
    rows = run(int(sys.argv[1]) if len(sys.argv) > 1 else 30, kinds=kinds, first_seed=first)
    json.dump({"swiaty": rows, "podsumowanie": summarize(rows)}, sys.stdout, ensure_ascii=False, indent=1)
