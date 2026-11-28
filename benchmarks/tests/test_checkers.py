"""Testy kontrolne sprawdzaczy: znane przypadki przyjęte, podrzucone błędy odrzucone."""
import numpy as np
import pytest

from lmm_bench import basis, controls, proofcheck, status, terms, worlds
from lmm_bench.proofcheck import Step
from lmm_bench.status import Hypothesis, Scope, Status
from lmm_bench.terms import parse_law, parse_term

Z4_ADD = (np.arange(4)[:, None] + np.arange(4)[None, :]) % 4          # grupa cykliczna
LEFT_PROJ = np.tile(np.arange(5)[:, None], (1, 5))                     # x*y = x


# ---------- DSL ----------
def test_parse_roundtrip_and_left_assoc():
    assert parse_term("x*y*z") == (("x", "y"), "z")
    law = parse_law("x*(y*x) = (x*y)*x")
    assert terms.show_law(law) == "x*(y*x) = (x*y)*x"
    with pytest.raises(terms.ParseError):
        parse_law("x*y")
    with pytest.raises(terms.ParseError):
        parse_term("x+y")


def test_canonical_identifies_renaming_orientation_and_dual():
    a = terms.canonical(parse_law("x*(x*y) = y"))
    assert terms.canonical(parse_law("b = a*(a*b)")) == a        # przemianowanie + orientacja
    assert terms.canonical(parse_law("(y*x)*x = y")) == a        # dualność
    assert terms.canonical(parse_law("x*(x*y) = y"), with_dual=False) != \
        terms.canonical(parse_law("(y*x)*x = y"), with_dual=False)


def test_eval_known_laws():
    assert terms.holds(parse_law("x*y = y*x"), Z4_ADD)
    assert terms.holds(parse_law("(x*y)*z = x*(y*z)"), Z4_ADD)
    assert not terms.holds(parse_law("x*x = x"), Z4_ADD)
    assert terms.holds(parse_law("x*y = x"), LEFT_PROJ)
    cex = terms.counterexample(parse_law("x*y = y*x"), LEFT_PROJ)
    assert cex is not None and LEFT_PROJ[cex["x"], cex["y"]] != LEFT_PROJ[cex["y"], cex["x"]]


def test_etp_range_flag():
    assert terms.in_etp_size_range(parse_law("x*(y*x) = (x*y)*x"))      # 4 operacje
    assert not terms.in_etp_size_range(parse_law("x*(y*(z*x)) = (x*y)*(z*x)"))


# ---------- światy ----------
def test_seed_and_size_policy():
    with pytest.raises(worlds.SeedPolicyError):
        worlds.random_magma(5, seed=10)
    with pytest.raises(worlds.SeedPolicyError):
        worlds.random_magma(5, seed=1020)
    with pytest.raises(worlds.SeedPolicyError):
        worlds.random_magma(3, seed=2000)
    w = worlds.random_magma(6, seed=2001)
    assert w.n == 6 and np.array_equal(w.table, worlds.random_magma(6, seed=2001).table)


def test_relabel_is_isomorphism_and_preserves_laws():
    perm = np.array([2, 0, 3, 1])
    t2 = worlds.relabeled(Z4_ADD, perm)
    for a in range(4):
        for b in range(4):
            assert t2[perm[a], perm[b]] == perm[Z4_ADD[a, b]]
    for s in ["x*y = y*x", "(x*y)*z = x*(y*z)", "x*x = x"]:
        assert terms.holds(parse_law(s), t2) == terms.holds(parse_law(s), Z4_ADD)


def test_affine_world_commutative_iff_a_equals_b():
    for seed in range(2000, 2030):
        w = worlds.affine_magma(5, seed)
        comm = terms.holds(parse_law("x*y = y*x"), w.table)
        assert comm == (w.params["a"] == w.params["b"])


# ---------- statusy ----------
def test_status_in_world():
    h = status.check_in_world(Hypothesis(parse_law("x*y = y*x"), Scope.W), Z4_ADD, "Z4")
    assert h.status is Status.TRUE_IN_WORLD
    h = status.check_in_world(Hypothesis(parse_law("x*x = x"), Scope.W), Z4_ADD, "Z4")
    assert h.status is Status.FALSE_IN_WORLD and "counterexample" in h.certificate


def test_family_gives_at_most_unrefuted_in_range():
    fam = [(str(p), t) for p, t in worlds.affine_family(4)]
    h = Hypothesis(parse_law("x*y = y*x"), Scope.K, axioms=(parse_law("x*y = y*x"),))
    assert status.check_on_family(h, fam).status is Status.NIEOBALONA_W_ZAKRESIE
    h = Hypothesis(parse_law("x*x = x"), Scope.K)
    assert status.check_on_family(h, fam).status is Status.DISPROVED


def test_universal_never_proved_by_checking():
    fam = [(str(p), t) for p, t in worlds.affine_family(4)]
    h = Hypothesis(parse_law("(x*y)*x = x*(y*x)"), Scope.U, axioms=(parse_law("x*y = y*x"),))
    status.check_on_family(h, fam)
    assert h.status is Status.UNKNOWN          # brak kontrprzykładu ≠ dowód


def test_world_counterexample_disproves_universal():
    h = Hypothesis(parse_law("x*y = y*x"), Scope.U, axioms=(parse_law("x*y = x"),))
    assert status.refute_universal(h, LEFT_PROJ, "proj").status is Status.DISPROVED


# ---------- dowody ----------
AX = [parse_law("x*(x*y) = y")]


def test_proof_accepted():
    # z x*(x*y) = y:   x*(x*(x*y)) = x*y   (aksjomat w korzeniu, y := x*y)
    claim = (parse_term("x*(x*(x*y))"), parse_term("x*y"))
    ok, why = proofcheck.check_proof(claim, AX, [Step(0, "lr", (), parse_term("x*y"))])
    assert ok, why
    # ten sam wynik przez przepisanie wewnątrz: pozycja (1,)
    ok, why = proofcheck.check_proof(claim, AX, [Step(0, "lr", (1,), parse_term("x*y"))])
    assert ok, why


@pytest.mark.parametrize("step,reason", [
    (Step(1, "lr", (), parse_term("x*y")), "brak aksjomatu"),
    (Step(0, "xx", (), parse_term("x*y")), "zły kierunek"),
    (Step(0, "lr", (0,), parse_term("x*y")), "nie pasuje"),
    (Step(0, "lr", (), parse_term("y")), "deklarowany wynik"),
    (Step(0, "rl", (), parse_term("x*y")), "zmienne wolne"),
    (Step(0, "lr", (1, 1, 1, 1), parse_term("x*y")), "poza termem"),
])
def test_planted_proof_errors_rejected(step, reason):
    claim = (parse_term("x*(x*(x*y))"), parse_term("x*y"))
    ok, why = proofcheck.check_proof(claim, AX, [step])
    assert not ok and reason in why


def test_empty_proof_of_false_claim_rejected():
    ok, why = proofcheck.check_proof(parse_law("x*y = y*x"), AX, [])
    assert not ok


def test_accept_proof_is_only_route_to_proved():
    h = Hypothesis((parse_term("x*(x*(x*y))"), parse_term("x*y")), Scope.U, axioms=tuple(AX))
    ok, _ = proofcheck.accept_proof(h, [Step(0, "lr", (), parse_term("y"))])
    assert not ok and h.status is Status.UNKNOWN
    ok, _ = proofcheck.accept_proof(h, [Step(0, "lr", (), parse_term("x*y"))])
    assert ok and h.status is Status.PROVED_FROM_AXIOMS


# ---------- NPH* i N1 ----------
def F(*a):
    return frozenset(a)


def test_nph_star_review_example_counts_one():
    # przykład z hostile review: A⇒B, A∧C⇒B, A∧C∧D⇒B, A∧C∧D∧E⇒B  -> NPH* = 1
    acc = [(F("A"), "B"), (F("A", "C"), "B"), (F("A", "C", "D"), "B"), (F("A", "C", "D", "E"), "B")]
    assert basis.nph_star_rules(acc) == [(F("A"), "B")]


def test_nph_star_order_and_transitivity():
    acc = [(F("A"), "B"), (F("B"), "C"), (F("A"), "C")]
    assert basis.nph_star_rules(acc) == [(F("A"), "B"), (F("B"), "C")]
    # wiedza początkowa unieważnia zgłoszenie
    assert basis.nph_star_rules([(F("A"), "C")], initial=[(F("A"), "B"), (F("B"), "C")]) == []


def test_novelty_n1():
    init = [(F("A"), "B"), (F("B"), "C")]
    assert basis.novelty_n1((F("A"), "A"), init) == 0
    assert basis.novelty_n1((F("A"), "C"), init) == 2
    assert basis.novelty_n1((F("A"), "D"), init) == float("inf")


def test_nph_star_laws_interval():
    refs = [t for _, t in worlds.affine_family(4)] + [t for _, t in worlds.affine_family(5)]
    acc = [parse_law("x*y = y*x"), parse_law("b*a = a*b"),           # duplikat po kanonizacji
           parse_law("(x*x)*y = y*(x*x)"),                           # podstawienie komutatywności
           parse_law("(x*y)*z = x*(y*z)")]
    lo, hi = basis.nph_star_laws(acc, reference_models=refs)
    assert hi == 2 and 1 <= lo <= hi


def test_nph_star_laws_excludes_initial_equivalents():
    init = [parse_law("y*x = x*y")]
    assert basis.nph_star_laws([parse_law("x*y = y*x")], initial=init) == (0, 0)
    assert basis.nph_star_laws([parse_law("(x*x)*y = y*(x*x)")], initial=init) == (0, 0)


# ---------- kontrole ----------
def test_controls_deterministic_and_capped():
    E = controls.enumerator_E(20)
    assert len(E) == 20 and E == controls.enumerator_E(20)
    assert all(terms.law_ops(a) <= terms.law_ops(b) for a, b in zip(E, E[1:]))
    R = controls.random_R0(20, seed=2000)
    assert len(R) == 20 and R == controls.random_R0(20, seed=2000) and R != controls.random_R0(20, seed=2001)
    ex = E[:5]
    assert not set(controls.enumerator_E(20, exclude=ex)) & {terms.canonical(e) for e in ex}


# ---------- sprawdzacz wynikania ----------
from lmm_bench import entail  # noqa: E402


@pytest.mark.parametrize("axioms,law,expected", [
    (["x*(x*y) = y"], "x*(x*(x*y)) = x*y", entail.PROVED),
    (["x*y = x"], "(x*y)*z = x*(y*z)", entail.PROVED),           # wymaga odwrócenia kroku z podstawieniem
    (["(x*y)*z = x*(y*z)", "x*y = y*x"], "(x*y)*z = (y*z)*x", entail.PROVED),
    (["x*y = y*x"], "(x*y)*z = x*(y*z)", entail.REFUTED),
    (["x*(x*y) = y"], "x*y = y", entail.REFUTED),
    ([], "x*x = x", entail.REFUTED),
])
def test_entailment_known_cases(axioms, law, expected):
    st, cert = entail.entails([parse_law(a) for a in axioms], parse_law(law))
    assert st == expected
    if st == entail.REFUTED:
        assert all(terms.holds(parse_law(a), cert) for a in axioms) and not terms.holds(parse_law(law), cert)
    if st == entail.PROVED:
        ok, _ = proofcheck.check_proof(parse_law(law), [parse_law(a) for a in axioms], cert)
        assert ok


def test_entailment_never_both_proved_and_refuted():
    pool = list(controls.law_pool(3))
    rng = np.random.default_rng(2000)
    for _ in range(60):
        a, b = (pool[i] for i in rng.choice(len(pool), 2, replace=False))
        steps = entail.prove([a], b, node_limit=3000)
        cm = entail.countermodel([a], b)
        assert not (steps is not None and cm is not None)


def test_nph_star_entail_bounds_sound():
    acc = [parse_law(s) for s in ["x*y = y*x", "(x*y)*z = x*(y*z)", "(x*y)*z = (y*z)*x"]]
    lo, hi = basis.nph_star_laws_entail(acc)
    assert lo <= hi == 2


# ---------- filtr ETP ----------
from lmm_bench import etp  # noqa: E402


def test_etp_list_loads_and_covers_pool():
    assert len(etp.etp_canonical()) == 2389            # 4694 wpisy, pary dualne sklejone
    assert etp.etp_ids(parse_law("x = x")) == [1]
    assert etp.in_etp(parse_law("x*(y*z) = (x*y)*z"))   # łączność
    # cała pula D1 (≤ 4 operacje, ≤ 3 zmienne) leży w ETP: wariant N wymaga praw spoza tej puli
    assert all(etp.in_etp(l) for l in controls.law_pool(4))
    assert not etp.in_etp(parse_law("x*(y*(z*x)) = (x*y)*(z*x)"))   # 5 operacji


def test_packing_lower_bound():
    # pakowanie nigdy nie obniża granicy i nie przekracza górnej
    acc = [parse_law(s) for s in ["x*y = y*x", "(x*y)*z = x*(y*z)", "(x*y)*z = (y*z)*x", "x*x = x"]]
    lo0, hi0 = basis.nph_star_laws_entail(acc, packing=False)
    lo, hi = basis.nph_star_laws_entail(acc)
    assert lo0 <= lo <= hi == hi0
    # niezależne: komutatywność i idempotentność
    assert basis.nph_star_laws_entail([parse_law("x*y = y*x"), parse_law("x*x = x")]) == (2, 2)
    # zbiór praw równoważnych bez prawa niezbędnego: dolna granica co najmniej 1
    eq = [parse_law("x*y = y*x"), parse_law("(x*y)*z = z*(x*y)")]
    assert basis._packing(eq, [], [], (2, 4)) >= 1


# ---------- D1' ----------
from lmm_bench import d1prime  # noqa: E402

FAM, HELD = d1prime.make_family(2100), d1prime.make_family(2101)


def test_d1prime_family_deterministic_and_mixed():
    assert len(FAM) == 20 and all(5 <= w.n <= 7 for w in FAM)
    assert {w.kind for w in FAM} == {"afiniczna", "izotop", "jednoargumentowa", "losowa"}
    again = d1prime.make_family(2100)
    assert all(np.array_equal(a.table, b.table) for a, b in zip(FAM, again))


@pytest.mark.parametrize("law,ok,reason", [
    ("x*y = x*z", True, "nowe"),
    ("(x*y)*z = (x*z)*y", True, "nowe"),
    ("x*y = y*x", False, "równoważne pojęciu"),           # podane pojęcie
    ("(x*x)*y = y*(x*x)", False, "równoważne pojęciu"),   # inna składnia, ta sama sygnatura
    ("x*(y*z) = x*(y*w)", False, "składnia"),             # 4 zmienne
    ("x = x*x*x*x*x*x", False, "składnia"),               # głębokość 5
    ("x*y = y*x*x*x*x*x", False, "składnia"),
])
def test_d1prime_concept_conditions(law, ok, reason):
    v = d1prime.check_concept(parse_law(law), FAM, HELD)
    assert v.ok_new is ok and reason in v.reason


def test_d1prime_constant_concept_rejected():
    v = d1prime.check_concept(parse_law("(x*y)*(z*x) = (x*z)*(y*x)"), FAM, HELD)
    if all(v.sig) or not any(v.sig):
        assert not v.ok_new and "stałe" in v.reason


def test_d1prime_implications():
    P = parse_law
    v = d1prime.check_implication([P("x*y = y*x")], P("x*x = x"), FAM, HELD)
    assert v.status is Status.DISPROVED and isinstance(v.certificate, int)
    w = (FAM + HELD)[v.certificate].table
    assert terms.holds(P("x*y = y*x"), w) and not terms.holds(P("x*x = x"), w)
    v = d1prime.check_implication([P("x*y = x*z")], P("(x*y)*z = (x*w)*z"), FAM, HELD)
    assert v.trivial and "podstawieniem" in v.reason
    v = d1prime.check_implication([P("x*y = y*x"), P("(x*y)*z = x*(y*z)")], P("(x*y)*z = (y*z)*x"), FAM, HELD)
    assert v.status is Status.NIEOBALONA_W_ZAKRESIE and v.proved     # dowód z aksjomatów też sprawdzony


def test_d1prime_score_counts_only_used_new_concepts():
    P = parse_law
    new = P("x*y = x*z")                     # „lewa stałość”: wynik nie zależy od prawego argumentu
    imps = [([new], P("(x*y)*z = (x*z)*y")), ([new], P("x*y = y*x"))]
    res = d1prime.score([new, P("x*y = y*x")], imps, FAM, HELD)
    assert res["pojecia_nowe"] == 1
    good = [v for v in res["werdykty_implikacji"] if v.status is Status.NIEOBALONA_W_ZAKRESIE and not v.trivial]
    assert res["pojecia_zaliczone"] == (1 if good else 0)
    assert res["nph_star_reguly"] <= res["implikacje_dobre"]
    # wariant N: pojęcie z listy ETP się nie liczy
    assert d1prime.score([new], imps, FAM, HELD, variant_N=True)["pojecia_nowe"] == 0


def test_prover_instantiates_free_variables():
    # x*y = x*z (wynik nie zależy od prawego argumentu) ⊨ (x*y)*z = (x*z)*y:
    # oba kierunki aksjomatu wprowadzają zmienną wolną, dowodnik musi ją jawnie podstawić
    ax, law = [parse_law("x*y = x*z")], parse_law("(x*y)*z = (x*z)*y")
    steps = entail.prove(ax, law)
    assert steps is not None
    assert proofcheck.check_proof(law, ax, steps)[0]


def test_d1prime_semantic_duplicates_count_once():
    P = parse_law
    a, b = P("(x*x)*y = x"), P("(x*y)*x = x")          # różna składnia, ta sama sygnatura na F ∪ H
    assert d1prime.signature(a, FAM + HELD) == d1prime.signature(b, FAM + HELD)
    assert d1prime.check_concept(a, FAM, HELD).ok_new and d1prime.check_concept(b, FAM, HELD).ok_new
    assert d1prime.score([a, b], [], FAM, HELD)["pojecia_nowe"] == 1


def test_min_hitting_set_exact():
    assert basis.min_hitting_set([frozenset({0, 1}), frozenset({1, 2}), frozenset({3})], 4) == 2
    assert basis.min_hitting_set([frozenset({0}), frozenset({1}), frozenset({2})], 3) == 3
    assert basis.min_hitting_set([], 5) == 0


def test_countermodel_any_breaks_one_of_several():
    ax = [parse_law("x*y = y*x")]
    laws = [parse_law("(x*y)*z = x*(y*z)"), parse_law("x*x = x")]
    t = entail.countermodel_any(ax, laws)
    assert t is not None and terms.holds(ax[0], t) and any(not terms.holds(l, t) for l in laws)
    assert entail.countermodel_any([parse_law("x*y = x")], [parse_law("(x*y)*z = x")]) is None


def test_hitting_set_and_countermodel_any_without_pysat(monkeypatch):
    import builtins
    real = builtins.__import__

    def fake(name, *a, **k):
        if name.startswith("pysat"):
            raise ImportError(name)
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", fake)
    assert basis.min_hitting_set([frozenset({0, 1}), frozenset({1, 2}), frozenset({3})], 4) == 2
    ax = [parse_law("x*y = y*x")]
    t = entail.countermodel_any(ax, [parse_law("x*x = x")])
    assert t is not None and t.shape == (2, 2) and terms.holds(ax[0], t)


# ---------- twee (zewnętrzny prover, dowody sprawdzane przez proofcheck) ----------
from lmm_bench import twee  # noqa: E402

needs_twee = pytest.mark.skipif(twee.binary() is None, reason="brak binarki twee (narzedzia/pobierz_twee.sh)")


@needs_twee
@pytest.mark.parametrize("axioms,law", [
    (["x*y = x*z"], "(x*y)*z = (x*z)*y"),
    (["x*y = x"], "(x*y)*z = x*(y*z)"),
    (["x*y = y*x", "(x*y)*z = x*(y*z)"], "(x*y)*z = (y*z)*x"),
])
def test_twee_proofs_pass_our_checker(axioms, law):
    ax, L = [parse_law(a) for a in axioms], parse_law(law)
    steps = twee.prove(ax, L, timeout=5)
    assert steps is not None and proofcheck.check_proof(L, ax, steps)[0]


@needs_twee
def test_twee_false_entailment_gives_none():
    assert twee.prove([parse_law("x*y = y*x")], parse_law("(x*y)*z = x*(y*z)"), timeout=2) is None


def test_twee_missing_binary_is_none(monkeypatch):
    monkeypatch.setenv("TWEE", "/nie/ma/takiej/binarki")
    twee.binary.cache_clear()
    try:
        assert twee.prove([parse_law("x*y = x")], parse_law("(x*y)*z = x")) is None
    finally:
        monkeypatch.delenv("TWEE")
        twee.binary.cache_clear()


def test_nph_star_entail_empty_extra_ops():
    acc = [parse_law("x*y = y*x"), parse_law("(x*x)*y = y*(x*x)")]
    lo, hi = basis.nph_star_laws_entail(acc, extra_ops=())
    assert 1 <= lo <= hi <= 2


def test_min_hitting_set_witness_hits_all():
    sets = [frozenset({0, 1}), frozenset({1, 2}), frozenset({3})]
    h = basis.min_hitting_set_witness(sets, 4)
    assert len(h) == 2 and all(v & h for v in sets)


def test_cegar_basis_exact_on_known_cases():
    P = parse_law

    def prov(base, law):
        return entail.prove(base, law, node_limit=5000) is not None
    # komutatywność generuje swoje podstawienie: baza = 1
    lo, hi, B = basis.cegar_basis([P("x*y = y*x"), P("(x*x)*y = y*(x*x)")], [], (2, 4), prov)
    assert lo == hi == 1 and B == [P("x*y = y*x")]
    # dwa niezależne prawa: baza = 2
    lo, hi, B = basis.cegar_basis([P("x*y = y*x"), P("x*x = x")], [], (2, 4), prov)
    assert lo == hi == 2
    # dolna nigdy nie przekracza górnej
    acc = [P(s) for s in ["x*y = y*x", "(x*y)*z = x*(y*z)", "(x*y)*z = (y*z)*x", "x*x = x"]]
    lo, hi, _ = basis.cegar_basis(acc, [], (2, 4), prov)
    assert lo <= hi
