"""Prototyp rdzenia Matyldy: czuwanie → sen → przebudzenie → seed w Praxis, sklejony z istniejących części.

    python -m matylda_rdzen.prototyp --prawo łączna --rzad 3 --ziarno 0 --wyj /ścieżka/katalog

Co robi (bez nowych mechanizmów):
1. `petla.uruchom` (ramię S, protokół S-1b: dzień 1 do 300 wywołań, sen 50, domyślna intuicja = heurystyka grafu).
2. Każda intuicja z przebudzenia staje się rekordem Praxis w stanie SEED (`HypothesisRecord.seed`, magazyn SQLite Praxis),
   z genealogią: skąd przyszła (powtórka / śmiałe przeczucie), w którym cyklu, z jakim wsparciem.
3. Werdykt weryfikatora z następnego czuwania jest dopisywany obok, w słowniku statusów rdzenia:
   OBALONA (wynik negatywny snu) / NIEOBALONA_W_ZAKRESIE (tylko na |W_H| magmach świata) / WYNIKA_Z_WIEDZY / NIEROZSTRZYGNIĘTA.
   Stanu rekordu w Praxis sen ani weryfikator NIE zmieniają: przejście SEED → dalej należy do protokołu Praxis i człowieka.
Bez Praxis (brak pakietu) seedy trafiają tylko do JSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pamiec import OBALONA, SKONTROWANA
from .petla import DOMYSLNY_WZOR, uruchom
from .praxis_most import praxis_dostepny
from .s1 import CEX, SLOWNIK
from .s1b import BUDZET_DNIA, BUDZET_SNU

STATUS = {SKONTROWANA: "NIEOBALONA_W_ZAKRESIE", OBALONA: "OBALONA"}


def werdykt(p, a, b):
    if (a, b) in p.status:
        return STATUS[p.status[(a, b)]]
    if p.wynika(a, b):
        return "WYNIKA_Z_WIEDZY"          # pominięta w czuwaniu: wynika z już skontrowanych krawędzi
    return "NIEROZSTRZYGNIĘTA"


def prototyp(prawo: str, rzad: int = 3, ziarno: int = 0, wyj: str | Path | None = None,
             budzet_dnia: int = BUDZET_DNIA, budzet_snu: int = BUDZET_SNU) -> dict:
    pr = uruchom(prawo, ziarno, "S", budzet=budzet_dnia, budzet_snu=budzet_snu, rzad=rzad, slownik=SLOWNIK, cex_cap=CEX)
    p = pr.pamiec
    tytul = lambda s: f"{s.a} ⇒ {s.b} (świat: magmy rzędu {rzad} z prawem {prawo})"  # noqa: E731
    wpisy = [{"tytul": tytul(s), "a": s.a, "b": s.b, "genealogia": {"zrodlo": s.zrodlo, "cykl": s.cykl, "wsparcie": s.wsparcie},
              "werdykt_weryfikatora": werdykt(p, s.a, s.b)} for s in pr.seedy]
    praxis = None
    if wyj is not None:
        wyj = Path(wyj)
        wyj.mkdir(parents=True, exist_ok=True)
        if praxis_dostepny():
            from matylda_praxis.adapters.sqlite import SQLiteArtifactRepository
            from matylda_praxis.domain.models import HypothesisRecord
            repo = SQLiteArtifactRepository(wyj / "praxis.sqlite3")
            for w in wpisy:
                rec = HypothesisRecord.seed(w["tytul"])
                repo.save(rec, expected_revision=None)
                w["praxis_id"], w["praxis_stan"] = rec.id, rec.state.value
            praxis = {"magazyn": str(wyj / "praxis.sqlite3"), "rekordow": len(repo.list())}
    licz = {k: sum(w["werdykt_weryfikatora"] == k for w in wpisy) for k in ("OBALONA", "NIEOBALONA_W_ZAKRESIE", "WYNIKA_Z_WIEDZY", "NIEROZSTRZYGNIĘTA")}
    out = {"prawo": prawo, "rzad": rzad, "ziarno": ziarno, "intuicja": f"heurystyka grafu [{DOMYSLNY_WZOR}]",
           "wywolania": pr.wywolania, "cykle": pr.cykle, "koniec_dnia1": pr.dziennik.koniec_dnia1,
           "pokrycie_TR": pr.dziennik.krzywa[-1][1] if pr.dziennik.krzywa else 0, "seedy": len(wpisy), "werdykty": licz,
           "praxis": praxis, "wpisy": wpisy}
    if wyj is not None:
        (wyj / "przebudzenie.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prawo", default="łączna")
    ap.add_argument("--rzad", type=int, default=3)
    ap.add_argument("--ziarno", type=int, default=0)
    ap.add_argument("--wyj", default="wyniki/prototyp")
    a = ap.parse_args()
    o = prototyp(a.prawo, a.rzad, a.ziarno, a.wyj)
    print(json.dumps({k: v for k, v in o.items() if k != "wpisy"}, ensure_ascii=False, indent=1))
