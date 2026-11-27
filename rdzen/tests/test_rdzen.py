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


# --- S-1: ramiona różnią się tylko portem Intuicja ---
from matylda_rdzen.intuicja import IntuicjaLosowa  # noqa: E402
from matylda_rdzen.s1 import RAMIONA as RAMIONA_S1, intuicja as intuicja_s1, pole  # noqa: E402

PRAWO_TESTOWE = "elastyczna x(yx)=(xy)x"     # spoza PRAW_S0, żeby testy nie podglądały świata S-1


@pytest.mark.parametrize("rzad", [3, 4])
def test_s1_czuwanie_i_pula_wspolne(rzad):
    sw = zbuduj_swiat(PRAWO_TESTOWE, rzad, "literaly")
    prz = [uruchom(PRAWO_TESTOWE, 11, "S", budzet=100, rzad=rzad, slownik="literaly", cex_cap=1,
                   intuicja=intuicja_s1(r, 11, sw)) for r in RAMIONA_S1]
    d1 = {p.dziennik.koniec_dnia1 for p in prz}
    assert len(d1) == 1
    pref = [[x for x in p.dziennik.krzywa if x[0] <= d1.copy().pop()] for p in prz]
    assert all(x == pref[0] for x in pref)
    pule = [p.dziennik.pula_snu1 for p in prz]
    assert all(x == pule[0] for x in pule) and pule[0]
    assert all(set(p.dziennik.wybrane_snu1) <= set(pule[0]) for p in prz)


def test_s1_losowa_deterministyczna_i_bez_swiata():
    kons = uruchom("idempotentna", 0, "A2").pamiec.konsolidacja()
    kand = [Kandydat("a", "b", "sen:smiale", 1)] * 5
    a = IntuicjaLosowa(3).ocen(kand, KontekstIntuicji(kons, 20))
    b = IntuicjaLosowa(3).ocen(kand, KontekstIntuicji(kons, 20))
    assert (a == b).all()
    sw = zbuduj_swiat(PRAWO_TESTOWE, 3, "literaly")
    for r in ("losowa", "heurystyka"):
        assert not any(v is sw for v in vars(intuicja_s1(r, 0, sw)).values())


def test_s1_pole_pod_krzywa():
    k = [(10, 2, 0), (12, 4, 0)]
    assert pole(k, 10, 13) == (2 + 2 + 4 + 4) / 4
    assert pole(k, 12, 12) == 4.0


def test_s1b_osobny_budzet_snu():
    """S-1b: po dniu 1 pętla wydaje najwyżej budzet_snu wywołań; dzień 1 jak przy tym samym limicie dnia."""
    for rz in (3, 4):
        a = uruchom(PRAWO_TESTOWE, 5, "S", budzet=300, budzet_snu=50, rzad=rz, slownik="literaly", cex_cap=1)
        b = uruchom(PRAWO_TESTOWE, 5, "A2", budzet=300, rzad=rz, slownik="literaly", cex_cap=1)
        assert a.dziennik.koniec_dnia1 == b.dziennik.koniec_dnia1
        assert a.wywolania - a.dziennik.koniec_dnia1 <= 50


def test_s1b_sen_odbywa_sie_gdy_dzien_wiaze():
    a = uruchom(PRAWO_TESTOWE, 5, "S", budzet=10, budzet_snu=30, rzad=3, slownik="literaly", cex_cap=1)
    assert a.dziennik.koniec_dnia1 == 10
    assert 0 < a.wywolania - a.dziennik.koniec_dnia1 <= 30
    x = uruchom(PRAWO_TESTOWE, 5, "S", budzet=100, rzad=3, slownik="literaly", cex_cap=1)
    y = uruchom(PRAWO_TESTOWE, 5, "S", budzet=100, budzet_snu=None, rzad=3, slownik="literaly", cex_cap=1)
    assert x.wywolania == y.wywolania and x.dziennik.krzywa == y.dziennik.krzywa


# --- ramię LMM ---
import hashlib  # noqa: E402

LMM_WAGI = Path(__file__).resolve().parents[1] / "dane" / "lmm_intuicja_v2.pt"


def test_lmm_kopia_kodera_zgodna_ze_zrodlem():
    src = (Path(__file__).resolve().parents[1] / "matylda_rdzen" / "lmm_bsd2_models.py").read_bytes()
    body = b"\n".join(src.split(b"\n")[2:])
    assert hashlib.sha256(body).hexdigest() == "eaa06c45b5d1092d0a1aea76fbca8d08dd242c6cdcec731b730dc74aa778097e"


@pytest.mark.skipif(not LMM_WAGI.exists(), reason="brak wag LMM")
def test_lmm_deterministyczna_i_bez_swiata_w_petli():
    pytest.importorskip("torch")
    from matylda_rdzen.lmm_intuicja import IntuicjaLMM as L
    from matylda_rdzen.s1lmm import WAGI_SHA
    a, b = L(LMM_WAGI), L(LMM_WAGI)
    assert WAGI_SHA is None or a.sha256 == WAGI_SHA
    assert not any(hasattr(v, "world") for v in vars(a).values())
    pa = uruchom(PRAWO_TESTOWE, 9, "S", budzet=300, budzet_snu=50, rzad=3, slownik="literaly", cex_cap=1, intuicja=a)
    pb = uruchom(PRAWO_TESTOWE, 9, "S", budzet=300, budzet_snu=50, rzad=3, slownik="literaly", cex_cap=1, intuicja=b)
    assert pa.dziennik.krzywa == pb.dziennik.krzywa and pa.dziennik.wybrane_snu1 == pb.dziennik.wybrane_snu1


def test_lmm_trening_bez_praw_s0():
    from matylda_rdzen.lmm_trening import WALIDACJA, swiaty_v2
    from matylda_rdzen.uniwersum4t import WYKLUCZONE
    assert not any(c in PRAWA_S0 for H, _ in WALIDACJA for c in H.split(" ∧ "))
    for H, rz in swiaty_v2():
        assert rz in ("3T", "4T") and not set(H.split(" ∧ ")) & set(WYKLUCZONE)
        sw = zbuduj_swiat(H, rz, "literaly")
        assert not any(sw.concepts[h][sw.world].any() for h in WYKLUCZONE)   # żadna magma treningowa nie spełnia praw S-0 ani walidacyjnych


def test_uniwersum_treningowe_rozlaczne_z_u4():
    from matylda_rdzen.uniwersum4 import wczytaj as u4
    from matylda_rdzen.uniwersum4t import wczytaj as u4t
    a = {tuple(m.ravel()) for m in u4()}
    assert not any(tuple(m.ravel()) in a for m in u4t())


def test_prawa_losowe_zgodne_z_nazwanymi():
    from matylda_rdzen.prawa_losowe import maska_prawa
    from matylda_rdzen.swiat import ALL, T
    assert (maska_prawa("L:(x*y)=(y*x)", T) == ALL["komutatywna"]).all()
    assert (maska_prawa("L:((x*y)*z)=(x*(y*z))", T) == ALL["łączna"]).all()


def test_lmm_v3_bez_praw_wykluczonych():
    """Światy v3 nie zawierają magm praw S-0 ani walidacyjnych (uniwersa 3T/4T) i nie używają nazw tych praw."""
    import json
    from matylda_rdzen.lmm_trening import SWIATY_V3
    from matylda_rdzen.swiat import PRAWA_S0, pojecia, zbuduj_swiat
    from matylda_rdzen.uniwersum4t import WYKLUCZONE
    if not SWIATY_V3.exists():
        import pytest
        pytest.skip("brak dane/swiaty_v3.json")
    L = json.loads(SWIATY_V3.read_text(encoding="utf-8"))
    assert all(H.startswith("L:") and rz in ("3T", "4T") for H, rz, *_ in L)
    for H, rz, *_ in L[::25]:
        sw = zbuduj_swiat(H, rz, "literaly")
        from matylda_rdzen.swiat import _tablice
        P = pojecia(_tablice(rz)[sw.world])
        assert not np.logical_or.reduce([P[h] for h in WYKLUCZONE]).any()
    assert not set(PRAWA_S0) & {H for H, *_ in L}


def test_domyslna_intuicja_to_heurystyka_grafu():
    """Od 27.11 domyślną intuicją rdzenia jest heurystyka grafu; linia bazowa pozostaje dostępna jawnie."""
    from matylda_rdzen.heurystyki import HeurystykaGrafu
    a = uruchom("medialna", 1, "S", budzet=60)
    b = uruchom("medialna", 1, "S", budzet=60, intuicja=HeurystykaGrafu("oa+ob+kara"))
    c = uruchom("medialna", 1, "S", budzet=60, intuicja=HeurystykaOgolnosci())
    assert a.dziennik.krzywa == b.dziennik.krzywa
    assert c.wywolania > 0


def test_prototyp_seedy_w_praxis(tmp_path):
    """Prototyp: każda intuicja z przebudzenia to rekord Praxis w stanie SEED; werdykt tylko obok, stan Praxis bez zmian."""
    from matylda_rdzen.praxis_most import praxis_dostepny
    from matylda_rdzen.prototyp import prototyp
    o = prototyp("komutatywna", 3, 7, tmp_path, budzet_dnia=60, budzet_snu=20)
    assert o["seedy"] == len(o["wpisy"]) > 0 and sum(o["werdykty"].values()) == o["seedy"]
    assert (tmp_path / "przebudzenie.json").exists()
    if praxis_dostepny():
        from matylda_praxis.adapters.sqlite import SQLiteArtifactRepository
        recs = SQLiteArtifactRepository(tmp_path / "praxis.sqlite3").list()
        assert len(recs) == o["seedy"] and all(r.state.value == "seed" for r in recs)


def test_zachlanny_przyrost_liczy_jak_pokrycie():
    """Przyrost wybranej krawędzi = przyrost Swiat.pokrycie; wybór sekwencyjny nie powtarza zysku."""
    from matylda_rdzen.wyrocznie import zachlanny_przyrost
    from matylda_rdzen.swiat import closure
    sw = zbuduj_swiat("medialna", 3, "literaly")
    tr = sorted(sw.TR)
    a, b = [x for x, _ in tr[:5]], [y for _, y in tr[:5]]
    wybor = zachlanny_przyrost(sw.names, set(), tr, a + a[:1], b + b[:1], np.zeros(6), k=6)
    assert sorted(wybor[:5]) == [0, 1, 2, 3, 4] and wybor[5] == 5        # duplikat ostatni (zysk 0)
    przed = sw.pokrycie(set())[0]
    po = sw.pokrycie({(a[wybor[0]], b[wybor[0]])})[0]
    assert po - przed >= 1


def test_wyrocznia_przyrostu_i_heurystyka_przyrostu_w_petli():
    """Wyrocznia: najpierw prawdziwe; heurystyka przyrostu nie zna świata (ten sam wynik dla tego samego ziarna)."""
    from matylda_rdzen.heurystyki_przyrostu import HeurystykaPrzyrostu
    from matylda_rdzen.wyrocznie import IntuicjaWyroczniaPrzyrostu
    sw = zbuduj_swiat("medialna", 3, "literaly")
    r1 = uruchom("medialna", 3, "S", budzet=80, budzet_snu=30, slownik="literaly", cex_cap=1, intuicja=HeurystykaPrzyrostu(1))
    r2 = uruchom("medialna", 3, "S", budzet=80, budzet_snu=30, slownik="literaly", cex_cap=1, intuicja=HeurystykaPrzyrostu(1))
    assert r1.dziennik.krzywa == r2.dziennik.krzywa
    w = uruchom("medialna", 3, "S", budzet=80, budzet_snu=30, slownik="literaly", cex_cap=1, intuicja=IntuicjaWyroczniaPrzyrostu(sw))
    wyb = w.dziennik.wybrane_snu1
    if wyb:
        from matylda_rdzen.s1 import prawdziwa
        flagi = [prawdziwa(sw, k.a, k.b) for k in wyb]
        assert flagi == sorted(flagi, reverse=True)
