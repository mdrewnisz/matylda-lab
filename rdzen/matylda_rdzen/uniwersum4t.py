"""Uniwersum TRENINGOWE rzędu 4 dla intuicji LMM (v2), rozłączne z U4 i bez magm praw S-0 i praw walidacyjnych.

Recenzja przed zamrożeniem S-1 LMM (B1): światy treningowe rzędu 4 wycięte z U4 pokrywały się prawie w całości ze światami S-0
(np. lewa alternatywność ⊃ łączne, lewo-skracalne ⊃ x(xy)=y). Tu magmy losujemy od nowa:
  - pod prawa treningowe (wyszukiwanie z nawrotami, jak w U4),
  - konstrukcyjnie pod własności strukturalne (wiersze/kolumny permutacjami, kwadraty łacińskie, element neutralny, zero, idempotent),
  - plus tło jednostajne;
i usuwamy każdą magmę, która spełnia prawo S-0 lub prawo walidacyjne albo leży w U4.

    python -m matylda_rdzen.uniwersum4t   # generuje dane/u4t.npy (deterministycznie, ziarno 4242)
"""
from __future__ import annotations

import hashlib
import random
from pathlib import Path

import numpy as np

from . import uniwersum4 as U

N = 4
N_NA_GENERATOR = 700
N_LOSOWE = 2000
ZIARNO = 4242
PLIK = Path(__file__).resolve().parents[1] / "dane" / "u4t.npy"
_x, _y = U._x, U._y
_M = U._M
TERMY_TRENING = {
    "unipotentna xx=yy": (_M(_x, _x), _M(_y, _y)),
    "lewa alternat. x(xy)=(xx)y": (_M(_x, _M(_x, _y)), _M(_M(_x, _x), _y)),
    "prawa alternat. (yx)x=y(xx)": (_M(_M(_y, _x), _x), _M(_y, _M(_x, _x))),
    "półsymetr. y(xy)=x": (_M(_y, _M(_x, _y)), _x),
}
# prawa, których magm NIE może być w uniwersum treningowym (S-0 + prawa walidacyjne LMM)
WYKLUCZONE = ("idempotentna", "komutatywna", "x(xy)=y", "łączna", "medialna",
              "elastyczna x(yx)=(xy)x", "lewa samodystr.", "prawa samodystr.", "x(xy)=xy", "(yx)x=y")


def _latin(rng):
    t = [[None] * N for _ in range(N)]

    def bt(k):
        if k == N * N:
            return True
        i, j = divmod(k, N)
        vals = list(range(N)); rng.shuffle(vals)
        for v in vals:
            if v not in t[i] and all(t[r][j] != v for r in range(N)):
                t[i][j] = v
                if bt(k + 1):
                    return True
                t[i][j] = None
        return False
    bt(0)
    return [v for row in t for v in row]


def _konstrukcje(rng):
    def los():
        return [rng.randrange(N) for _ in range(N * N)]

    def wiersze():
        out = []
        for _ in range(N):
            p = list(range(N)); rng.shuffle(p); out += p
        return out

    def kolumny():
        cols = []
        for _ in range(N):
            p = list(range(N)); rng.shuffle(p); cols.append(p)
        return [cols[j][i] for i in range(N) for j in range(N)]

    def neutralny(lewy_tylko=False):
        t, e = los(), rng.randrange(N)
        for b in range(N):
            t[e * N + b] = b
            if not lewy_tylko:
                t[b * N + e] = b
        return t

    def zero():
        t, e = los(), rng.randrange(N)
        for b in range(N):
            t[e * N + b] = e; t[b * N + e] = e
        return t

    def idempotent():
        t, e = los(), rng.randrange(N)
        t[e * N + e] = e
        return t

    return {"quasigrupa": lambda: _latin(rng), "lewo-skracalna": wiersze, "prawo-skracalna": kolumny,
            "ma neutralny": neutralny, "ma lewy neutralny": lambda: neutralny(True), "ma zero": zero,
            "ma idempotent": idempotent}


def generuj() -> np.ndarray:
    from .swiat import pojecia
    rng = random.Random(ZIARNO)
    zbior: dict[tuple, None] = {}
    U.TERMY.update(TERMY_TRENING)          # probka() czyta TERMY; dopisujemy tylko prawa treningowe
    for prawo in TERMY_TRENING:
        mam = proby = 0
        while mam < N_NA_GENERATOR and proby < 20 * N_NA_GENERATOR:
            proby += 1
            s = U.probka(prawo, rng)
            if s is not None and s not in zbior:
                zbior[s] = None; mam += 1
    for gen in _konstrukcje(rng).values():
        for _ in range(N_NA_GENERATOR):
            zbior.setdefault(tuple(gen()), None)
    for _ in range(N_LOSOWE):
        zbior.setdefault(tuple(rng.randrange(N) for _ in range(N * N)), None)
    T = np.array(list(zbior), dtype=np.uint8).reshape(-1, N, N)
    P = pojecia(T.astype(np.int64))
    zly = np.logical_or.reduce([P[h] for h in WYKLUCZONE])
    u4 = {tuple(m.ravel()) for m in np.load(U.PLIK)}
    w_u4 = np.array([tuple(m.ravel()) in u4 for m in T])
    return T[~zly & ~w_u4]


def sha256(T: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(T).tobytes()).hexdigest()


def wczytaj() -> np.ndarray:
    if not PLIK.exists():
        raise FileNotFoundError(f"Brak {PLIK}. Wygeneruj: python -m matylda_rdzen.uniwersum4t")
    return np.load(PLIK).astype(np.int64)


if __name__ == "__main__":
    T = generuj()
    np.save(PLIK, T)
    print(len(T), sha256(T))
