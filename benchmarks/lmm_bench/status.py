"""Statusy epistemiczne z zakresem (specyfikacja 2.0, sekcja „Statusy epistemiczne”).

Zakres W: jeden świat (magma). Zakres K: rodzina światów w zadanym zakresie.
Zakres U: każda magma spełniająca aksjomaty.

Zasady twarde:
  * status zmienia tylko sprawdzacz (ten moduł albo proofcheck);
  * TRUE_IN_WORLD nigdy nie przechodzi w PROVED_FROM_AXIOMS;
  * sprawdzenie rodziny daje co najwyżej NIEOBALONA_W_ZAKRESIE;
  * kontrprzykład spełniający aksjomaty obala zdanie o zakresie U lub K (DISPROVED).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

import numpy as np

from .terms import Law, counterexample, holds, show_law


class Status(str, Enum):
    UNKNOWN = "UNKNOWN"
    TRUE_IN_WORLD = "TRUE_IN_WORLD"
    FALSE_IN_WORLD = "FALSE_IN_WORLD"
    NIEOBALONA_W_ZAKRESIE = "NIEOBALONA_W_ZAKRESIE"
    PROVED_FROM_AXIOMS = "PROVED_FROM_AXIOMS"
    DISPROVED = "DISPROVED"


class Scope(str, Enum):
    W = "W"
    K = "K"
    U = "U"


@dataclass
class Hypothesis:
    claim: Law
    scope: Scope
    axioms: tuple = ()          # prawa-założenia (dla K i U)
    status: Status = Status.UNKNOWN
    certificate: dict = field(default_factory=dict)

    def __str__(self) -> str:
        pre = " ∧ ".join(show_law(a) for a in self.axioms)
        return f"[{self.scope.value}] {pre + ' ⊢ ' if pre else ''}{show_law(self.claim)} : {self.status.value}"


def check_in_world(h: Hypothesis, table: np.ndarray, world_id: str = "") -> Hypothesis:
    if h.scope is not Scope.W:
        raise ValueError("check_in_world tylko dla zakresu W")
    cex = counterexample(h.claim, table)
    if cex is None:
        h.status = Status.TRUE_IN_WORLD
        h.certificate = {"world": world_id, "check": "wyczerpujące", "n": int(table.shape[0])}
    else:
        h.status = Status.FALSE_IN_WORLD
        h.certificate = {"world": world_id, "counterexample": cex}
    return h


def check_on_family(h: Hypothesis, family: Iterable, family_id: str = "") -> Hypothesis:
    """family: iterowalne par (id_świata, tabela). Światy niespełniające aksjomatów pomijamy."""
    if h.scope not in (Scope.K, Scope.U):
        raise ValueError("check_on_family dla zakresu K albo U")
    checked = 0
    for wid, table in family:
        if not all(holds(a, table) for a in h.axioms):
            continue
        checked += 1
        cex = counterexample(h.claim, table)
        if cex is not None:
            h.status = Status.DISPROVED
            h.certificate = {"family": family_id, "world": wid, "table": table.tolist(),
                             "counterexample": cex}
            return h
    if h.scope is Scope.K:
        h.status = Status.NIEOBALONA_W_ZAKRESIE if checked else Status.UNKNOWN
    # Zakres U: brak kontrprzykładu w rodzinie NIE zmienia statusu (tylko dowód może).
    h.certificate = {"family": family_id, "worlds_checked": checked}
    return h


def refute_universal(h: Hypothesis, table: np.ndarray, world_id: str = "") -> Hypothesis:
    """Asymetria: jeden świat spełniający aksjomaty i łamiący tezę obala zdanie o zakresie U."""
    if h.scope is not Scope.U:
        raise ValueError("refute_universal tylko dla zakresu U")
    if all(holds(a, table) for a in h.axioms):
        cex = counterexample(h.claim, table)
        if cex is not None:
            h.status = Status.DISPROVED
            h.certificate = {"world": world_id, "table": table.tolist(), "counterexample": cex}
    return h
