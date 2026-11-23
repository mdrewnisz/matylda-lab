import json
from pathlib import Path

import numpy as np
import pytest

from matylda_rdzen.fazy import SenPelny
from matylda_rdzen.intuicja import HeurystykaOgolnosci, IntuicjaLMM, Kandydat, KontekstIntuicji
from matylda_rdzen.pamiec import SKONTROWANA, Pamiec, Weryfikator
from matylda_rdzen.petla import RAMIONA, uruchom
from matylda_rdzen.praxis_most import do_json, do_praxis, praxis_dostepny
from matylda_rdzen.swiat import PRAWA_S0, zbuduj_swiat

FIX = Path(__file__).parent / "kg0b_A2.json"


def test_czuwanie_odtwarza_kg0b():
    """Ramię A2 musi odtwarzać KG-0b co do krzywej (regresja przeniesienia kodu)."""
    for r in json.loads(FIX.read_text(encoding="utf-8")):
        pr = uruchom(r["H"], r["seed"], "A2", budzet=10 ** 6)
        assert pr.wywolania == r["calls"]
        assert [list(x) for x in pr.dziennik.krzywa] == r["curve"]


def test_weryfikator_nie_myli_sie():
    sw = zbuduj_swiat("idempotentna")
    wer = Weryfikator(sw)
    for (a, b) in list(sw.E)[:30]:
        assert wer.sprawdz(a, b) == []
    falszywe = [(a, b) for a in sw.names for b in sw.names if a != b and (a, b) not in sw.E
                and sw.concepts[a][sw.world].any()][:30]
    for (a, b) in falszywe:
        assert wer.sprawdz(a, b)


@pytest.mark.parametrize("ramie", RAMIONA)
def test_budzet_i_statusy(ramie):
    pr = uruchom("komutatywna", 3, ramie, budzet=40)
    assert pr.wywolania <= 40
    sw = zbuduj_swiat("komutatywna")
    # każda skontrowana krawędź jest prawdziwa w świecie (także pusto, gdy przesłanka nie zachodzi w W_H)
    for (a, b), s in pr.pamiec.status.items():
        if s == SKONTROWANA:
            assert (a, b) in sw.E or not sw.concepts[a][sw.world].any()


def test_sen_nie_wola_weryfikatora_ani_nie_zmienia_statusow():
    pr = uruchom("łączna", 0, "A2", budzet=10 ** 6)
    p = pr.pamiec
    przed = dict(p.status)
    out = SenPelny()(p, np.random.default_rng(0), HeurystykaOgolnosci(), 10)
    assert p.status == przed
    assert all(not p.rozstrzygnieta(c.a, c.b) for c in out)


def test_tokeny_zaleznosci_sa_porzadkiem_czesciowym():
    pr = uruchom("medialna", 1, "S", budzet=60)
    M = pr.pamiec.konsolidacja().macierz_zaleznosci
    assert not M.diagonal().any()
    assert not (M & M.T).any()
    Mi = M.astype(int)
    assert not ((Mi @ Mi > 0) & ~M).any()          # przechodniość


def test_intuicja_lmm_jeszcze_niepodpieta():
    kons = uruchom("idempotentna", 0, "A2").pamiec.konsolidacja()
    with pytest.raises(NotImplementedError):
        IntuicjaLMM().ocen([Kandydat("a", "b", "sen:powtorka", 2)], KontekstIntuicji(kons, 20))


def test_seedy_do_json(tmp_path):
    pr = uruchom("x(xy)=y", 2, "S", budzet=60)
    assert pr.seedy
    out = json.loads(do_json(pr.seedy, tmp_path / "s.json").read_text(encoding="utf-8"))
    assert all(s["status"] == "seed" for s in out)


@pytest.mark.skipif(not praxis_dostepny(), reason="matylda_praxis nie jest zainstalowany")
def test_seedy_do_praxis():
    from matylda_praxis.domain.models import HypothesisState
    pr = uruchom("x(xy)=y", 2, "S", budzet=60)
    recs = do_praxis(pr.seedy[:3])
    assert all(r.state == HypothesisState.SEED for r in recs)


def test_prawa_s0_niepuste():
    for H in PRAWA_S0:
        assert len(zbuduj_swiat(H).TR) > 0


def test_swiat_literaly_ma_zaleznosci_wpisow():
    sw = zbuduj_swiat("komutatywna", 3, "literaly")
    assert ("0·1=2", "1·0=2") in sw.E          # komutatywność wymusza zależność między wpisami
    assert ("0·1=2", "1·0=1") not in sw.E
