"""NPH* (baza nieredundantna) i Novelty N1.

Dwa rodzaje hipotez:
  1. Implikacje między własnościami nad klasą światów: frozenset(poprzednik) ⇒ następnik.
     Redundancja liczona dokładnie przez domknięcie Horna (obejmuje wzmocnienie poprzednika,
     przechodniość i koniunkcję w następniku).
  2. Prawa (tożsamości) w jednym świecie. Wynikanie równaniowe jest w ogólności
     nierozstrzygalne, więc podajemy PRZEDZIAŁ:
       górna granica NPH* – usuwamy tylko prawa będące podstawieniem innego (składniowo);
       dolna granica NPH* – usuwamy też prawa spełnione we wszystkich modelach referencyjnych
       pozostałych praw (wynikanie semantyczne na skończonej próbie modeli).
"""
from __future__ import annotations

from typing import Iterable

from .proofcheck import match
from .terms import Law, canonical, holds, is_trivial, mirror

Rule = tuple  # (frozenset[str], str)


# ---------- implikacje między własnościami ----------
def horn_closure(facts: Iterable[str], rules: Iterable[Rule]) -> set:
    known = set(facts)
    rules = list(rules)
    changed = True
    while changed:
        changed = False
        for ante, cons in rules:
            if cons not in known and ante <= known:
                known.add(cons)
                changed = True
    return known


def derivable(rule: Rule, others: Iterable[Rule]) -> bool:
    ante, cons = rule
    return cons in ante or cons in horn_closure(ante, others)


def nph_star_rules(accepted: list, initial: list = ()) -> list:
    """Baza nieredundantna. Kolejność listy = kolejność zgłoszeń; przy remisie zostaje wcześniejsza."""
    basis = list(accepted)
    for r in reversed(accepted):          # najpierw próbujemy usunąć późniejsze
        rest = [x for x in basis if x is not r] + list(initial)
        if derivable(r, rest):
            basis.remove(r)
    return basis


def novelty_n1(rule: Rule, initial: list) -> float:
    """Liczba rund wnioskowania w przód potrzebna, by z wiedzy początkowej wyprowadzić regułę.
    0 = trywialna, inf = niewyprowadzalna z wiedzy początkowej."""
    ante, cons = rule
    if cons in ante:
        return 0
    known, rnd = set(ante), 0
    while True:
        new = {c for a, c in initial if a <= known and c not in known}
        if not new:
            return float("inf")
        rnd += 1
        known |= new
        if cons in known:
            return rnd


# ---------- prawa w jednym świecie ----------
def is_instance(law: Law, general: Law) -> bool:
    """Czy `law` jest podstawieniem `general` (z orientacją stron i dualnością)?"""
    l, r = law
    for gl, gr in (general, general[::-1], (mirror(general[0]), mirror(general[1])),
                   (mirror(general[1]), mirror(general[0]))):
        s = match(gl, l, {})
        if s is not None and match(gr, r, s) is not None:
            return True
    return False


def nph_star_laws(accepted: list, initial: list = (), reference_models: list = ()) -> tuple:
    """Zwraca (dolna, górna) granicę NPH* dla praw przyjętych w świecie."""
    seen, uniq = {canonical(i) for i in initial}, []   # znane na starcie nie liczą się
    for law in accepted:
        c = canonical(law)
        if is_trivial(law) or c in seen:
            continue
        seen.add(c)
        uniq.append(law)

    upper = [law for i, law in enumerate(uniq)
             if not any(is_instance(law, g) for g in list(initial) + uniq[:i] + uniq[i + 1:]
                        if canonical(g) != canonical(law))]

    lower = list(upper)
    for law in reversed(upper):
        others = [x for x in lower if x is not law] + list(initial)
        models = [t for t in reference_models if all(holds(o, t) for o in others)]
        if models and all(holds(law, t) for t in models):
            lower.remove(law)
    return len(lower), len(upper)


def nph_star_laws_entail(accepted: list, initial: list = (), sizes=(2, 4, 5), node_limit: int = 20000):
    """Przedział NPH* oparty na prawdziwym sprawdzaczu wynikania (entail.py). Obie granice są pewne:

    górna = liczność zbioru po zachłannym usunięciu praw z DOWODEM wynikania z pozostałych
            (to nadal zbiór generujący, więc baza minimalna nie jest większa);
    dolna = liczba praw „niezbędnych”: z KONTRMODELEM względem wszystkich pozostałych naraz
            (każda baza będąca podzbiorem musi je zawierać).
    """
    from . import entail

    seen, uniq = {canonical(i) for i in initial}, []
    for law in accepted:
        c = canonical(law)
        if is_trivial(law) or c in seen:
            continue
        seen.add(c)
        uniq.append(law)

    upper = list(uniq)
    for law in reversed(uniq):
        rest = [x for x in upper if x is not law] + list(initial)
        if entail.prove(rest, law, node_limit=node_limit) is not None:
            upper.remove(law)

    essential = []
    for law in uniq:
        rest = [x for x in uniq if x is not law] + list(initial)
        if entail.countermodel(rest, law, sizes=sizes) is not None:
            essential.append(law)
    return len(essential), len(upper)
