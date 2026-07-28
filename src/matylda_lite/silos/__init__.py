"""Silo auto-discovery i loader.

Silo to niezależny moduł rozszerzeń Matyldy Lite.
Każdy silo ma własne API, dane i opcjonalny widget dashboardu.

Użycie (po migracji na FastAPI):
    from matylda_lite.silos import load_enabled_silos
    for meta, router in load_enabled_silos():
        app.include_router(router, prefix=meta["api_prefix"])
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Generator

_SILOS_ROOT = Path(__file__).parent


def discover_silos() -> list[str]:
    """Zwróć listę id silo (nazwy podkatalogów z __init__.py)."""
    ids = []
    for d in sorted(_SILOS_ROOT.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.name.startswith("silo_"):
            ids.append(d.name)
    return ids


def load_silo(silo_id: str):
    """Importuj moduł silo i zwróć go."""
    return importlib.import_module(f".{silo_id}", package=__name__)


def load_enabled_silos() -> Generator[tuple[dict, object], None, None]:
    """Generator: (meta, router) dla każdego aktywnego silo."""
    for silo_id in discover_silos():
        try:
            mod = load_silo(silo_id)
            meta = mod.SILO_META
            if meta.get("enabled"):
                router = mod.get_router()
                yield meta, router
        except Exception as exc:  # noqa: BLE001
            print(f"[silos] błąd ładowania {silo_id}: {exc}")


def all_silo_meta() -> list[dict]:
    """Zwróć meta wszystkich silo (aktywnych i nieaktywnych)."""
    result = []
    for silo_id in discover_silos():
        try:
            mod = load_silo(silo_id)
            result.append(mod.SILO_META)
        except Exception as exc:  # noqa: BLE001
            result.append({"id": silo_id, "name": silo_id, "enabled": False, "error": str(exc)})
    return result
