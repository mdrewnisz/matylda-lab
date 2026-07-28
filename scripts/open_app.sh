#!/bin/bash
# Szybkie otwarcie aplikacji (alternatywa dla kliknięcia w .app)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
open "$PROJECT_ROOT/Matylda Lite.app"
