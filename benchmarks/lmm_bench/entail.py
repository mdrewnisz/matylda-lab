"""Sprawdzacz wynikania między prawami: Γ ⊨ L ?

Dwie niezależne, rozstrzygające w jedną stronę procedury:
  * prove():  ograniczone dwukierunkowe przeszukiwanie przepisań (dowód równaniowy).
              Każdy znaleziony dowód jest PONOWNIE sprawdzany przez proofcheck.check_proof.
              Wynik pozytywny = PROVED (pewny). Brak dowodu nic nie znaczy.
  * countermodel(): szukanie skończonej magmy spełniającej Γ i łamiącej L (SAT, pysat),
              w stylu Mace4. Wynik = REFUTED z tabelą jako certyfikatem, sprawdzoną
              niezależnie przez terms.holds. Brak kontrmodelu nic nie znaczy.
Gdy żadna nie rozstrzyga: UNKNOWN.

Rozmiar 3 jest pomijany w szukaniu kontrmodeli (blokada KG-1 na magmy rozmiaru 3).
"""
from __future__ import annotations

from collections import deque
from itertools import product

import numpy as np

from .proofcheck import Step, apply_subst, check_proof, match, replace_at, subterm
from .terms import Law, Term, holds, law_variables, n_ops

PROVED, REFUTED, UNKNOWN = "PROVED", "REFUTED", "UNKNOWN"


# ---------- dowodzenie ----------
def _vars(t, acc=None):
    acc = set() if acc is None else acc
    if isinstance(t, str):
        acc.add(t)
    else:
        _vars(t[0], acc)
        _vars(t[1], acc)
    return acc


def _positions(t, pre=()):
    yield pre
    if not isinstance(t, str):
        yield from _positions(t[0], pre + (0,))
        yield from _positions(t[1], pre + (1,))


def _oriented(axioms):
    out = []
    for i, (l, r) in enumerate(axioms):
        for d, (s, t) in (("lr", (l, r)), ("rl", (r, l))):
            out.append((i, d, s, t))
    return out


def _forward(term, rules, max_ops, fillers=()):
    """Kroki przepisania w przód. Zmienne wolne strony docelowej (np. z w x*y -> x*z) dostają
    kolejno każdą wartość z `fillers` (zmienne celu); podstawienie trafia jawnie do kroku."""
    for i, d, src, dst in rules:
        free = sorted(_vars(dst) - _vars(src))
        if free and not fillers:
            continue
        for pos in _positions(term):
            s = match(src, subterm(term, pos), {})
            if s is None:
                continue
            for vals in product(fillers, repeat=len(free)) if free else [()]:
                s2 = dict(s)
                s2.update(zip(free, vals))
                nt = replace_at(term, pos, apply_subst(dst, s2))
                if n_ops(nt) <= max_ops:
                    yield nt, Step(i, d, pos, nt, s2)


def prove(axioms: list, law: Law, extra_ops: int = 2, node_limit: int = 20000, fill_free: bool = True):
    """Zwraca listę kroków sprawdzoną przez proofcheck albo None.

    Przeszukiwanie w przód z obu stron (l i r) aż do wspólnego termu; kroki ze strony r
    są odwracane, a zmienne wolne odwróconego kroku dostają jawne podstawienie."""
    l, r = law
    if l == r:
        return []
    rules = _oriented(axioms)
    max_ops = max(n_ops(l), n_ops(r)) + extra_ops
    fillers = tuple(sorted(_vars(l) | _vars(r))) if fill_free else ()
    seen = [{l: None}, {r: None}]
    queues = [deque([l]), deque([r])]
    nodes = 0
    while (queues[0] or queues[1]) and nodes < node_limit:
        for side in (0, 1):
            if not queues[side]:
                continue
            t = queues[side].popleft()
            for nt, st in _forward(t, rules, max_ops, fillers):
                nodes += 1
                if nt in seen[side]:
                    continue
                seen[side][nt] = (t, st)
                if nt in seen[1 - side]:
                    return _build(nt, seen[0], seen[1], axioms, law)
                queues[side].append(nt)
    return None


def _build(meet, fwd, bwd, axioms, law):
    head, t = [], meet
    while fwd[t] is not None:
        prev, st = fwd[t]
        head.append(st)
        t = prev
    head.reverse()
    t = meet
    while bwd[t] is not None:          # bwd[t] = (poprzednik po stronie r, krok poprzednik -> t)
        prev, st = bwd[t]
        src, dst = axioms[st.axiom] if st.direction == "lr" else axioms[st.axiom][::-1]
        free = _vars(src) - _vars(dst)
        head.append(Step(st.axiom, "rl" if st.direction == "lr" else "lr", st.position, prev,
                         {v: st.subst[v] for v in free}))
        t = prev
    ok, why = check_proof(law, axioms, head)
    if not ok:                       # nigdy nie przyjmujemy dowodu bez sprawdzacza
        raise AssertionError(f"wewnętrzny dowód odrzucony przez sprawdzacz: {why}")
    return head


# ---------- kontrmodele (SAT) ----------
def _subterms(t, acc):
    if not isinstance(t, str):
        _subterms(t[0], acc)
        _subterms(t[1], acc)
    if t not in acc:
        acc.append(t)
    return acc


def countermodel(axioms: list, law: Law, sizes=(2, 4, 5)):
    try:
        from pysat.solvers import Cadical153
    except ImportError:            # bez pysat: tylko pełne przeszukanie rozmiaru 2
        return _brute2(axioms, law)
    for n in sizes:
        t = _sat_countermodel(axioms, law, n, Cadical153)
        if t is not None:
            assert all(holds(a, t) for a in axioms) and not holds(law, t)   # niezależna kontrola
            return t
    return None


def _brute2(axioms, law):
    for code in range(16):
        t = np.array([[(code >> (2 * a + b)) & 1 for b in range(2)] for a in range(2)])
        if all(holds(a, t) for a in axioms) and not holds(law, t):
            return t
    return None


def _sat_countermodel(axioms, law, n, Solver):
    nv = [0]

    def new():
        nv[0] += 1
        return nv[0]

    M = {(a, b, c): new() for a in range(n) for b in range(n) for c in range(n)}
    cls = []
    for a in range(n):
        for b in range(n):
            lits = [M[a, b, c] for c in range(n)]
            cls.append(lits)
            cls += [[-x, -y] for i, x in enumerate(lits) for y in lits[i + 1:]]

    def encode_value(t, sigma, cache):
        """Zwraca listę n literałów: lit[k] <=> wartość termu = k (dla zmiennej: stałe)."""
        if isinstance(t, str):
            return ("const", sigma[t])
        key = (t, tuple(sorted(sigma.items())))
        if key in cache:
            return cache[key]
        A = encode_value(t[0], sigma, cache)
        B = encode_value(t[1], sigma, cache)
        E = [new() for _ in range(n)]
        cls.extend([[-x, -y] for i, x in enumerate(E) for y in E[i + 1:]])
        ai = [A[1]] if A[0] == "const" else range(n)
        bj = [B[1]] if B[0] == "const" else range(n)
        for i in ai:
            for j in bj:
                for k in range(n):
                    c = [-M[i, j, k], E[k]]
                    if A[0] != "const":
                        c.append(-A[1][i])
                    if B[0] != "const":
                        c.append(-B[1][j])
                    cls.append(c)
        res = ("var", E)
        cache[key] = res
        return res

    def lit_eq(v, k):          # literał „wartość = k” albo stała prawda/fałsz
        if v[0] == "const":
            return True if v[1] == k else False
        return v[1][k]

    cache = {}
    for ax in axioms:
        vs = law_variables(ax)
        for vals in product(range(n), repeat=len(vs)):
            sg = dict(zip(vs, vals))
            L, R = encode_value(ax[0], sg, cache), encode_value(ax[1], sg, cache)
            for k in range(n):
                a, b = lit_eq(L, k), lit_eq(R, k)
                for x, y in ((a, b), (b, a)):           # x -> y
                    if x is False or y is True:
                        continue
                    c = []
                    if x is not True:
                        c.append(-x)
                    if y is not False:
                        c.append(y)
                    cls.append(c)
    vs = law_variables(law)
    sel = []
    for vals in product(range(n), repeat=len(vs)):
        sg = dict(zip(vs, vals))
        d = new()
        sel.append(d)
        L, R = encode_value(law[0], sg, cache), encode_value(law[1], sg, cache)
        for k in range(n):                              # d -> ¬(L=k ∧ R=k)
            a, b = lit_eq(L, k), lit_eq(R, k)
            if a is False or b is False:
                continue
            c = [-d]
            if a is not True:
                c.append(-a)
            if b is not True:
                c.append(-b)
            cls.append(c)
    cls.append(sel)
    with Solver(bootstrap_with=cls) as s:
        if not s.solve():
            return None
        model = set(x for x in s.get_model() if x > 0)
    t = np.zeros((n, n), dtype=np.int64)
    for (a, b, c), v in M.items():
        if v in model:
            t[a, b] = c
    return t


# ---------- rozstrzygnięcie ----------
def entails(axioms: list, law: Law, **kw):
    steps = prove(axioms, law, **{k: v for k, v in kw.items() if k in ("extra_ops", "node_limit", "fill_free")})
    if steps is not None:
        return PROVED, steps
    t = countermodel(axioms, law, **{k: v for k, v in kw.items() if k == "sizes"})
    if t is not None:
        return REFUTED, t
    return UNKNOWN, None
