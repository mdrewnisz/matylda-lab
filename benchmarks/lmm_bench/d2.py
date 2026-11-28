"""Klasa D2: indukcja i generalizacja (sprawdzacz przed modelem).

Zadanie: rodzina parametryczna x*y = P(x, y) mod n, gdzie P jest ukrytym wielomianem
o współczynnikach całkowitych (afinicznym albo kwadratowym), wspólnym dla wszystkich n.
Ramię widzi tylko tabele dla n ∈ UCZACE (4 ≤ n ≤ N0 = 12) i zgłasza:
  (i)  regułę wykonywalną: współczynniki (a, b, c, d, e, f) wielomianu
       a·x² + b·x·y + c·y² + d·x + e·y + f; predykcje = tabele dla n ∈ TESTOWE;
  (ii) do K praw równaniowych, które według niego zachodzą dla KAŻDEGO n w rodzinie.

Prawda podstawowa (spec 2.0: „niezależny generator dla N0 < n ≤ N1”) liczy osobna ścieżka
kodu (_tabela_niezalezna: czysty Python, bez numpy), więc błąd generatora uczącego nie
przenosi się automatycznie na ocenę.

Ocena:
  * generalizacja = ułamek n ∈ TESTOWE (13..40, 28 przypadków), w których predykcja jest równa
    prawdziwej tabeli;
  * prawo przyjęte = zachodzi na wszystkich tabelach UCZACE ∪ TESTOWE; status
    NIEOBALONA_W_ZAKRESIE (zakres K: ta rodzina, n ≤ N1);
  * NPH* = zamrożony sprawdzacz (zamrozenie.nph_zamrozone) na przyjętych prawach.

Polityka rozmiarów D2 (PROPOZYCJA, do zatwierdzenia z prerejestracją): n = 2 i n = 3 wyłączone
w całości (n = 3 zablokowane do czasu KG-1; n = 2 pominięte dla spójności z MIN_SIZE światów).
Ziarna rodzin D2: od 2200.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from . import controls
from .terms import canonical, holds

N0, N1 = 12, 40
UCZACE = tuple(range(4, N0 + 1))
TESTOWE = tuple(range(N0 + 1, N1 + 1))
SEEDS_FROM = 2200
COEF_MAX = 5                       # wersja 1: współczynniki z {0, …, COEF_MAX}
L = 27720                          # lcm(4..12): wersja 2, współczynniki mod L


@dataclass(frozen=True)
class Rodzina:
    seed: int
    kind: str                       # "afiniczna" | "kwadratowa"
    coefs: tuple                    # (a, b, c, d, e, f)
    wersja: int = 1


def make_family(seed: int, wersja: int = 2) -> Rodzina:
    """Wersja 1 (spec 2.0): współczynniki 0–5 – pilot 2026-11-28 pokazał, że pełne przeszukanie ją
    rozwiązuje (WYNIK NEGATYWNY). Wersja 2 (PROPOZYCJA): a, c ∈ [0, L/2), b, d, e, f ∈ [0, L).
    Ograniczenie a, c < L/2 usuwa jedyną niejednoznaczność: (L/2)·x(x−1) ≡ 0 mod każdego n | L."""
    if seed < SEEDS_FROM:
        raise ValueError(f"ziarno D2 {seed} < {SEEDS_FROM}")
    if wersja == 2:
        return _make_family_v2(seed)
    rng = np.random.default_rng(seed)
    kind = "afiniczna" if seed % 2 == 0 else "kwadratowa"
    while True:
        a, b, c = (int(v) for v in rng.integers(0, COEF_MAX + 1, size=3)) if kind == "kwadratowa" else (0, 0, 0)
        d, e, f = (int(v) for v in rng.integers(0, COEF_MAX + 1, size=3))
        if kind == "kwadratowa" and a == b == c == 0:
            continue
        if d == e == 0 and a == b == c == 0:           # stała: zadanie trywialne
            continue
        return Rodzina(seed, kind, (a, b, c, d, e, f))


def _make_family_v2(seed: int) -> Rodzina:
    rng = np.random.default_rng([seed, 2])
    kind = "afiniczna" if seed % 2 == 0 else "kwadratowa"
    h = L // 2
    while True:
        if kind == "kwadratowa":
            a, c = (int(v) for v in rng.integers(0, h, size=2))
            b = int(rng.integers(0, L))
        else:
            a = b = c = 0
        d, e, f = (int(v) for v in rng.integers(0, L, size=3))
        if kind == "kwadratowa" and a == b == c == 0:
            continue
        if a == b == c == d == e == 0:
            continue
        return Rodzina(seed, kind, (a, b, c, d, e, f), wersja=2)


def tabela(coefs: tuple, n: int) -> np.ndarray:
    """Generator uczący (numpy)."""
    if n < 4:
        raise ValueError("D2: n < 4 wyłączone (polityka rozmiarów)")
    a, b, c, d, e, f = coefs
    x = np.arange(n)[:, None]
    y = np.arange(n)[None, :]
    return ((a * x * x + b * x * y + c * y * y + d * x + e * y + f) % n).astype(np.int64)


def _tabela_niezalezna(coefs: tuple, n: int) -> list:
    """Niezależny generator prawdy dla testu: pętle w czystym Pythonie, schemat Hornera."""
    a, b, c, d, e, f = coefs
    out = []
    for x in range(n):
        row = []
        for y in range(n):
            v = ((a * x + b * y + d) * x + (c * y + e) * y + f) % n
            row.append(v)
        out.append(row)
    return out


def uczace(fam: Rodzina) -> dict:
    return {n: tabela(fam.coefs, n) for n in UCZACE}


def generalizacja(fam: Rodzina, coefs_zgloszone) -> float:
    if coefs_zgloszone is None:
        return 0.0
    ok = 0
    for n in TESTOWE:
        pred = tabela(tuple(int(v) for v in coefs_zgloszone), n).tolist()
        ok += pred == _tabela_niezalezna(fam.coefs, n)
    return ok / len(TESTOWE)


def prawo_w_rodzinie(law, fam: Rodzina) -> bool:
    for n in UCZACE + TESTOWE:
        t = np.array(_tabela_niezalezna(fam.coefs, n), dtype=np.int64) if n in TESTOWE else tabela(fam.coefs, n)
        if not holds(law, t):
            return False
    return True


def score(fam: Rodzina, coefs_zgloszone, prawa: list, K: int, nph=None) -> dict:
    """nph: funkcja (przyjęte) -> (dolna, górna); domyślnie zamrożony sprawdzacz NPH-1."""
    if nph is None:
        from .zamrozenie import nph_zamrozone as nph
    prawa = prawa[:K]
    uniq = list(dict.fromkeys(canonical(l) for l in prawa))
    acc = [l for l in uniq if prawo_w_rodzinie(l, fam)]
    lo, hi = nph(acc) if acc else (0, 0)
    return {"generalizacja": generalizacja(fam, coefs_zgloszone), "prawa_zgloszone": len(prawa),
            "prawa_przyjete": len(acc), "precyzja": len(acc) / len(uniq) if uniq else None,
            "nph_lo": lo, "nph_hi": hi}


# ---------- ramiona bez modelu ----------
def _crt(res: dict, lo: int = 0, hi: int = L):
    """Jedyna wartość v ∈ [lo, hi) z v ≡ res[n] (mod n) dla wszystkich n, albo None."""
    v = np.arange(lo, hi)
    ok = np.ones(len(v), bool)
    for n, r in res.items():
        ok &= (v % n) == r
    idx = np.flatnonzero(ok)
    return int(v[idx[0]]) if len(idx) == 1 else None


def solve_crt(train: dict):
    """Punkt odniesienia C' dla wersji 2: współczynniki z tabel przez reszty mod n i CRT.
    Dla każdego n: f = T[0,0]; para (a, d) z kolumny y = 0, para (c, e) z wiersza x = 0, b z T[1,1].
    a (i c) wybierane z [0, L/2) zgodnie ze wszystkimi n, reszta wyznaczona jednoznacznie."""
    ns = sorted(train)
    f = _crt({n: int(train[n][0, 0]) for n in ns})
    if f is None:
        return None
    def pair(get):
        # dopuszczalne reszty a mod n: istnieje d z a·x² + d·x + f ≡ T(x) dla wszystkich x
        allowed = {}
        for n in ns:
            t = np.array([get(train[n], x) for x in range(n)])
            xs = np.arange(n)
            allowed[n] = {a for a in range(n)
                          if np.array_equal((a * xs * xs + ((int(t[1]) - a - f) % n) * xs + f) % n, t)}
        v = np.arange(L // 2)
        ok = np.ones(len(v), bool)
        for n in ns:
            ok &= np.isin(v % n, sorted(allowed[n]))
        cands = np.flatnonzero(ok)
        if len(cands) != 1:
            return None
        a = int(cands[0])
        d = _crt({n: (int(get(train[n], 1)) - a - f) % n for n in ns})
        return None if d is None else (a, d)
    ad = pair(lambda T, x: T[x, 0])
    ce = pair(lambda T, y: T[0, y])
    if ad is None or ce is None:
        return None
    (a, d), (c, e) = ad, ce
    b = _crt({n: (int(train[n][1, 1]) - a - c - d - e - f) % n for n in ns})
    if b is None:
        return None
    co = (a, b, c, d, e, f)
    return co if all(np.array_equal(tabela(co, n), train[n]) for n in ns) else None


def arm_C(train: dict, K: int, max_ops: int = 4, wersja: int = 2):
    """Pętla narzędziowa: (i) przeszukanie współczynników zgodnych ze WSZYSTKIMI tabelami uczącymi
    (pierwszy zgodny w kolejności leksykograficznej); (ii) prawa z puli ≤ max_ops działań, które
    zachodzą we wszystkich tabelach uczących, w kolejności puli, do K."""
    ns = sorted(train)
    found = None
    if wersja == 2:
        found = solve_crt(train)
    else:
        for co in itertools.product(np.arange(COEF_MAX + 1), repeat=6):
            if all(np.array_equal(tabela(co, n), train[n]) for n in ns):
                found = tuple(int(v) for v in co)
                break
    laws = []
    for l in controls.law_pool(max_ops):
        if all(holds(l, train[n]) for n in ns):
            laws.append(l)
            if len(laws) >= K:
                break
    return found, laws


def arm_E(K: int, max_ops: int = 4):
    """Enumerator: reguła x+y (najprostsza nietrywialna afiniczna), prawa = pierwsze K z puli."""
    return (0, 0, 0, 1, 1, 0), controls.enumerator_E(K, max_ops=max_ops)


def arm_R0(K: int, seed: int, max_ops: int = 4, wersja: int = 2):
    # osobny strumień: to samo ziarno co make_family odtworzyłoby ukryte współczynniki (błąd pilota 1)
    rng = np.random.default_rng([seed, 0xD2])
    top = COEF_MAX + 1 if wersja == 1 else L // 2
    return tuple(int(v) for v in rng.integers(0, top, size=6)), controls.random_R0(K, seed, max_ops=max_ops)


def run_pilot(seeds, K: int = 20, wersja: int = 2):
    from . import zamrozenie
    zamrozenie.sprawdz()
    rows = []
    for s in seeds:
        fam = make_family(s, wersja)
        tr = uczace(fam)
        rec = {"seed": s, "kind": fam.kind}
        for name, (co, laws) in (("C", arm_C(tr, K, wersja=wersja)), ("E", arm_E(K)),
                                 ("R0", arm_R0(K, s, wersja=wersja))):
            rec[name] = score(fam, co, laws, K)
        rows.append(rec)
    return {"meta": {"K": K, "N0": N0, "N1": N1, "uczace": list(UCZACE), "testowe": list(TESTOWE),
                     "wersja": wersja, "COEF_MAX": COEF_MAX if wersja == 1 else L, "sprawdzacz_nph": zamrozenie.opis(),
                     "uwaga": "PILOT D2, nie test"}, "rodziny": rows}
