#!/bin/bash
# Kopiuje Matylda Lite.app do /Applications dla dostępu globalnego

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP="$PROJECT_ROOT/Matylda Lite.app"

if [ ! -d "$APP" ]; then
    echo "Błąd: nie znaleziono $APP"
    exit 1
fi

echo "Kopiuję Matylda Lite.app → /Applications..."
cp -R "$APP" /Applications/
echo "✓ Zainstalowano. Możesz teraz otworzyć Matylda Lite z Launchpada."
