"""Zamrożone uniwersum magm rzędu 4 dla S-0b.

Magm rzędu 4 jest 4^16 ≈ 4,3 mld, więc nie da się ich przejrzeć jak w rzędzie 3. Uniwersum U4 to:
  - dla każdego prawa z PRAWA_S0: do N_PRAWO różnych magm spełniających to prawo, losowanych
    przeszukiwaniem z nawrotami w losowej kolejności wartości (próbka NIE jest jednostajna),
  - N_LOSOWE magm jednostajnie losowych (tło: dzięki nim „podłożone” krawędzie mają kontrprzykłady).
Świat W_H = magmy z U4 spełniające H (także te wylosowane dla innych praw). Prawda podstawowa
dotyczy tego zamkniętego świata, nie wszystkich magm rzędu 4.

    python -m matylda_rdzen.uniwersum4   # generuje dane/u4.npy (deterministycznie, ziarno 2026)
"""
from __future__ import annotations

import hashlib
import itertools
import random
from pathlib import Path

import numpy as np

N = 4
N_PRAWO = 1000
N_LOSOWE = 2000
ZIARNO = 2026
PLIK = Path(__file__).resolve().parents[1] / "dane" / "u4.npy"

_V = lambda s: ("v", s)  # noqa: E731
_M = lambda a, b: ("*", a, b)  # noqa: E731
_x, _y, _z, _w = _V("x"), _V("y"), _V("z"), _V("w")
TERMY = {
    "idempotentna": (_M(_x, _x), _x),
    "komutatywna": (_M(_x, _y), _M(_y, _x)),
    "x(xy)=y": (_M(_x, _M(_x, _y)), _y),
    "łączna": (_M(_M(_x, _y), _z), _M(_x, _M(_y, _z))),
    "medialna": (_M(_M(_x, _y), _M(_z, _w)), _M(_M(_x, _z), _M(_y, _w))),
}


def _ev(t, term, env):
    if term[0] == "v":
        return env[term[1]]
    a = _ev(t, term[1], env)
    if a is None:
        return None
    b = _ev(t, term[2], env)
    if b is None:
        return None
    return t[a * N + b]


def _zmienne(term, acc):
    if term[0] == "v":
        acc.add(term[1])
    else:
        _zmienne(term[1], acc); _zmienne(term[2], acc)
    return acc


def probka(prawo: str, rng: random.Random, limit_wezlow: int = 20000):
    l, r = TERMY[prawo]
    vs = sorted(_zmienne(l, set()) | _zmienne(r, set()))
    envs = [dict(zip(vs, c)) for c in itertools.product(range(N), repeat=len(vs))]
    t = [None] * (N * N)
    wezly = [0]

    def ok():
        for e in envs:
            a = _ev(t, l, e)
            if a is None:
                continue
            b = _ev(t, r, e)
            if b is not None and a != b:
                return False
        return True

    def bt(i):
        wezly[0] += 1
        if wezly[0] > limit_wezlow:
            return False
        if i == N * N:
            return True
        vals = list(range(N)); rng.shuffle(vals)
        for v in vals:
            t[i] = v
            if ok() and bt(i + 1):
                return True
        t[i] = None
        return False

    return tuple(t) if bt(0) else None


def generuj() -> np.ndarray:
    rng = random.Random(ZIARNO)
    zbior: dict[tuple, None] = {}
    for prawo in TERMY:
        mam, proby = 0, 0
        while mam < N_PRAWO and proby < 20 * N_PRAWO:
            proby += 1
            s = probka(prawo, rng)
            if s is not None and s not in zbior:
                zbior[s] = None; mam += 1
    nrng = np.random.default_rng(ZIARNO)
    for row in nrng.integers(0, N, size=(N_LOSOWE, N * N)):
        zbior.setdefault(tuple(int(v) for v in row), None)
    return np.array(list(zbior), dtype=np.uint8).reshape(-1, N, N)


def sha256(U: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(U).tobytes()).hexdigest()


def wczytaj() -> np.ndarray:
    if not PLIK.exists():
        raise FileNotFoundError(f"Brak {PLIK}. Wygeneruj: python -m matylda_rdzen.uniwersum4")
    return np.load(PLIK).astype(np.int64)


if __name__ == "__main__":
    U = generuj()
    PLIK.parent.mkdir(parents=True, exist_ok=True)
    np.save(PLIK, U)
    print(len(U), sha256(U))
