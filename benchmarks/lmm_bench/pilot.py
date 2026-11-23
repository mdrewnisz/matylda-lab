"""Etap 2: pilot techniczny BEZ LMM. Ramiona C, R0, E na zadaniu D1-W (prawa w jednym świecie).

PILOT, NIE TEST. Wyniki służą tylko do: oszacowania odchylenia NPH* (analiza mocy),
sprawdzenia efektu sufitu/podłogi i kosztów. Nie wchodzą do testu właściwego.

Ziarna pilota: 2000–2999. Test właściwy będzie używał ziaren >= 3000.

Zadanie D1-W: świat = jedna magma. Hipoteza = prawo z puli (<= MAX_OPS operacji, <= 3 zmienne).
Limit zgłoszeń K na świat, identyczny dla ramion. Prawda podstawowa: wyczerpujące sprawdzenie.

Ramiona:
  E   enumerator: pierwsze K praw puli według rozmiaru składniowego.
  R0  losowe: K praw z puli, ziarno = ziarno świata.
  C   pętla symboliczna jak KG: „okno” = W losowych podstawień (tanie obserwacje), z puli
      zostają prawa bez kontrprzykładu w oknie, zgłaszane od najmniejszych; pomija prawa
      będące podstawieniem już przyjętego (wiedza z grafu). Koszt narzędzi raportowany osobno.
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

from . import basis, controls, worlds
from .terms import assignments, eval_term, holds, law_variables

PILOT_SEEDS = range(2000, 3000)
MAX_OPS = 4
K = 20
WINDOW = 12


def reference_models() -> list:
    """Modele do dolnej granicy NPH*: wszystkie magmy rozmiaru 2 i pełne rodziny afiniczne 4–5.
    Rozmiar 3 pominięty (blokada KG-1)."""
    refs = []
    for code in range(16):
        refs.append(np.array([[(code >> (2 * a + b)) & 1 for b in range(2)] for a in range(2)]))
    for n in (4, 5):
        refs += [t for _, t in worlds.affine_family(n)]
    return refs


def holds_on_window(law, table, rows) -> bool:
    vs = law_variables(law)
    env = assignments(table.shape[0], vs)
    n_all = len(env[vs[0]])
    pick = rows % n_all
    sub = {v: env[v][pick] for v in vs}
    return bool((eval_term(law[0], table, sub) == eval_term(law[1], table, sub)).all())


def arm_C(table, seed, pool):
    rng = np.random.default_rng(seed + 10_000_000)
    rows = rng.integers(0, 10**9, size=WINDOW)
    submitted, accepted, tool_checks = [], [], 0
    for law in pool:
        if len(submitted) >= K:
            break
        tool_checks += 1
        if not holds_on_window(law, table, rows):
            continue
        if any(basis.is_instance(law, g) for g in accepted):
            continue
        submitted.append(law)
        if holds(law, table):
            accepted.append(law)
    return submitted, tool_checks


def score(submitted, table, refs):
    acc = [l for l in submitted if holds(l, table)]
    lo, hi = basis.nph_star_laws(acc, reference_models=refs)
    return {"zgloszone": len(submitted), "przyjete": len(acc),
            "precyzja": len(acc) / len(submitted) if submitted else None,
            "nph_star_lo": lo, "nph_star_hi": hi}


def run(n_worlds: int = 30, sizes=(4, 5, 6), kinds=("afiniczna", "losowa")) -> dict:
    pool = list(controls.law_pool(MAX_OPS))
    refs = reference_models()
    rows = []
    seeds = iter(PILOT_SEEDS)
    for kind in kinds:
        for n in sizes:
            for _ in range(n_worlds // len(sizes)):
                s = next(seeds)
                w = (worlds.affine_magma if kind == "afiniczna" else worlds.random_magma)(n, s)
                t0 = time.perf_counter()
                truth = [l for l in pool if holds(l, w.table)]
                truth_lo, truth_hi = basis.nph_star_laws(truth, reference_models=refs) if truth else (0, 0)
                rec = {"seed": s, "kind": kind, "n": n, "prawdziwe_w_puli": len(truth),
                       "sufit_nph_star": [truth_lo, truth_hi]}
                rec["E"] = score(controls.enumerator_E(K, max_ops=MAX_OPS), w.table, refs)
                rec["R0"] = score(controls.random_R0(K, seed=s, max_ops=MAX_OPS), w.table, refs)
                subC, checks = arm_C(w.table, s, pool)
                rec["C"] = score(subC, w.table, refs)
                rec["C"]["sprawdzenia_okna"] = checks
                rec["czas_s"] = round(time.perf_counter() - t0, 3)
                rows.append(rec)
    return {"meta": {"K": K, "MAX_OPS": MAX_OPS, "WINDOW": WINDOW, "pula": len(pool),
                     "uwaga": "PILOT, nie test; ziarna 2000–2999"}, "swiaty": rows}


def summarize(res: dict) -> dict:
    out = {}
    for kind in sorted({r["kind"] for r in res["swiaty"]}):
        rs = [r for r in res["swiaty"] if r["kind"] == kind]
        d = {"swiaty": len(rs),
             "prawdziwe_w_puli_srednio": float(np.mean([r["prawdziwe_w_puli"] for r in rs])),
             "swiaty_bez_zadnego_prawa": sum(r["prawdziwe_w_puli"] == 0 for r in rs)}
        for arm in ("E", "R0", "C"):
            lo = np.array([r[arm]["nph_star_lo"] for r in rs], float)
            hi = np.array([r[arm]["nph_star_hi"] for r in rs], float)
            d[arm] = {"nph_star_hi_srednia": hi.mean(), "nph_star_hi_sd": hi.std(ddof=1),
                      "nph_star_lo_srednia": lo.mean(), "nph_star_lo_sd": lo.std(ddof=1)}
        for a, b in (("C", "E"), ("C", "R0")):
            diff = np.array([r[a]["nph_star_hi"] - r[b]["nph_star_hi"] for r in rs], float)
            d[f"{a}-{b}_hi"] = {"srednia": diff.mean(), "sd": diff.std(ddof=1)}
        out[kind] = d
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    res = run(n)
    res["podsumowanie"] = summarize(res)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1, default=float)
