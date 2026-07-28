"""Silo 5 — placeholder.

Przeznaczenie: [do zdefiniowania]
"""
from __future__ import annotations
from ...config import ROOT

SILO_META: dict = {
    "id":          "silo_5",
    "name":        "Silo 5",
    "version":     "0.0",
    "enabled":     False,
    "description": "[do zdefiniowania]",
    "api_prefix":  "/api/silo_5",
    "data_dir":    ROOT / "data" / "silos" / "silo_5",
}


def get_router():
    raise NotImplementedError("silo_5 nie zaimplementowany")


def get_dashboard_widget() -> str:
    return ""


def on_startup() -> None:
    SILO_META["data_dir"].mkdir(parents=True, exist_ok=True)


def on_shutdown() -> None:
    pass
