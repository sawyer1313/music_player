#!/usr/bin/env bash
# Überträgt das Projekt vom PC auf den Pi und installiert/aktualisiert es dort.
# Aufruf:  ./deploy/deploy.sh benutzer@musik.local
set -euo pipefail
TARGET="${1:?Aufruf: $0 benutzer@musik.local}"
cd "$(dirname "$0")/.."

rsync -a --delete \
  --exclude .venv --exclude data --exclude config.toml \
  --exclude __pycache__ --exclude .playwright-mcp --exclude .git \
  ./ "$TARGET:music_player/"

# Eine lokale config.toml nur beim ersten Mal mitnehmen – danach gilt die auf dem Pi.
if [ -f config.toml ]; then
  rsync -a --ignore-existing config.toml "$TARGET:music_player/"
fi

ssh -t "$TARGET" "cd music_player && ./deploy/install.sh"
