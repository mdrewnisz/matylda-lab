"""Ramię LMM: intuicja Matyldy na tokenach zależności.

Koder = architektura LMM (bsd2.PosetEncoder, wariant B, kopia w `lmm_bsd2_models.py`) czytający skonsolidowany graf wiedzy:
węzły = klasy pojęć, kanały = znane wynikanie (porządek częściowy), znane wykluczenie (obalone w obu kierunkach), ukryte (nierozstrzygnięte).
Wagi uczone TUTAJ od zera na światach praw spoza S-0 (wagi z Asusa są niedostępne i uczone na innych danych).

Co widzi model (bez nazw pojęć i bez prawdy świata):
- macierz zależności i macierz obaleń między klasami (z pamięci),
- cechy węzła: częstość pojęcia na znanych magmach, rozmiar klasy, typ pojęcia (prawo / własność strukturalna / literał a·b=c / ⊤),
- cechy kandydatury: wsparcie / liczba znanych magm, czy to śmiałe przeczucie, czy odwrotny kierunek jest obalony.
Ocena = głowica MRP (logit „i ⇒ j”) + mała sieć na stanach węzłów i cechach kandydatury.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from .intuicja import Kandydat, KontekstIntuicji
from .pamiec import OBALONA

STRUKT = {"quasigrupa", "lewo-skracalna", "prawo-skracalna", "ma neutralny", "ma lewy neutralny", "ma zero", "ma idempotent"}
N_CECH_WEZLA = 6
N_CECH_PARY = 3


def typ_pojecia(nazwa: str) -> int:
    if nazwa == "⊤":
        return 3
    if "·" in nazwa:
        return 2
    return 1 if nazwa in STRUKT else 0


def migawka(kandydaci: list[Kandydat], ctx: KontekstIntuicji):
    """Tokeny zależności + cechy dla jednego snu. Zwraca słownik tablic numpy (bez prawdy świata)."""
    kons, p = ctx.konsolidacja, ctx.pamiec
    reps = kons.reprezentanci
    ri = {r: i for i, r in enumerate(reps)}
    n = len(reps)
    F = kons.macierz_zaleznosci.astype(np.float32)
    ob = np.zeros((n, n), dtype=bool)
    for (a, b), s in p.status.items():
        if s == OBALONA:
            ob[ri[kons.cls[a]], ri[kons.cls[b]]] = True
    znane = np.asarray(ctx.znane_magmy, dtype=np.int64)
    rozm = np.zeros(n)
    for a, r in kons.cls.items():
        rozm[ri[r]] += 1
    X = np.zeros((n, N_CECH_WEZLA), dtype=np.float32)
    for r, i in ri.items():
        X[i, 0] = p.concepts[r][znane].mean() if len(znane) else 0.0
        X[i, 1] = np.log1p(rozm[i]) / 3
        X[i, 2 + typ_pojecia(r)] = 1.0
    wykl = (ob & ob.T).astype(np.float32)                         # wykluczenie znane w obu kierunkach
    Hid = ((F + F.T + wykl) == 0).astype(np.float32)
    np.fill_diagonal(Hid, 0)
    ij = np.array([(ri[kons.cls[k.a]], ri[kons.cls[k.b]]) for k in kandydaci], dtype=np.int64).reshape(-1, 2)
    nz = max(ctx.liczba_znanych_magm, 1)
    C = np.array([(k.wsparcie / nz, float(k.zrodlo == "sen:smiale"), float(ob[ri[kons.cls[k.b]], ri[kons.cls[k.a]]]))
                  for k in kandydaci], dtype=np.float32).reshape(-1, N_CECH_PARY)
    return {"F": F, "Hid": Hid, "X": X, "ij": ij, "C": C}


def etykiety(kandydaci: list[Kandydat], sw) -> np.ndarray:
    """TYLKO do treningu na światach spoza S-0: 1 = prawdziwa i na TR, 0,5 = prawdziwa poza TR, 0 = fałszywa."""
    W, c = sw.world, sw.concepts
    y = []
    for k in kandydaci:
        t = not (c[k.a][W] & ~c[k.b][W]).any()
        y.append(0.0 if not t else 1.0 if (sw.cls[k.a], sw.cls[k.b]) in sw.TR else 0.5)
    return np.array(y, dtype=np.float32)


def zbuduj_model(d=64, L=4, heads=4, graf=True):
    import torch
    import torch.nn as nn

    from .lmm_bsd2_models import MRPHead, PosetEncoder, relation_channels

    class IntuicjaNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = PosetEncoder("B", d, L, heads)
            self.cechy = nn.Linear(N_CECH_WEZLA, d)
            self.mrp = MRPHead(d)
            self.glowa = nn.Sequential(nn.Linear(2 * d + 1 + N_CECH_PARY, d), nn.GELU(), nn.Linear(d, 1))

        def forward(self, F, Hid, X, ij, C):
            enc = self.enc
            Fv, Pv, Uv, Hf, eye = relation_channels(F[None], Hid[None])
            T = (Pv + 2.0 * (Uv + Hf) + 3.0 * eye).long()
            h = enc.h0 + self.cechy(X)[None]
            if graf:                       # ablacja „bez grafu”: bez przepływu przez tokeny zależności
                for blk in enc.blocks:
                    h = blk(h, Fv, Pv, Uv, T)
            h = enc.out(h)[0]
            m = self.mrp(h[None])[0][ij[:, 0], ij[:, 1]][:, None]
            return self.glowa(torch.cat([h[ij[:, 0]], h[ij[:, 1]], m, C], dim=1))[:, 0]

    return IntuicjaNet()


def tensory(s):
    import torch
    return [torch.from_numpy(np.ascontiguousarray(s[k])) for k in ("F", "Hid", "X", "ij", "C")]


class IntuicjaLMM:
    """Port Intuicja wypełniony koderem LMM. Deterministyczny (inferencja w float32, 1 wątek)."""

    nazwa = "lmm"

    def __init__(self, sciezka_wag):
        import torch
        torch.set_num_threads(1)
        self.sciezka_wag = Path(sciezka_wag)
        self.sha256 = hashlib.sha256(self.sciezka_wag.read_bytes()).hexdigest()
        stan = torch.load(self.sciezka_wag, map_location="cpu")
        self.model = zbuduj_model(**stan["konfig"])
        self.model.load_state_dict(stan["wagi"])
        self.model.eval()

    def ocen(self, kandydaci, kontekst):
        import torch
        if kontekst.pamiec is None:
            raise ValueError("IntuicjaLMM wymaga pamięci w kontekście (fazy.SenPelny ją przekazuje)")
        s = migawka(kandydaci, kontekst)
        with torch.no_grad():
            return self.model(*tensory(s)).numpy().astype(float)
