"""Build the Matylda Lab flask icon from the canonical PNG source."""
from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).parent
SOURCE = ROOT / "icon_1024.png"
OUTPUT = ROOT.parent.parent / "Matylda Lite.app" / "Contents" / "Resources" / "MatyldaLite.icns"
SIZES = [(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)]


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Brak źródła ikony: {SOURCE}")
    image = Image.open(SOURCE).convert("RGBA")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, format="ICNS", sizes=SIZES)
    print(f"Zapisano ikonę retorty: {OUTPUT}")


if __name__ == "__main__":
    main()
