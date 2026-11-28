"""Pilot odniesienia na zamrożonym sprawdzaczu NPH-1 (2026-11-28): ramiona bez modelu (C, E, R0)
we wszystkich trzech klasach, z parametrami przyjętymi przez Michała 28.11.

D1-W: światy pilotowe 2000–2059 (te same co pilot 2026-11-23, K = 20), NPH* z wynikaniem przez NPH-1.
D1':  pary rodzin 2110–2129 (10 par F/H, |F| = |H| = 20, K = 30); NPH* reguł (dokładne, Horn).
D2:   wersja 2, rodziny 2250–2269 (K = 20); metryka kontrastu = generalizacja.
Wynik nie wchodzi do testu: test używa ziaren zarezerwowanych w prerejestracji.
"""
import json
import sys
import time

from . import d1prime, d2, pilot, zamrozenie


def main(out):
    zamrozenie.sprawdz()
    t = time.time()
    res = {"sprawdzacz_nph": zamrozenie.opis()}
    res["D2"] = d2.run_pilot(range(2250, 2270), K=20, wersja=2)
    print("D2", round(time.time() - t), file=sys.stderr, flush=True)
    res["D1p"] = {"K": d1prime.K, "rodziny": d1prime.run_pilot(10, first_seed=2110)}
    print("D1p", round(time.time() - t), file=sys.stderr, flush=True)
    res["D1W"] = pilot.run(n_worlds=30)
    print("D1W", round(time.time() - t), file=sys.stderr, flush=True)
    with open(out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
