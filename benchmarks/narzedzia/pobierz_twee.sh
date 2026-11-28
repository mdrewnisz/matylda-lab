#!/bin/sh
# Pobiera binarkę twee 2.4.2 (github.com/nick8325/twee, wydanie autora) i sprawdza SHA-256.
# Użycie (z katalogu benchmarks/):  sh narzedzia/pobierz_twee.sh
set -e
DIR="$(dirname "$0")/bin"
mkdir -p "$DIR"
curl -sSfL -o "$DIR/twee" https://github.com/nick8325/twee/releases/download/2.4.2/twee-2.4.2-linux-amd64
echo "75e69a47166f7f5c54facde4a8c71a33552b4cb20bdac8b7ece9536f94e07e6e  $DIR/twee" | sha256sum -c -
chmod +x "$DIR/twee"
