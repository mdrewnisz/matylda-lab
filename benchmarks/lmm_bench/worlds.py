"""Generatory światów (magm) z ziarnami i przemianowaniem.

Rezerwacje ziaren (uzgodnione z wątkiem KG, 2026-11-22):
  0–19      KG-0b pilot (WIDZIANE)
  1000–1049 KG-1 zbiór potwierdzający (zarezerwowany)
Benchmark: ziarna >= 2000. Magmy rozmiaru 3 zakazane, dopóki KG-1 nie przejdzie.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

MIN_SEED = 2000
MIN_SIZE = 4
MAX_SIZE = 7


class SeedPolicyError(ValueError):
    pass


def check_policy(seed: int, n: int) -> None:
    if seed < MIN_SEED:
        raise SeedPolicyError(f"ziarno {seed} < {MIN_SEED}: zakres zarezerwowany przez KG-0b/KG-1")
    if not (MIN_SIZE <= n <= MAX_SIZE):
        raise SeedPolicyError(f"rozmiar {n} poza {MIN_SIZE}–{MAX_SIZE} (rozmiar 3 zablokowany do czasu KG-1)")


@dataclass
class World:
    table: np.ndarray            # table[a, b] = a*b
    seed: int
    kind: str                    # "losowa" | "afiniczna" | ...
    params: dict = field(default_factory=dict)
    relabel: np.ndarray | None = None  # permutacja użyta do przemianowania

    @property
    def n(self) -> int:
        return self.table.shape[0]


def relabeled(table: np.ndarray, perm: np.ndarray) -> np.ndarray:
    """Izomorficzna kopia: element a przechodzi na perm[a]."""
    n = table.shape[0]
    inv = np.empty(n, dtype=np.int64)
    inv[perm] = np.arange(n)
    return perm[table[inv][:, inv]]


def random_magma(n: int, seed: int, relabel: bool = True) -> World:
    check_policy(seed, n)
    rng = np.random.default_rng(seed)
    t = rng.integers(0, n, size=(n, n), dtype=np.int64)
    perm = rng.permutation(n) if relabel else None
    if perm is not None:
        t = relabeled(t, perm)
    return World(t, seed, "losowa", {}, perm)


def affine_magma(n: int, seed: int, relabel: bool = True) -> World:
    """x*y = a x + b y + c (mod n), parametry losowane z ziarna. Rodzina z ukrytą strukturą."""
    check_policy(seed, n)
    rng = np.random.default_rng(seed)
    a, b, c = (int(v) for v in rng.integers(0, n, size=3))
    x = np.arange(n)
    t = (a * x[:, None] + b * x[None, :] + c) % n
    perm = rng.permutation(n) if relabel else None
    if perm is not None:
        t = relabeled(t, perm)
    return World(t.astype(np.int64), seed, "afiniczna", {"a": a, "b": b, "c": c}, perm)


def affine_family(n: int):
    """Wszystkie magmy afiniczne na Z_n (n^3 tabel), bez przemianowania. Do światów-klas (zakres K)."""
    x = np.arange(n)
    for a in range(n):
        for b in range(n):
            for c in range(n):
                yield (a, b, c), ((a * x[:, None] + b * x[None, :] + c) % n).astype(np.int64)
