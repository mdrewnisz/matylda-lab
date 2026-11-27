"""Wybór praw dla testu rzędu 3 według rozmiaru świata (PREREJESTRACJA_ROZMIAR3.md).
Klasa większych termów (jak PRZYROST), generator ziarno 9494 (jedyne użyte). Filtr tylko w rzędzie 3 (test nie dotyczy rzędu 4):
|TR| ≥ 15, rozmiar w jednym z przedziałów MALE = [20, 300] lub DUZE = [500, ∞) (luka 301–499 celowo pominięta); prawo i świat
(oraz jego transpozycja) bez Jaccarda ≥ 0,5 z żadnym zużytym światem rzędu 3 i bez zawierania świata prawa testowanego.
Lista zakazana = lista z przyrost_wybor_praw + 5 praw walidacyjnych PRZYROST + 10 praw pilota PRZYROST.
    python -m matylda_rdzen.rozmiar3_wybor_praw   → wyniki/rozmiar3_prawa.json
"""
import json

from .heur4_dev import swiaty_dev
from .heur4_walidacja import PRAWA as PRAWA_HEUR4
from .lmm_trening import _L, _S
from .przyrost_dev import swiaty_dev3
from .przyrost_walidacja import PRAWA as PRAWA_PRZYROST
from .przyrost_wybor_praw import losuj_prawa_duze, zb
from .s1 import PRAWA_MOCY, ROOT
from .swiat import PRAWA_S0

ZIARNO = 9494
NA_PRZEDZIAL = 7       # 5 + 2 rezerwowe (B4 recenzji): do analizy wchodzi pierwszych 5 ważnych w kolejności generatora
MALE, DUZE = (20, 300), (500, 10 ** 9)


def przedzial(n):
    return "male" if MALE[0] <= n <= MALE[1] else "duze" if n >= DUZE[0] else None


def main():
    pilot = [H for H, _ in json.loads((ROOT / "wyniki" / "przyrost_pilot_prawa.json").read_text(encoding="utf-8"))]
    L3 = [H for H, *_ in json.load(open(ROOT / "dane" / "swiaty_v3.json"))]
    spent = list(dict.fromkeys(list(PRAWA_S0) + list(PRAWA_MOCY) + _L + _S + L3 + swiaty_dev(120) + list(PRAWA_HEUR4)
                               + swiaty_dev3(40) + list(PRAWA_PRZYROST) + pilot))
    TESTOWANE = set(PRAWA_S0) | set(PRAWA_MOCY) | set(PRAWA_HEUR4) | set(PRAWA_PRZYROST)
    ref = []
    for H in spent:
        a, at, _ = zb(H, 3)
        if a:
            ref.append((H, a, at))
    out, lic = {"male": [], "duze": []}, {}
    for H in losuj_prawa_duze(20000, ZIARNO):
        if all(len(v) >= NA_PRZEDZIAL for v in out.values()):
            break
        if H in spent:
            continue
        a, at, sw = zb(H, 3)
        p = przedzial(len(sw.world))
        if len(sw.TR) < 15 or p is None:
            lic["rozmiar"] = lic.get("rozmiar", 0) + 1
            continue
        if len(out[p]) >= NA_PRZEDZIAL:
            continue
        jmax, zly = 0.0, False
        for H2, b, bt in ref:
            for x in (a, at):
                j = len(x & b) / len(x | b)
                jmax = max(jmax, j)
                if j >= 0.5 or (H2 in TESTOWANE and b <= x):
                    zly = True
        if zly:
            lic["jaccard_lub_nadzbior"] = lic.get("jaccard_lub_nadzbior", 0) + 1
            continue
        out[p].append((H, len(sw.world), len(sw.TR), round(jmax, 3)))
        ref.append((H, a, at))
    return {"ziarno": ZIARNO, "prawa": out, "odrzucenia": lic}


if __name__ == "__main__":
    w = main()
    (ROOT / "wyniki" / "rozmiar3_prawa.json").write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(w, ensure_ascii=False))
