"""Świat zamknięty: magmy rozmiaru 3 z podłożonym prawem H (przeniesione z KG-0b, kg/kg0b_magmy.py).

Prawda podstawowa (graf implikacji między pojęciami w świecie W_H, jego redukcja przechodnia
na klasach równoważności i krawędzie „podłożone”) jest liczona wyczerpująco. Używa jej
WYŁĄCZNIE ewaluator i weryfikator; czuwanie, sen i intuicja nie mają do niej dostępu.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product

import numpy as np

S = 3
TOP = "⊤"

_codes = np.arange(S ** (S * S))
T = np.stack([(_codes // S ** i) % S for i in range(S * S)], axis=1).reshape(-1, S, S)
NM = len(T)
_I = np.arange(NM)[:, None]


def _op(a, b):
    return T[_I, a, b]


def _grid(r):
    X = np.array(list(product(range(S), repeat=r)))
    return [X[:, i][None].repeat(NM, 0) for i in range(r)]


_x2, _y2 = _grid(2)
_x3, _y3, _z3 = _grid(3)
_x4, _y4, _z4, _w4 = _grid(4)


def _law2(l, r):
    return (l(_x2, _y2) == r(_x2, _y2)).all(1)


def _law3(l, r):
    return (l(_x3, _y3, _z3) == r(_x3, _y3, _z3)).all(1)


def _concepts() -> dict[str, np.ndarray]:
    op = _op
    rows_perm = np.array([[len(set(t[i])) == S for i in range(S)] for t in T]).all(1)
    cols_perm = np.array([[len(set(t[:, j])) == S for j in range(S)] for t in T]).all(1)
    diag = T[:, np.arange(S), np.arange(S)]
    neutral = np.zeros(NM, bool); left_neutral = np.zeros(NM, bool); zero = np.zeros(NM, bool)
    for e in range(S):
        neutral |= (T[:, e, :] == np.arange(S)).all(1) & (T[:, :, e] == np.arange(S)).all(1)
        left_neutral |= (T[:, e, :] == np.arange(S)).all(1)
        zero |= (T[:, e, :] == e).all(1) & (T[:, :, e] == e).all(1)
    laws = {
        "komutatywna": _law2(lambda x, y: op(x, y), lambda x, y: op(y, x)),
        "łączna": _law3(lambda x, y, z: op(op(x, y), z), lambda x, y, z: op(x, op(y, z))),
        "idempotentna": (diag == np.arange(S)).all(1),
        "unipotentna xx=yy": (diag == diag[:, :1]).all(1),
        "xy=x": _law2(lambda x, y: op(x, y), lambda x, y: x),
        "xy=y": _law2(lambda x, y: op(x, y), lambda x, y: y),
        "stała": (T.reshape(NM, -1) == T.reshape(NM, -1)[:, :1]).all(1),
        "elastyczna x(yx)=(xy)x": _law2(lambda x, y: op(x, op(y, x)), lambda x, y: op(op(x, y), x)),
        "lewa alternat. x(xy)=(xx)y": _law2(lambda x, y: op(x, op(x, y)), lambda x, y: op(op(x, x), y)),
        "prawa alternat. (yx)x=y(xx)": _law2(lambda x, y: op(op(y, x), x), lambda x, y: op(y, op(x, x))),
        "medialna": (op(op(_x4, _y4), op(_z4, _w4)) == op(op(_x4, _z4), op(_y4, _w4))).all(1),
        "lewa samodystr.": _law3(lambda x, y, z: op(x, op(y, z)), lambda x, y, z: op(op(x, y), op(x, z))),
        "prawa samodystr.": _law3(lambda x, y, z: op(op(y, z), x), lambda x, y, z: op(op(y, x), op(z, x))),
        "x(xy)=y": _law2(lambda x, y: op(x, op(x, y)), lambda x, y: y),
        "(yx)x=y": _law2(lambda x, y: op(op(y, x), x), lambda x, y: y),
        "półsymetr. y(xy)=x": _law2(lambda x, y: op(y, op(x, y)), lambda x, y: x),
        "x(xy)=xy": _law2(lambda x, y: op(x, op(x, y)), lambda x, y: op(x, y)),
    }
    struct = {
        "quasigrupa": rows_perm & cols_perm,
        "lewo-skracalna": rows_perm,
        "prawo-skracalna": cols_perm,
        "ma neutralny": neutral,
        "ma lewy neutralny": left_neutral,
        "ma zero": zero,
        "ma idempotent": (diag == np.arange(S)).any(1),
    }
    return {**laws, **struct}


ALL = _concepts()
PRAWA_S0 = ("idempotentna", "komutatywna", "x(xy)=y", "łączna", "medialna")


def closure(names: list[str], edges) -> tuple[np.ndarray, dict[str, int]]:
    """Domknięcie zwrotno-przechodnie (Floyd–Warshall na bool)."""
    idx = {c: i for i, c in enumerate(names)}
    R = np.eye(len(names), dtype=bool)
    for a, b in edges:
        R[idx[a], idx[b]] = True
    for k in range(len(names)):
        R |= R[:, k:k + 1] & R[k:k + 1, :]
    return R, idx


def klasy_i_redukcja(names: list[str], E) -> tuple[dict[str, str], set]:
    """Klasy równoważności (reprezentant = pierwszy w kolejności names) i redukcja przechodnia na klasach."""
    R, idx = closure(names, E)
    cls = {a: min((b for b in names if R[idx[a], idx[b]] and R[idx[b], idx[a]]), key=names.index)
           for a in names}
    reps = sorted(set(cls.values()), key=names.index)
    CE = {(cls[a], cls[b]) for a, b in E if cls[a] != cls[b]}
    TR = {(a, b) for (a, b) in CE
          if not any((a, c) in CE and (c, b) in CE for c in reps if c not in (a, b))}
    return cls, TR


@dataclass(frozen=True)
class Swiat:
    H: str
    world: np.ndarray          # indeksy magm spełniających H
    concepts: dict             # nazwa -> maska bool po wszystkich magmach (bez H, z ⊤)
    names: list
    E: frozenset               # prawdziwe krawędzie w W_H (tylko dla ewaluatora/weryfikatora)
    TR: frozenset              # redukcja przechodnia na klasach
    TR_planted: frozenset      # krawędzie TR obecne dzięki H (fałszywe w całym M3)
    cls: dict

    def pokrycie(self, known_true) -> tuple[int, int]:
        R, idx = closure(self.names, known_true)
        cov = sum(bool(R[idx[x], idx[y]]) for (x, y) in self.TR)
        cov_p = sum(bool(R[idx[x], idx[y]]) for (x, y) in self.TR_planted)
        return cov, cov_p


def _ground_truth(world, concepts, names):
    return {(a, b) for a in names for b in names if a != b
            and concepts[a][world].any() and not (concepts[a][world] & ~concepts[b][world]).any()}


@lru_cache(maxsize=None)
def zbuduj_swiat(H: str) -> Swiat:
    world = np.nonzero(ALL[H])[0]
    concepts = {k: v for k, v in ALL.items() if k != H}
    concepts[TOP] = np.ones(NM, bool)
    names = list(concepts)
    E = _ground_truth(world, concepts, names)
    E_full = _ground_truth(np.arange(NM), concepts, names)
    planted = {e for e in E if e not in E_full}
    cls, TR = klasy_i_redukcja(names, E)
    TR_planted = {(a, b) for (a, b) in TR
                  if any((x, y) in planted for x in names for y in names if cls[x] == a and cls[y] == b)}
    return Swiat(H, world, concepts, names, frozenset(E), frozenset(TR), frozenset(TR_planted), cls)
