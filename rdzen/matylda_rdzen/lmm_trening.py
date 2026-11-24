"""Trening i walidacja intuicji LMM. WYŁĄCZNIE światy bez magm praw S-0 (i bez magm praw walidacyjnych od v2).

    python -m matylda_rdzen.lmm_trening            # v2: dane → trening LMM i ablacji „bez grafu” → wagi → raport

Historia (jawnie, zob. PREREJESTRACJA_S1_LMM.md; kod v0/v1: wyniki/lmm_trening_v0_v1_kod.py.txt):
- v0: 7 światów praw spoza S-0 (ziarna 1100–1199). Walidacja w pętli: werdykt reguły z sekcji 5 = WYNIK NEGATYWNY.
- v1: + światy strukturalne i koniunkcje (54, ziarna 1100–1139). Walidacja: lepsza w 4/5 praw. ODRZUCONY przez recenzję przed
  zamrożeniem: światy rzędu 4 wycięte z U4 pokrywały się prawie w całości ze światami S-0 (np. lewa alternat. ⊃ łączne).
- v2: światy na uniwersach treningowych „3T” (wszystkie magmy rzędu 3 bez magm praw S-0 i walidacyjnych) i „4T”
  (osobne uniwersum, `uniwersum4t.py`, rozłączne z U4); 32 różne światy. Procedura z góry: 10 epok, LR kosinusowo 1e-3 → 1e-5,
  wybór epoki po stracie na odłożonych ziarnach światów treningowych (1160–1169), nie na prawach walidacyjnych.
  Ten sam trening dla ablacji „bez grafu” (koder bez przepływu przez tokeny zależności).
  Wynik v2: nie uogólnia się na prawa walidacyjne (WYNIK NEGATYWNY, wyniki/LMM_RAPORT_v0_v2.md).
- v3 (PLAN_LMM_V3.md): światy z LOSOWYCH praw równościowych (`prawa_losowe.py`) na 3T/4T, setki światów, mało ziaren na świat;
  podział na światy treningowe i ODŁOŻONE ŚWIATY (wybór epoki mierzy przenoszenie na nowe prawa). Architektura i cechy bez zmian.

    python -m matylda_rdzen.lmm_trening v3
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from itertools import combinations

import numpy as np

from .intuicja import HeurystykaOgolnosci, IntuicjaLosowa
from .lmm_intuicja import etykiety, migawka, tensory, zbuduj_model
from .petla import uruchom
from .s1 import CEX, ROOT, SLOWNIK
from .s1b import BUDZET_DNIA, BUDZET_SNU
from .swiat import PRAWA_S0, zbuduj_swiat
from .uniwersum4t import WYKLUCZONE

WALIDACJA = [(H, rz) for rz in (3, 4) for H in ("elastyczna x(yx)=(xy)x", "lewa samodystr.", "prawa samodystr.",
                                                 "x(xy)=xy", "(yx)x=y")]
_L = ["unipotentna xx=yy", "lewa alternat. x(xy)=(xx)y", "prawa alternat. (yx)x=y(xx)", "półsymetr. y(xy)=x"]
_S = ["quasigrupa", "lewo-skracalna", "prawo-skracalna", "ma neutralny", "ma lewy neutralny", "ma zero", "ma idempotent"]
SEEDS_TRENING = range(1100, 1160)
SEEDS_ODLOZONE = range(1160, 1170)
SEEDS_WALID_W_PETLI = range(1440, 1480)   # 1300–1339 użyte do walidacji v0/v1, 1400–1419 przez recenzenta
EPOKI, LR, LR_MIN, ZIARNO = 10, 1e-3, 1e-5, 2024
KONFIGI = {"v2": {"d": 64, "L": 4, "heads": 4, "graf": True}, "v2_bez_grafu": {"d": 64, "L": 4, "heads": 4, "graf": False}}


SWIATY_V3 = ROOT / "dane" / "swiaty_v3.json"
SEEDS_V3 = range(1500, 1508)                # 8 ziaren na świat (światy treningowe i odłożone)
UDZIAL_ODLOZONYCH_V3, ZIARNO_PODZIALU_V3 = 0.15, 77
KONFIGI_V3 = {"v3": {"d": 64, "L": 4, "heads": 4, "graf": True}, "v3_bez_grafu": {"d": 64, "L": 4, "heads": 4, "graf": False}}


def wagi(nazwa):
    return ROOT / "dane" / f"lmm_intuicja_{nazwa}.pt"


def swiaty_v2():
    kand = _L + _S + [f"{a} ∧ {b}" for a in _L for b in _S] + [f"{a} ∧ {b}" for a, b in combinations(_L, 2)]
    out, widziane = [], set()
    for rz in ("3T", "4T"):
        for H in kand:
            sw = zbuduj_swiat(H, rz, SLOWNIK)
            klucz = (rz, tuple(sw.world))
            if len(sw.world) >= 20 and len(sw.TR) >= 15 and klucz not in widziane:
                widziane.add(klucz)
                out.append((H, rz))
    return out


class Nagrywacz:
    """Owija ramię i zapisuje migawkę każdego snu (pula, tokeny zależności, etykiety ewaluatora)."""

    def __init__(self, inner, sw, bufor):
        self.inner, self.sw, self.bufor = inner, sw, bufor
        self.nazwa = inner.nazwa

    def ocen(self, kandydaci, kontekst):
        s = migawka(kandydaci, kontekst)
        s["y"] = etykiety(kandydaci, self.sw)
        s["heur"] = HeurystykaOgolnosci().ocen(kandydaci, kontekst).astype(np.float32)
        self.bufor.append(s)
        return self.inner.ocen(kandydaci, kontekst)


def zbierz(swiaty, seeds):
    bufor = []
    for H, rz in swiaty:
        sw = zbuduj_swiat(H, rz, SLOWNIK)
        for s in seeds:
            for inner in (IntuicjaLosowa(s), HeurystykaOgolnosci()):
                uruchom(H, s, "S", budzet=BUDZET_DNIA, budzet_snu=BUDZET_SNU, rzad=rz, slownik=SLOWNIK, cex_cap=CEX,
                        intuicja=Nagrywacz(inner, sw, bufor))
    return [b for b in bufor if len(b["y"]) > 0]


def _strata(model, T):
    import torch
    model.eval()
    with torch.no_grad():
        return float(np.mean([float(torch.nn.functional.binary_cross_entropy_with_logits(model(*x), y)) for x, y in T]))


def trenuj(dane, odlozone, konfig):
    import torch
    torch.manual_seed(ZIARNO)
    torch.use_deterministic_algorithms(True)
    model = zbuduj_model(**konfig)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    rng = np.random.default_rng(ZIARNO)
    T = [(tensory(s), torch.from_numpy(s["y"])) for s in dane]
    V = [(tensory(s), torch.from_numpy(s["y"])) for s in odlozone]
    hist, najl, stan = [], float("inf"), None
    krok, kroki = 0, EPOKI * len(T)
    for ep in range(EPOKI):
        model.train()
        tot = 0.0
        for i in rng.permutation(len(T)):
            for g in opt.param_groups:
                g["lr"] = LR_MIN + 0.5 * (LR - LR_MIN) * (1 + math.cos(math.pi * krok / kroki))
            x, y = T[i]
            loss = torch.nn.functional.binary_cross_entropy_with_logits(model(*x), y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += float(loss.detach())
            krok += 1
        v = _strata(model, V)
        hist.append({"epoka": ep + 1, "trening": tot / len(T), "odlozone": v})
        print(f"{konfig} epoka {ep + 1}: trening {tot / len(T):.4f}, odłożone {v:.4f}", flush=True)
        if v < najl:
            najl, stan = v, {k: t.clone() for k, t in model.state_dict().items()}
    model.load_state_dict(stan)
    return model, hist


def auc(score, lab):
    pos, neg = score[lab], score[~lab]
    if len(pos) == 0 or len(neg) == 0:
        return None
    v = np.concatenate([pos, neg])
    order = np.argsort(v, kind="mergesort")
    r = np.empty(len(v)); r[order] = np.arange(1, len(v) + 1)
    for u in np.unique(v):                      # remisy: średnie rangi (stała ocena → AUC 0,5)
        m = v == u
        r[m] = r[m].mean()
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def ocena_offline(model, dane, k=10):
    import torch
    model.eval()
    wyn = {"lmm": [], "heur": [], "los": []}
    rng = np.random.default_rng(0)
    for s in dane:
        with torch.no_grad():
            sc = {"lmm": model(*tensory(s)).numpy(), "heur": s["heur"], "los": rng.random(len(s["y"]))}
        y = s["y"]
        sm = s["C"][:, 1] > 0.5
        for nm, v in sc.items():
            top = np.lexsort((rng.random(len(v)), -v))[:k]
            wyn[nm].append((auc(v, y > 0), auc(v, y == 1.0), float(y[top].mean()),
                            auc(v[sm], y[sm] > 0) if sm.sum() > 1 else None))
    out = {}
    for nm, L in wyn.items():
        A = np.array([[np.nan if x is None else x for x in r] for r in L], float)
        out[nm] = {"auc_prawda": float(np.nanmean(A[:, 0])), "auc_TR": float(np.nanmean(A[:, 1])),
                   "topk_wartosc": float(np.nanmean(A[:, 2])), "auc_prawda_smiale": float(np.nanmean(A[:, 3]))}
    return out


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def swiaty_v3():
    """Zamrożona lista (dane/swiaty_v3.json) → (treningowe, odłożone); podział losowy po światach, ziarno 77."""
    L = [(H, rz) for H, rz, *_ in json.loads(SWIATY_V3.read_text(encoding="utf-8"))]
    rng = np.random.default_rng(ZIARNO_PODZIALU_V3)
    idx = rng.permutation(len(L))
    k = int(round(UDZIAL_ODLOZONYCH_V3 * len(L)))
    return [L[i] for i in sorted(idx[k:])], [L[i] for i in sorted(idx[:k])]


def main_v3():
    import torch
    torch.set_num_threads(4)
    tr_sw, od_sw = swiaty_v3()
    assert not any(c in PRAWA_S0 or c in WYKLUCZONE for H, _ in tr_sw + od_sw for c in H.split(" ∧ "))
    t = time.time()
    tr, od = zbierz(tr_sw, SEEDS_V3), zbierz(od_sw, SEEDS_V3)
    print(f"migawki: trening {len(tr)}, odłożone światy {len(od)} ({time.time() - t:.0f} s)", flush=True)
    from .uniwersum4t import sha256 as s4t, wczytaj as w4t
    rap = {"torch": torch.__version__, "swiaty_v3_sha256": _sha(SWIATY_V3), "swiaty_treningowe": len(tr_sw), "swiaty_odlozone": od_sw,
           "u4t_sha256": s4t(w4t().astype(np.uint8)), "seeds": [SEEDS_V3[0], SEEDS_V3[-1]], "epoki": EPOKI, "lr": [LR, LR_MIN],
           "ziarno": ZIARNO, "migawki": {"trening": len(tr), "odlozone_swiaty": len(od)}, "modele": {}}
    for nazwa, konf in KONFIGI_V3.items():
        model, hist = trenuj(tr, od, konf)
        torch.save({"konfig": konf, "wagi": model.state_dict()}, wagi(nazwa))
        rap["modele"][nazwa] = {"konfig": konf, "wagi_sha256": _sha(wagi(nazwa)), "historia": hist,
                                "wybrana_epoka": min(hist, key=lambda h: h["odlozone"])["epoka"],
                                "offline_odlozone_swiaty": ocena_offline(model, od)}
    rap["kod_sha256"] = {f: _sha(ROOT / "matylda_rdzen" / f) for f in
                         ("lmm_intuicja.py", "lmm_trening.py", "lmm_bsd2_models.py", "uniwersum4t.py", "swiat.py", "prawa_losowe.py")}
    (ROOT / "wyniki" / "lmm_trening_v3.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({n: {k: m[k] for k in ("wagi_sha256", "wybrana_epoka", "offline_odlozone_swiaty")} for n, m in rap["modele"].items()},
                     ensure_ascii=False, indent=1))


def main():
    import torch
    torch.set_num_threads(4)
    sw2 = swiaty_v2()
    assert not any(c in PRAWA_S0 or c in WYKLUCZONE for H, _ in sw2 for c in H.split(" ∧ "))
    t = time.time()
    tr, od, wa = zbierz(sw2, SEEDS_TRENING), zbierz(sw2, SEEDS_ODLOZONE), zbierz(WALIDACJA, range(1200, 1240))
    print(f"migawki: trening {len(tr)}, odłożone {len(od)}, walidacja {len(wa)} ({time.time() - t:.0f} s)", flush=True)
    from .uniwersum4t import sha256 as s4t, wczytaj as w4t
    rap = {"torch": torch.__version__, "swiaty_treningowe": sw2, "u4t_sha256": s4t(w4t().astype(np.uint8)),
           "seeds_trening": [1100, 1159], "seeds_odlozone": [1160, 1169], "epoki": EPOKI, "lr": [LR, LR_MIN], "ziarno": ZIARNO,
           "migawki": {"trening": len(tr), "odlozone": len(od), "walidacja_offline": len(wa)}, "modele": {}}
    for nazwa, konf in KONFIGI.items():
        model, hist = trenuj(tr, od, konf)
        torch.save({"konfig": konf, "wagi": model.state_dict()}, wagi(nazwa))
        rap["modele"][nazwa] = {"konfig": konf, "wagi_sha256": _sha(wagi(nazwa)), "historia": hist,
                                "wybrana_epoka": min(hist, key=lambda h: h["odlozone"])["epoka"],
                                "offline_odlozone": ocena_offline(model, od), "offline_walidacja": ocena_offline(model, wa)}
    rap["kod_sha256"] = {f: _sha(ROOT / "matylda_rdzen" / f) for f in
                         ("lmm_intuicja.py", "lmm_trening.py", "lmm_bsd2_models.py", "uniwersum4t.py", "swiat.py")}
    (ROOT / "wyniki" / "lmm_trening_v2.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({n: {k: m[k] for k in ("wagi_sha256", "wybrana_epoka", "offline_walidacja")} for n, m in rap["modele"].items()},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    import sys
    main_v3() if "v3" in sys.argv[1:] else main()
