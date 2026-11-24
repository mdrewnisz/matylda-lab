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


def wszystkie_magmy(n: int) -> np.ndarray:
    codes = np.arange(n ** (n * n))
    return np.stack([(codes // n ** i) % n for i in range(n * n)], axis=1).reshape(-1, n, n)


def pojecia(T: np.ndarray) -> dict[str, np.ndarray]:
    """Maski pojęć (prawa i własności strukturalne) dla tablic działań T kształtu (liczba, n, n)."""
    NM, n = len(T), T.shape[1]
    I = np.arange(NM)[:, None]

    def op(a, b):
        return T[I, a, b]

    def grid(r):
        X = np.array(list(product(range(n), repeat=r)))
        return [X[:, i][None].repeat(NM, 0) for i in range(r)]

    x2, y2 = grid(2)
    x3, y3, z3 = grid(3)
    x4, y4, z4, w4 = grid(4)

    def law2(l, r):
        return (l(x2, y2) == r(x2, y2)).all(1)

    def law3(l, r):
        return (l(x3, y3, z3) == r(x3, y3, z3)).all(1)

    ar = np.arange(n)
    rows_perm = (np.sort(T, axis=2) == ar).all((1, 2))
    cols_perm = (np.sort(T, axis=1) == ar[:, None]).all((1, 2))
    diag = T[:, ar, ar]
    neutral = np.zeros(NM, bool); left_neutral = np.zeros(NM, bool); zero = np.zeros(NM, bool)
    for e in range(n):
        neutral |= (T[:, e, :] == ar).all(1) & (T[:, :, e] == ar).all(1)
        left_neutral |= (T[:, e, :] == ar).all(1)
        zero |= (T[:, e, :] == e).all(1) & (T[:, :, e] == e).all(1)
    laws = {
        "komutatywna": law2(lambda x, y: op(x, y), lambda x, y: op(y, x)),
        "łączna": law3(lambda x, y, z: op(op(x, y), z), lambda x, y, z: op(x, op(y, z))),
        "idempotentna": (diag == ar).all(1),
        "unipotentna xx=yy": (diag == diag[:, :1]).all(1),
        "xy=x": law2(lambda x, y: op(x, y), lambda x, y: x),
        "xy=y": law2(lambda x, y: op(x, y), lambda x, y: y),
        "stała": (T.reshape(NM, -1) == T.reshape(NM, -1)[:, :1]).all(1),
        "elastyczna x(yx)=(xy)x": law2(lambda x, y: op(x, op(y, x)), lambda x, y: op(op(x, y), x)),
        "lewa alternat. x(xy)=(xx)y": law2(lambda x, y: op(x, op(x, y)), lambda x, y: op(op(x, x), y)),
        "prawa alternat. (yx)x=y(xx)": law2(lambda x, y: op(op(y, x), x), lambda x, y: op(y, op(x, x))),
        "medialna": (op(op(x4, y4), op(z4, w4)) == op(op(x4, z4), op(y4, w4))).all(1),
        "lewa samodystr.": law3(lambda x, y, z: op(x, op(y, z)), lambda x, y, z: op(op(x, y), op(x, z))),
        "prawa samodystr.": law3(lambda x, y, z: op(op(y, z), x), lambda x, y, z: op(op(y, x), op(z, x))),
        "x(xy)=y": law2(lambda x, y: op(x, op(x, y)), lambda x, y: y),
        "(yx)x=y": law2(lambda x, y: op(op(y, x), x), lambda x, y: y),
        "półsymetr. y(xy)=x": law2(lambda x, y: op(y, op(x, y)), lambda x, y: x),
        "x(xy)=xy": law2(lambda x, y: op(x, op(x, y)), lambda x, y: op(x, y)),
    }
    struct = {
        "quasigrupa": rows_perm & cols_perm,
        "lewo-skracalna": rows_perm,
        "prawo-skracalna": cols_perm,
        "ma neutralny": neutral,
        "ma lewy neutralny": left_neutral,
        "ma zero": zero,
        "ma idempotent": (diag == ar).any(1),
    }
    return {**laws, **struct}


T = wszystkie_magmy(S)
NM = len(T)
ALL = pojecia(T)
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
def zbuduj_swiat(H: str, rzad: int = 3, slownik: str = "baza") -> Swiat:
    """rzad 3: wszystkie 3^9 magm (jak KG-0b). rzad 4: zamrożone uniwersum próbkowane (dane/u4.npy).
    slownik: "baza" (24 pojęcia + ⊤) albo "negacje" (do tego zaprzeczenie każdego pojęcia, ¬X)."""
    if rzad in (3, "3T"):
        allc, nm = ALL, NM
    elif rzad == 4:
        allc, nm = _pojecia_u4()
    elif rzad == "4T":
        allc, nm = _pojecia_u4t()
    else:
        raise ValueError(rzad)
    czesci = H.split(" ∧ ")                     # koniunkcja praw/własności (światy treningowe LMM)
    maska = np.logical_and.reduce([allc[c] for c in czesci])
    if rzad in ("3T", "4T"):                    # światy treningowe LMM v2: bez magm praw S-0 i walidacyjnych
        from .uniwersum4t import WYKLUCZONE
        assert not set(czesci) & set(WYKLUCZONE)
        maska = maska & ~np.logical_or.reduce([allc[h] for h in WYKLUCZONE])
    world = np.nonzero(maska)[0]
    concepts = {k: v for k, v in allc.items() if k not in czesci}
    if slownik == "negacje":
        concepts.update({f"¬{k}": ~v for k, v in list(concepts.items())})
    elif slownik in ("literaly", "tylko_literaly"):
        # „tokeny zależności” najniższego poziomu: pojedyncze wpisy tablicy działania, a·b = c
        U = _tablice(rzad)
        n = U.shape[1]
        lit = {f"{a}·{b}={c}": U[:, a, b] == c for a in range(n) for b in range(n) for c in range(n)}
        if slownik == "tylko_literaly":
            concepts = {}
        concepts.update(lit)
    elif slownik != "baza":
        raise ValueError(slownik)
    concepts[TOP] = np.ones(nm, bool)
    names = list(concepts)
    E = _ground_truth(world, concepts, names)
    E_full = _ground_truth(np.arange(nm), concepts, names)
    planted = {e for e in E if e not in E_full}
    cls, TR = klasy_i_redukcja(names, E)
    TR_planted = {(a, b) for (a, b) in TR
                  if any((x, y) in planted for x in names for y in names if cls[x] == a and cls[y] == b)}
    return Swiat(H, world, concepts, names, frozenset(E), frozenset(TR), frozenset(TR_planted), cls)


def _tablice(rzad) -> np.ndarray:
    if rzad in (3, "3T"):
        return T
    if rzad == "4T":
        from .uniwersum4t import wczytaj as w4t
        return w4t()
    from .uniwersum4 import wczytaj
    return wczytaj()


@lru_cache(maxsize=None)
def _pojecia_u4():
    from .uniwersum4 import wczytaj
    U = wczytaj()
    return pojecia(U), len(U)


@lru_cache(maxsize=None)
def _pojecia_u4t():
    from .uniwersum4t import wczytaj
    U = wczytaj()
    return pojecia(U), len(U)
