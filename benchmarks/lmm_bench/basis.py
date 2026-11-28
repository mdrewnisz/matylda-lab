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


def nph_star_laws_entail(accepted: list, initial: list = (), sizes=(2, 4, 5), node_limit: int = 20000,
                         packing: bool = True, fill_free: bool = True,
                         extra_ops=(2, 4), pairs: bool = False, use_twee: bool = True,
                         twee_timeout: float = 3.0):
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

    from . import twee as _twee
    tw = use_twee and _twee.binary() is not None

    def _provable(rest, law):
        if entail.prove(rest, law, extra_ops=extra_ops[0], node_limit=node_limit, fill_free=fill_free) is not None:
            return True
        if tw and _twee.prove(rest, law, timeout=twee_timeout) is not None:
            return True
        return any(entail.prove(rest, law, extra_ops=eo, node_limit=node_limit, fill_free=fill_free) is not None
                   for eo in extra_ops[1:])

    def greedy(order):
        up = list(uniq)
        for law in order:
            rest = [x for x in up if x is not law] + list(initial)
            # harmonogram: tani własny dowodnik, potem twee (dowód sprawdzany przez proofcheck),
            # potem szerszy własny dowodnik; pierwszy sukces kończy
            if _provable(rest, law):
                up = [x for x in up if x is not law]
        return up

    # Zachłanne usuwanie zależy od kolejności (mocniejszy dowodnik może dać WIĘKSZY zbiór).
    # Każdy wynik jest zbiorem generującym, więc minimum z dwóch kolejności też jest górną granicą.
    upper = min(greedy(list(reversed(uniq))), greedy(list(uniq)), key=len)

    essential = []
    for law in uniq:
        rest = [x for x in uniq if x is not law] + list(initial)
        if entail.countermodel(rest, law, sizes=sizes) is not None:
            essential.append(law)
    if not packing:
        return len(essential), len(upper)
    return len(essential) + _packing(uniq, essential, initial, sizes, pairs=pairs), len(upper)


def _packing(uniq, essential, initial, sizes, pairs: bool = True):
    """Dolna granica ponad prawa niezbędne E: minimalny zbiór trafiający zbiorów łamanych praw.

    Każda magma M spełniająca E ∪ wiedza początkowa i łamiąca któreś prawo z uniq daje zbiór
    V(M) = {l ∉ E : M łamie l} (niepusty). Każda baza B ⊆ uniq zawiera E i generuje wszystkie prawa,
    więc musi zawierać prawo łamane w M (inaczej M spełnia B, a więc i wszystko, co z B wynika).
    Zatem |B \ E| ≥ minimalny zbiór trafiający rodziny {V(M)}. Liczymy go DOKŁADNIE (SAT z ograniczeniem
    liczności), więc granica jest poprawna dla każdej zebranej rodziny; więcej małych zbiorów = ciaśniej.

    Rodzina: (1) dla każdego prawa L jeden kontrmodel względem E; (2) przy pairs=True dla każdej pary
    {L, L'} magma spełniająca E i WSZYSTKIE pozostałe prawa, łamiąca L lub L' (zbiór rozmiaru ≤ 2)."""
    from itertools import combinations

    from . import entail
    from .terms import holds

    base = list(essential) + list(initial)
    others = [l for l in uniq if not any(l is e for e in essential)]
    if not others:
        return 0
    sets = set()

    def add(m):
        v = frozenset(i for i, l in enumerate(others) if not holds(l, m))
        if v:
            sets.add(v)

    for law in others:
        m = entail.countermodel(base, law, sizes=sizes)
        if m is not None:
            add(m)
    if pairs:
        for i, j in combinations(range(len(others)), 2):
            rest = [l for k, l in enumerate(others) if k not in (i, j)]
            m = entail.countermodel_any(base + rest, [others[i], others[j]], sizes=sizes)
            if m is not None:
                add(m)
    return min_hitting_set(list(sets), len(others))


def min_hitting_set(sets: list, n: int) -> int:
    """Dokładna liczność minimalnego zbioru trafiającego (elementy 0..n-1)."""
    if not sets:
        return 0
    try:
        from pysat.card import CardEnc, EncType
        from pysat.solvers import Cadical153
    except ImportError:                     # bez pysat: przeszukanie wyczerpujące (dokładne, wolniejsze)
        from itertools import combinations
        for k in range(1, n + 1):
            for c in combinations(range(n), k):
                cs = set(c)
                if all(v & cs for v in sets):
                    return k
        return n
    lits = list(range(1, n + 1))
    for k in range(1, n + 1):
        enc = CardEnc.atmost(lits=lits, bound=k, top_id=n, encoding=EncType.seqcounter)
        with Cadical153(bootstrap_with=[[e + 1 for e in v] for v in sets] + enc.clauses) as sol:
            if sol.solve():
                return k
    return n
