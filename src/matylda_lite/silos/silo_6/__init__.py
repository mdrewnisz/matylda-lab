"""Silo 6 — placeholder.

Przeznaczenie: [do zdefiniowania]
"""
from __future__ import annotations
from ...config import ROOT

SILO_META: dict = {
    "id":          "silo_6",
    "name":        "Silo 6",
    "version":     "0.0",
    "enabled":     False,
    "description": "[do zdefiniowania]",
    "api_prefix":  "/api/silo_6",
    "data_dir":    ROOT / "data" / "silos" / "silo_6",
}


def get_router():
    raise NotImplementedError("silo_6 nie zaimplementowany")


def get_dashboard_widget() -> str:
    return ""


def on_startup() -> None:
    SILO_META["data_dir"].mkdir(parents=True, exist_ok=True)


def on_shutdown() -> None:
    pass
