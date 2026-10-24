# Pi Musik

Ein Musikplayer für den Raspberry Pi 2. Der Pi streamt die Musik selbst von deinem Navidrome-Server
und gibt sie über die 3,5-mm-Klinke aus. Gesteuert wird er vom Handy aus über den Browser unter `http://musik.local`.

```
Handy (Browser) ──WLAN──►  Pi: Weboberfläche + Python-Backend ──► mpv ──► 🔊 Klinke
                                         │
                                         └──── Subsonic-API ────► Navidrome (Internet)
```

- Das Handy ist nur die Fernbedienung. Wenn es in den Standby geht, spielt die Musik weiter.
- Du kannst Playlists, Alben und Künstler durchsuchen, die Warteschlange bearbeiten, wiederholen und mischen.
- Was du hörst, wird an Navidrome gemeldet (Scrobbling), dadurch stimmen dort Wiedergabezähler und „Zuletzt gespielt“.
- Nach einem Neustart macht der Pi an derselben Stelle weiter. Kaputte Titel werden übersprungen.

## 1. Pi vorbereiten (einmalig)

**Hardware:** Der Pi 2 hat **kein eingebautes WLAN**. Du brauchst also ein LAN-Kabel zum Router oder einen
USB-WLAN-Stick, der unter Linux läuft. Für die Ersteinrichtung ist ein LAN-Kabel am einfachsten.

1. Installiere den **Raspberry Pi Imager** auf dem PC und wähle:
   - Gerät: *Raspberry Pi 2*
   - Betriebssystem: *Raspberry Pi OS (other) → Raspberry Pi OS **Lite** (32-bit)*
2. Unter „Einstellungen bearbeiten“:
   - Hostname: **`musik`** (dadurch heißt die Adresse später `http://musik.local`)
   - Benutzername und Passwort festlegen
   - WLAN eintragen, falls du einen WLAN-Stick verwendest
   - Unter „Dienste“ **SSH aktivieren**
3. SD-Karte beschreiben, in den Pi stecken und einschalten. Nach 1–2 Minuten sollte das funktionieren:
   ```bash
   ssh benutzer@musik.local
   ```

## 2. Installieren

Am PC im Projektordner:

```bash
./deploy/deploy.sh benutzer@musik.local
```

Das Skript kopiert das Projekt nach `~/music_player` auf dem Pi und installiert dort mpv, die Python-Umgebung
und den Autostart. Auf einem Pi 2 dauert das beim ersten Mal ein paar Minuten.

Danach trägst du **auf dem Pi** deine Navidrome-Zugangsdaten ein und startest den Dienst:

```bash
ssh benutzer@musik.local
nano ~/music_player/config.toml     # url, username, password
sudo systemctl restart music-player
```

Jetzt kannst du auf dem Handy **`http://musik.local`** öffnen. Am besten legst du die Seite gleich über das
Browser-Menü auf den Startbildschirm, dann verhält sie sich wie eine App.

> **Android:** Manche Android-Geräte können keine `.local`-Adressen auflösen. In dem Fall gibst du dem Pi
> im Router eine feste IP-Adresse und öffnest diese, z.B. `http://192.168.178.50`.

**Updates** spielst du später mit demselben Befehl ein: `./deploy/deploy.sh benutzer@musik.local`

## Konfiguration (`config.toml`)

| Einstellung | Bedeutung |
|---|---|
| `navidrome.url` | Adresse deines Servers, z.B. `https://musik.example.com` |
| `navidrome.max_bitrate` | `0` streamt die Originaldatei. Bei schwacher Internetleitung z.B. `192` eintragen, dann transkodiert Navidrome. |
| `player.audio_device` | Wird von `install.sh` automatisch auf die Klinke gesetzt. Alle Geräte listet `mpv --audio-device=help` auf. |
| `player.autoplay` | `true` lässt den Pi nach dem Einschalten automatisch weiterspielen |
| `server.port` | Standard ist `80` |

## Wenn etwas nicht geht

```bash
journalctl -u music-player -f          # Logs live ansehen
sudo systemctl restart music-player    # Dienst neu starten
speaker-test -c2 -t wav -D plughw:CARD=Headphones   # Ton-Test der Klinke
```

- **Kein Ton:** Prüfe das Kabel und dann `alsamixer -c Headphones`. Der Pegel sollte bei 0 dB liegen.
- **„Navidrome nicht erreichbar“:** URL und Zugangsdaten in `config.toml` prüfen. Zum Test kannst du
  `curl -I https://deine-navidrome-url` auf dem Pi ausführen.
- **Rauschen an der Klinke:** Der analoge Ausgang des Pi 2 ist nicht besonders gut. Ein USB-Soundkarten-Stick
  für wenige Euro klingt deutlich besser. Danach `audio_device` anpassen.

## Am PC entwickeln

```bash
sudo apt install mpv
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp config.example.toml config.toml     # ausfüllen
.venv/bin/python -m app --port 8080    # http://localhost:8080
```

## Aufbau

| Datei | Aufgabe |
|---|---|
| `app/subsonic.py` | Client für die Subsonic-API von Navidrome (Token-Login, Bibliothek, Stream-URLs, Scrobbling) |
| `app/mpv.py` | Startet mpv und steuert es über den JSON-IPC-Socket. Stürzt mpv ab, wird es neu gestartet. |
| `app/player.py` | Warteschlange, Wiederholen/Mischen, Weiterschalten, Speichern des Zustands |
| `app/main.py` | REST-API, WebSocket für Live-Updates und Cover-Proxy |
| `web/` | Oberfläche fürs Handy (reines HTML/CSS/JS, ohne Build-Schritt) |
| `deploy/` | Installation auf dem Pi und Übertragen vom PC |
