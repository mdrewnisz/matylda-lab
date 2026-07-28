"""
Szablon silo — skopiuj do silo_N/__init__.py i wypełnij.

Minimalna implementacja:
  1. Ustaw SILO_META
  2. Zaimplementuj get_router() zwracający FastAPI APIRouter
  3. Opcjonalnie: get_dashboard_widget(), on_startup(), on_shutdown()
"""
from __future__ import annotations
from pathlib import Path
from ..config import ROOT

# ── Metadane silo ─────────────────────────────────────────────────────────────

SILO_META: dict = {
    "id":          "silo_N",            # zmień na silo_1 / silo_2 / ...
    "name":        "[Nazwa silo]",      # wyświetlana w UI i menu bar
    "version":     "0.1",
    "enabled":     False,               # zmień na True gdy gotowy
    "description": "[Opis przeznaczenia silo]",
    "api_prefix":  "/api/silo_N",       # prefix endpointów
    "data_dir":    ROOT / "data" / "silos" / "silo_N",
}

# ── API ───────────────────────────────────────────────────────────────────────

def get_router():
    """Zwróć FastAPI APIRouter z endpointami silo.

    Wywoływane tylko gdy enabled=True i serwer działa na FastAPI.
    """
    # TODO: Po migracji na FastAPI:
    # from fastapi import APIRouter
    # router = APIRouter()
    #
    # @router.get("/status")
    # def status():
    #     return {"silo": SILO_META["id"], "ok": True}
    #
    # return router
    raise NotImplementedError("silo router nie zaimplementowany")


# ── Dashboard widget ──────────────────────────────────────────────────────────

def get_dashboard_widget() -> str:
    """Zwróć HTML fragment do wstawienia w dashboardzie (opcjonalne).

    Wynik wstawiany jest do prawego panelu lub osobnej sekcji.
    """
    # TODO: Zwróć string HTML z widgetem
    return ""


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def on_startup() -> None:
    """Uruchamiane raz przy starcie serwera."""
    # TODO: Inicjalizacja katalogów danych, połączeń itp.
    SILO_META["data_dir"].mkdir(parents=True, exist_ok=True)


def on_shutdown() -> None:
    """Uruchamiane przy graceful shutdown."""
    # TODO: Cleanup połączeń, flush buforów itp.
    pass
