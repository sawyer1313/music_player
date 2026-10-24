#!/usr/bin/env bash
# Installiert den Musikplayer auf dem Raspberry Pi und richtet den Autostart ein.
# Aufruf auf dem Pi im Projektordner:  ./deploy/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."
APP_DIR="$(pwd)"
USER_NAME="$(id -un)"

echo "==> Systempakete (mpv, Python, mDNS, ALSA)"
sudo apt-get update -q
sudo apt-get install -y -q mpv python3-venv avahi-daemon alsa-utils

echo "==> Python-Umgebung"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

NEW_CONFIG=0
if [ ! -f config.toml ]; then
  cp config.example.toml config.toml
  NEW_CONFIG=1
fi

echo "==> Audio: 3,5-mm-Klinke"
if aplay -l 2>/dev/null | grep -q "Headphones"; then
  sed -i 's|^audio_device = "auto"|audio_device = "alsa/plughw:CARD=Headphones,DEV=0"|' config.toml
  amixer -q -c Headphones sset PCM 0dB 2>/dev/null || true   # Hardware-Pegel fix, Lautstärke regelt die App
  sudo alsactl store 2>/dev/null || true
else
  echo "    Kein 'Headphones'-Gerät gefunden – audio_device in config.toml bleibt wie es ist."
fi
sudo usermod -aG audio "$USER_NAME"

echo "==> systemd-Dienst"
sudo tee /etc/systemd/system/music-player.service >/dev/null <<EOF
[Unit]
Description=Pi-Musikplayer (Navidrome)
After=network-online.target sound.target
Wants=network-online.target

[Service]
User=$USER_NAME
SupplementaryGroups=audio
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python -m app
Restart=always
RestartSec=3
# Port 80 ohne root-Rechte
AmbientCapabilities=CAP_NET_BIND_SERVICE
RuntimeDirectory=music-player
Environment=XDG_RUNTIME_DIR=/run/music-player
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable -q music-player

HOST="$(hostname).local"
if [ "$NEW_CONFIG" = 1 ] || grep -q '^username = "dein-benutzer"' config.toml; then
  echo
  echo "Fast fertig! Trage jetzt deine Navidrome-Zugangsdaten ein:"
  echo "    nano $APP_DIR/config.toml"
  echo "und starte dann den Dienst:"
  echo "    sudo systemctl restart music-player"
else
  sudo systemctl restart music-player
  echo
  echo "Läuft! Öffne auf dem Handy:  http://$HOST"
fi
echo "Logs ansehen:  journalctl -u music-player -f"
