"""Load configuration from .env file and environment."""

import os
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def load_env() -> None:
    """Parse ROOT/.env and inject into os.environ (existing vars win)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # .env wins over empty/missing env vars; existing non-empty vars win
        if not os.environ.get(key):
            os.environ[key] = value


def get_api_key() -> str:
    load_env()
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key or key == "sk-ant-...":
        raise ValueError(
            "ANTHROPIC_API_KEY nie znaleziony.\n"
            f"Utwórz plik  {ROOT / '.env'}  i wpisz:\n"
            "ANTHROPIC_API_KEY=sk-ant-<twój_klucz>"
        )
    return key
