# Kopia bez zmian: mdrewnisz/LMM, bsd2/models.py, commit 39bd2172583699c3ad24211a61e6202e623e2fd3,
# sha256 eaa06c45b5d1092d0a1aea76fbca8d08dd242c6cdcec731b730dc74aa778097e (sprawdza test). Architektura LMM: PosetEncoder + MRPHead.
# -*- coding: utf-8 -*-
"""Architektury A i B (BSD-II / SP-v1). STATUS: PROJEKT IMPLEMENTACJI, NIEZAMROŻONY.

A (Poset Encoder, kontrola): warstwa M0 z bsd_model.py (BSD-I) bez zmian: trzy kanały relacji (przeszłość, przyszłość,
brak relacji), agregacja sumą unormowaną przez N, LayerNorm(4d) + MLP z połączeniem resztkowym; wspólny wektor startowy.
B (Relational Transformer, model główny): PROPOZYCJA DO AUDYTU. Warstwa B zawiera te same trzy kanały sumy unormowanej co A
oraz wielogłowicową uwagę z uczonym biasem typu relacji (4 typy: przyszłość, przeszłość, brak widocznej relacji, ten sam
punkt; para ukryta dostaje ten sam typ co para bez widocznej relacji — decyzja audytu: ścieżka uwagi nie zna położenia maski,
więc B dostaje informację o masce wyłącznie przez trzy kanały sumy, identyczne z A); oba składniki przechodzą przez
LayerNorm(5d) + MLP z połączeniem resztkowym.
Warstwy H3: wyjścia bloków o indeksach (od 1) ceil(L/2), L − 1, L; nazwy modułów "blocks.{k − 1}"; wymagane L ≥ 4."""
import math

import torch
import torch.nn as nn

REL_TYPES = ("przyszlosc", "przeszlosc", "brak_widocznej_relacji", "ten_sam_punkt")  # para ukryta -> brak widocznej relacji


def relation_channels(Fut, Hid=None):
    """Kanały jak w bsd_v2.visible (z maską) i bsd_model.Encoder (bez maski). Fut[i, j] = 1 <=> i ≺ j."""
    B, n, _ = Fut.shape
    eye = torch.eye(n, device=Fut.device, dtype=Fut.dtype).expand(B, n, n)
    Hf = torch.zeros_like(Fut) if Hid is None else Hid.to(Fut.dtype)
    Fv = Fut * (1.0 - Hf)
    Pv = Fv.transpose(1, 2)
    Uv = 1.0 - Fv - Pv - eye - Hf
    return Fv, Pv, Uv, Hf, eye


class RelationalLayer(nn.Module):
    """Architektura A: warstwa M0 z bsd_model.py, bez zmian (parametr T ignorowany)."""

    def __init__(self, d):
        super().__init__()
        self.wp = nn.Linear(d, d, bias=False)
        self.wf = nn.Linear(d, d, bias=False)
        self.wu = nn.Linear(d, d, bias=False)
        self.norm = nn.LayerNorm(4 * d)
        self.mlp = nn.Sequential(nn.Linear(4 * d, 2 * d), nn.GELU(), nn.Linear(2 * d, d))

    def forward(self, h, Fut, Past, Unr, T=None):
        n = h.shape[1]
        mp = torch.bmm(Past, self.wp(h)) / n
        mf = torch.bmm(Fut, self.wf(h)) / n
        mu = torch.bmm(Unr, self.wu(h)) / n
        return h + self.mlp(self.norm(torch.cat([h, mp, mf, mu], dim=-1)))


class RTLayer(nn.Module):
    """Architektura B: suma unormowana w trzech kanałach (jak A) + uwaga z biasem 4 typów relacji (maska niewidoczna dla uwagi)."""

    def __init__(self, d, heads):
        super().__init__()
        if d % heads:
            raise ValueError("d musi być podzielne przez liczbę głowic")
        self.heads, self.dh = heads, d // heads
        self.wp = nn.Linear(d, d, bias=False)
        self.wf = nn.Linear(d, d, bias=False)
        self.wu = nn.Linear(d, d, bias=False)
        self.q = nn.Linear(d, d, bias=False)
        self.k = nn.Linear(d, d, bias=False)
        self.v = nn.Linear(d, d, bias=False)
        self.o = nn.Linear(d, d)
        self.type_bias = nn.Parameter(torch.zeros(heads, len(REL_TYPES)))
        self.norm = nn.LayerNorm(5 * d)
        self.mlp = nn.Sequential(nn.Linear(5 * d, 2 * d), nn.GELU(), nn.Linear(2 * d, d))

    def forward(self, h, Fut, Past, Unr, T):
        B, n, d = h.shape
        mp = torch.bmm(Past, self.wp(h)) / n
        mf = torch.bmm(Fut, self.wf(h)) / n
        mu = torch.bmm(Unr, self.wu(h)) / n
        split = lambda x: x.view(B, n, self.heads, self.dh).transpose(1, 2)
        q, k, v = split(self.q(h)), split(self.k(h)), split(self.v(h))
        bias = self.type_bias[:, T].permute(1, 0, 2, 3)
        att = torch.softmax(q @ k.transpose(-1, -2) / math.sqrt(self.dh) + bias, dim=-1)
        a = self.o((att @ v).transpose(1, 2).reshape(B, n, d))
        return h + self.mlp(self.norm(torch.cat([h, mp, mf, mu, a], dim=-1)))


def h3_indices(L):
    """Indeksy bloków H3 (od 1): ceil(L/2), L − 1, L; wymagane L ≥ 4 (trzy różne bloki)."""
    if L < 4:
        raise ValueError("H3 wymaga wspólnej głębokości L ≥ 4")
    return [math.ceil(L / 2), L - 1, L]


class PosetEncoder(nn.Module):
    def __init__(self, arch, d, L, heads=None):
        super().__init__()
        if arch not in ("A", "B"):
            raise ValueError("architektura musi być 'A' albo 'B'")
        h3_indices(L)
        self.arch, self.d, self.L = arch, d, L
        self.h0 = nn.Parameter(0.1 * torch.randn(d))
        if arch == "A":
            blocks = [RelationalLayer(d) for _ in range(L)]
        else:
            if heads is None:
                raise ValueError("architektura B wymaga liczby głowic")
            blocks = [RTLayer(d, heads) for _ in range(L)]
        self.blocks = nn.ModuleList(blocks)
        self.out = nn.LayerNorm(d)

    def h3_module_names(self):
        return [f"blocks.{k - 1}" for k in h3_indices(self.L)]

    def forward(self, Fut, Hid=None, return_layers=False):
        """Zwraca (stany punktów h, reprezentację Z = LayerNorm(średnia punktów), listę średnich wyjść bloków)."""
        # SP-v1.1: wejście w typie wag (float32 w treningu, bit w bit jak .float(); float64 wyłącznie w kontroli T5)
        Fv, Pv, Uv, Hf, eye = relation_channels(Fut.to(self.h0.dtype), Hid)
        T = (Pv + 2.0 * (Uv + Hf) + 3.0 * eye).long() if self.arch == "B" else None  # para ukryta = typ 2
        B, n, _ = Fv.shape
        h = self.h0.expand(B, n, -1)
        layers = []
        for blk in self.blocks:
            h = blk(h, Fv, Pv, Uv, T)
            if return_layers:
                layers.append(h.mean(dim=1))
        return h, self.out(h.mean(dim=1)), layers


class MRPHead(nn.Module):
    """Odczyt pary z MRP0 (bsd_v2.py), bez zmian: logit P(i ≺ j) dwuliniowy plus składniki punktowe."""

    def __init__(self, d, r=32):
        super().__init__()
        self.u, self.w = nn.Linear(d, r), nn.Linear(d, r)
        self.a, self.b = nn.Linear(d, 1), nn.Linear(d, 1)
        self.r = r

    def forward(self, h):
        return torch.bmm(self.u(h), self.w(h).transpose(1, 2)) / math.sqrt(self.r) + self.a(h) + self.b(h).transpose(1, 2)
