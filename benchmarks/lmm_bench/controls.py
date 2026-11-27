"""Kontrole bez modelu: R0 (losowe hipotezy) i E (enumeracja według rozmiaru składniowego).

Obie korzystają z tej samej gramatyki i tego samego limitu zgłoszeń K co ramiona z modelem.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .terms import canonical, is_trivial, law_ops, show_law


@lru_cache(maxsize=None)
def terms_with_ops(k: int, vs: tuple) -> tuple:
    if k == 0:
        return vs
    out = []
    for i in range(k):
        for a in terms_with_ops(i, vs):
            for b in terms_with_ops(k - 1 - i, vs):
                out.append((a, b))
    return tuple(out)


@lru_cache(maxsize=None)
def law_pool(max_ops: int = 4, n_vars: int = 3) -> tuple:
    """Wszystkie kanoniczne, nietrywialne prawa o łącznie <= max_ops operacjach, uporządkowane
    według (liczba operacji, zapis). Kolejność jest deterministyczna."""
    vs = tuple("xyz"[:n_vars])
    seen = set()
    for total in range(max_ops + 1):
        for kl in range(total + 1):
            for l in terms_with_ops(kl, vs):
                for r in terms_with_ops(total - kl, vs):
                    law = (l, r)
                    if is_trivial(law):
                        continue
                    seen.add(canonical(law))
    return tuple(sorted(seen, key=lambda c: (law_ops(c), show_law(c))))


def enumerator_E(K: int, exclude=(), max_ops: int = 4) -> list:
    ex = {canonical(e) for e in exclude}
    return [c for c in law_pool(max_ops) if c not in ex][:K]


def random_R0(K: int, seed: int, exclude=(), max_ops: int = 4) -> list:
    ex = {canonical(e) for e in exclude}
    pool = [c for c in law_pool(max_ops) if c not in ex]
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(pool), size=min(K, len(pool)), replace=False)
    return [pool[i] for i in idx]
