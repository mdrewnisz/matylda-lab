"""Zewnętrzny prover równaniowy twee (decyzja Michała 2026-11-28) z NIEZALEŻNYM sprawdzeniem dowodu.

Twee 2.4.2 (github.com/nick8325/twee, binarka linux-amd64 z wydania autora) szuka dowodu Γ ⊨ L.
Dowód (opcja --no-lemmas: łańcuch termów, każdy krok „by axiom k (axk) L->R / R->L”) przepisujemy
na kroki Step (aksjomat, kierunek, pozycja, wynik, podstawienie) i sprawdzamy proofcheck.check_proof.
Twee jest więc tylko wyszukiwarką: wynik bez przejścia przez proofcheck jest odrzucany.

Ścieżka do binarki: zmienna środowiskowa TWEE albo benchmarks/narzedzia/bin/twee (pobiera ją
narzedzia/pobierz_twee.sh). Brak binarki -> None, a sprawdzacz wraca do własnego dowodnika.
SHA-256 sprawdzanej binarki: zapisany w TWEE_SHA256 (odrzucamy inną).
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
from functools import lru_cache

from .proofcheck import Step, apply_subst, check_proof, match, replace_at, subterm
from .terms import Law, Term

TWEE_SHA256 = "75e69a47166f7f5c54facde4a8c71a33552b4cb20bdac8b7ece9536f94e07e6e"
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "narzedzia", "bin", "twee")


@lru_cache(maxsize=1)
def binary():
    p = os.environ.get("TWEE", DEFAULT_PATH)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != TWEE_SHA256:
            return None
    return p


def _tptp(t: Term, var: bool) -> str:
    if isinstance(t, str):
        return t.upper() if var else "c" + t
    return f"mul({_tptp(t[0], var)},{_tptp(t[1], var)})"


def _parse(s: str):
    s = s.replace(" ", "")
    pos = 0

    def term():
        nonlocal pos
        if s.startswith("mul(", pos):
            pos += 4
            a = term()
            assert s[pos] == ","
            pos += 1
            b = term()
            assert s[pos] == ")"
            pos += 1
            return (a, b)
        m = re.match(r"[A-Za-z0-9_]+", s[pos:])
        if not m:
            raise ValueError(s)
        pos += m.end()
        name = m.group(0)
        if name.startswith("c") and name[1:].isalpha() and name[1:].islower():
            return name[1:]
        raise ValueError(f"nieznany symbol {name}")       # zmienne/stałe twee spoza celu: nie obsługujemy

    t = term()
    if pos != len(s):
        raise ValueError(s)
    return t


def _positions(t, pre=()):
    yield pre
    if not isinstance(t, str):
        yield from _positions(t[0], pre + (0,))
        yield from _positions(t[1], pre + (1,))


def _vars(t, acc=None):
    acc = set() if acc is None else acc
    if isinstance(t, str):
        acc.add(t)
    else:
        _vars(t[0], acc)
        _vars(t[1], acc)
    return acc


def _step(cur, nxt, axioms, k, direction):
    l, r = axioms[k]
    src, dst = (l, r) if direction == "lr" else (r, l)
    free = _vars(dst) - _vars(src)
    for pos in _positions(cur):
        s = match(src, subterm(cur, pos), {})
        if s is None:
            continue
        try:
            target = subterm(nxt, pos)
        except Exception:
            continue
        s2 = match(dst, target, dict(s))
        if s2 is None:
            continue
        if replace_at(cur, pos, apply_subst(dst, s2)) == nxt:
            return Step(k, direction, pos, nxt, {v: s2[v] for v in free} if free else None)
    return None


def prove(axioms: list, law: Law, timeout: float = 10.0):
    """Zwraca listę Step sprawdzoną przez proofcheck albo None (brak binarki, brak dowodu, dowód nieczytelny)."""
    exe = binary()
    if exe is None or not axioms:
        return None
    lines = [f"cnf(ax{i}, axiom, {_tptp(a[0], True)} = {_tptp(a[1], True)})." for i, a in enumerate(axioms)]
    lines.append(f"cnf(goal, negated_conjecture, {_tptp(law[0], False)} != {_tptp(law[1], False)}).")
    with tempfile.NamedTemporaryFile("w", suffix=".p", delete=False) as f:
        f.write("\n".join(lines) + "\n")
        path = f.name
    try:
        out = subprocess.run([exe, path, "--no-lemmas", "--quiet"], capture_output=True, text=True,
                             timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return None
    finally:
        os.unlink(path)
    if "The conjecture is true" not in out:
        return None
    body = out.split("Proof:", 1)[1] if "Proof:" in out else ""
    terms_, steps_raw = [], []
    for ln in body.splitlines():
        st = ln.strip()
        if not st:
            if terms_:
                break
            continue
        if st.startswith("= {"):
            m = re.search(r"axiom (\d+) \(ax(\d+)\)(?: (L->R|R->L))?", st)
            if not m:
                return None                      # krok przez coś innego niż nasz aksjomat
            steps_raw.append((int(m.group(2)), "rl" if m.group(3) == "R->L" else "lr"))
        elif st.startswith("RESULT"):
            break
        else:
            try:
                terms_.append(_parse(st))
            except ValueError:
                return None
    if len(terms_) != len(steps_raw) + 1 or terms_[0] != law[0] or terms_[-1] != law[1]:
        return None
    steps = []
    for (k, d), a, b in zip(steps_raw, terms_, terms_[1:]):
        s = _step(a, b, axioms, k, d) or _step(a, b, axioms, k, "lr" if d == "rl" else "rl")
        if s is None:
            return None
        steps.append(s)
    ok, _ = check_proof(law, axioms, steps)
    return steps if ok else None
