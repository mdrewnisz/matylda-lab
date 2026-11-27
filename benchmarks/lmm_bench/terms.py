"""DSL praw równaniowych dla magm (jedno działanie binarne `*`).

Term: zmienna (str) albo para (lewy, prawy) = lewy * prawy.
Prawo: para termów (l, r) czytana jako  ∀ zmienne: l = r.

Etap 1 benchmarku: to jest SPRAWDZACZ pisany przed jakimkolwiek modelem.
Nic tu nie generuje hipotez; tylko parsuje, liczy i kanonizuje.
"""
from __future__ import annotations

from itertools import product
from typing import Union

import numpy as np

Term = Union[str, tuple]
Law = tuple  # (Term, Term)

VARS = "xyzwuv"


# ---------- parser ----------
class ParseError(ValueError):
    pass


def _tokens(s: str):
    out = []
    for ch in s:
        if ch.isspace():
            continue
        if ch in "()*=" or ch.isalpha():
            out.append(ch)
        else:
            raise ParseError(f"niedozwolony znak: {ch!r}")
    return out


def parse_term(s: str) -> Term:
    toks = _tokens(s)
    pos = 0

    def atom():
        nonlocal pos
        if pos >= len(toks):
            raise ParseError("nieoczekiwany koniec")
        t = toks[pos]
        if t == "(":
            pos += 1
            e = expr()
            if pos >= len(toks) or toks[pos] != ")":
                raise ParseError("brak ')'")
            pos += 1
            return e
        if t.isalpha():
            pos += 1
            return t
        raise ParseError(f"nieoczekiwany token {t!r}")

    def expr():
        # '*' łączy w lewo:  x*y*z = (x*y)*z
        nonlocal pos
        left = atom()
        while pos < len(toks) and toks[pos] == "*":
            pos += 1
            left = (left, atom())
        return left

    t = expr()
    if pos != len(toks):
        raise ParseError(f"nadmiarowe tokeny od pozycji {pos}")
    return t


def parse_law(s: str) -> Law:
    if s.count("=") != 1:
        raise ParseError("prawo musi mieć dokładnie jedno '='")
    l, r = s.split("=")
    return parse_term(l), parse_term(r)


def show(t: Term) -> str:
    if isinstance(t, str):
        return t
    a, b = t
    sa = show(a) if isinstance(a, str) else f"({show(a)})"
    sb = show(b) if isinstance(b, str) else f"({show(b)})"
    return f"{sa}*{sb}"


def show_law(law: Law) -> str:
    return f"{show(law[0])} = {show(law[1])}"


# ---------- miary składniowe ----------
def variables(t: Term, acc=None) -> list:
    """Zmienne w kolejności pierwszego wystąpienia."""
    acc = [] if acc is None else acc
    if isinstance(t, str):
        if t not in acc:
            acc.append(t)
    else:
        variables(t[0], acc)
        variables(t[1], acc)
    return acc


def law_variables(law: Law) -> list:
    return variables(law[1], variables(law[0]))


def n_ops(t: Term) -> int:
    return 0 if isinstance(t, str) else 1 + n_ops(t[0]) + n_ops(t[1])


def law_ops(law: Law) -> int:
    return n_ops(law[0]) + n_ops(law[1])


def depth(t: Term) -> int:
    return 0 if isinstance(t, str) else 1 + max(depth(t[0]), depth(t[1]))


def in_etp_size_range(law: Law) -> bool:
    """Equational Theories Project obejmował prawa o <= 4 operacjach (z pamięci, do weryfikacji).

    Prawa w tym zakresie traktujemy jako potencjalnie OPUBLIKOWANE (wariant Z, nie N)."""
    return law_ops(law) <= 4


# ---------- kanonizacja ----------
def rename(t: Term, m: dict) -> Term:
    return m[t] if isinstance(t, str) else (rename(t[0], m), rename(t[1], m))


def mirror(t: Term) -> Term:
    """Prawo dualne: odwrócenie kolejności argumentów (x*y -> y*x)."""
    return t if isinstance(t, str) else (mirror(t[1]), mirror(t[0]))


def _key(t: Term) -> str:
    return show(t)


def _canon_oriented(l: Term, r: Term) -> Law:
    m = {v: VARS[i] if i < len(VARS) else f"v{i}" for i, v in enumerate(variables(r, variables(l)))}
    return rename(l, m), rename(r, m)


def canonical(law: Law, with_dual: bool = True) -> Law:
    """Reprezentant klasy: przemianowanie zmiennych, orientacja stron, opcjonalnie dualność."""
    l, r = law
    cands = [_canon_oriented(l, r), _canon_oriented(r, l)]
    if with_dual:
        ml, mr = mirror(l), mirror(r)
        cands += [_canon_oriented(ml, mr), _canon_oriented(mr, ml)]
    return min(cands, key=lambda c: (_key(c[0]), _key(c[1])))


def is_trivial(law: Law) -> bool:
    return law[0] == law[1]


# ---------- ewaluacja na tabeli ----------
def eval_term(t: Term, table: np.ndarray, env: dict) -> np.ndarray:
    """env: zmienna -> wektor indeksów elementów (wszystkie podstawienia naraz)."""
    if isinstance(t, str):
        return env[t]
    return table[eval_term(t[0], table, env), eval_term(t[1], table, env)]


def assignments(n: int, vs: list) -> dict:
    grid = np.array(list(product(range(n), repeat=len(vs))), dtype=np.int64).reshape(-1, len(vs))
    return {v: grid[:, i] for i, v in enumerate(vs)}


def counterexample(law: Law, table: np.ndarray):
    """None, gdy prawo zachodzi w magmie (sprawdzenie wyczerpujące); inaczej podstawienie."""
    n = table.shape[0]
    vs = law_variables(law)
    env = assignments(n, vs)
    bad = np.nonzero(eval_term(law[0], table, env) != eval_term(law[1], table, env))[0]
    if len(bad) == 0:
        return None
    i = int(bad[0])
    return {v: int(env[v][i]) for v in vs}


def holds(law: Law, table: np.ndarray) -> bool:
    return counterexample(law, table) is None
