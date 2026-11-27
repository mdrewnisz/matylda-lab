"""Sprawdzacz dowodów równaniowych (łańcuch przepisań).

Dowód zdania  l = r  z aksjomatów A_1..A_m to ciąg kroków. Krok = (i, kierunek, pozycja, wynik):
  * i: numer aksjomatu,
  * kierunek: "lr" (lewa strona -> prawa) albo "rl",
  * pozycja: krotka 0/1 (ścieżka do podtermu; 0 = lewy argument, 1 = prawy),
  * wynik: term po kroku (podawany jawnie, żeby błąd był wykrywalny).
Sprawdzacz sam dopasowuje podstawienie i porównuje wynik. Nic nie przyjmuje „na słowo”.
"""
from __future__ import annotations

from dataclasses import dataclass

from .terms import Law, Term, show


@dataclass
class Step:
    axiom: int
    direction: str
    position: tuple
    result: Term
    subst: dict | None = None   # wartości zmiennych występujących tylko po stronie docelowej


def match(pattern: Term, term: Term, subst: dict) -> dict | None:
    if isinstance(pattern, str):
        if pattern in subst:
            return subst if subst[pattern] == term else None
        s = dict(subst)
        s[pattern] = term
        return s
    if isinstance(term, str):
        return None
    s = match(pattern[0], term[0], subst)
    return None if s is None else match(pattern[1], term[1], s)


def apply_subst(t: Term, s: dict) -> Term:
    return s[t] if isinstance(t, str) else (apply_subst(t[0], s), apply_subst(t[1], s))


def subterm(t: Term, pos: tuple) -> Term:
    for p in pos:
        if isinstance(t, str):
            raise IndexError("pozycja poza termem")
        t = t[p]
    return t


def replace_at(t: Term, pos: tuple, new: Term) -> Term:
    if not pos:
        return new
    if isinstance(t, str):
        raise IndexError("pozycja poza termem")
    p, rest = pos[0], pos[1:]
    return (replace_at(t[0], rest, new), t[1]) if p == 0 else (t[0], replace_at(t[1], rest, new))


def _vars(t: Term, acc: set) -> set:
    if isinstance(t, str):
        acc.add(t)
    else:
        _vars(t[0], acc)
        _vars(t[1], acc)
    return acc


def check_proof(claim: Law, axioms: list, steps: list) -> tuple[bool, str]:
    cur = claim[0]
    for k, st in enumerate(steps):
        if not (0 <= st.axiom < len(axioms)):
            return False, f"krok {k}: brak aksjomatu {st.axiom}"
        if st.direction not in ("lr", "rl"):
            return False, f"krok {k}: zły kierunek {st.direction!r}"
        src, dst = axioms[st.axiom] if st.direction == "lr" else axioms[st.axiom][::-1]
        free = _vars(dst, set()) - _vars(src, set())
        if free - set((st.subst or {}).keys()):
            return False, f"krok {k}: strona docelowa ma zmienne wolne (podstawienie niejednoznaczne)"
        try:
            sub = subterm(cur, st.position)
        except IndexError:
            return False, f"krok {k}: pozycja {st.position} poza termem {show(cur)}"
        s = match(src, sub, {})
        if s is None:
            return False, f"krok {k}: aksjomat {st.axiom} nie pasuje do {show(sub)}"
        s = {**s, **{v: st.subst[v] for v in free}}
        nxt = replace_at(cur, st.position, apply_subst(dst, s))
        if nxt != st.result:
            return False, f"krok {k}: deklarowany wynik {show(st.result)} ≠ obliczony {show(nxt)}"
        cur = nxt
    if cur != claim[1]:
        return False, f"dowód kończy się na {show(cur)}, a nie na {show(claim[1])}"
    return True, "przyjęty"


def accept_proof(h, steps: list):
    """Jedyna droga do PROVED_FROM_AXIOMS. h: status.Hypothesis o zakresie U."""
    from .status import Scope, Status
    if h.scope is not Scope.U:
        raise ValueError("dowód z aksjomatów dotyczy zakresu U")
    ok, why = check_proof(h.claim, list(h.axioms), steps)
    if ok:
        h.status = Status.PROVED_FROM_AXIOMS
        h.certificate = {"proof_steps": len(steps), "checker": "proofcheck.check_proof"}
    return ok, why
