# Pi Musik – Projektdokumentation

Diese Datei beschreibt, **wie das Projekt aufgebaut ist und warum**. Wie man den Pi einrichtet und
die Software installiert, steht im [README.md](README.md).

---

## 1. Ziel

Ein Raspberry Pi 2 spielt Musik von einem Navidrome-Server ab, der im Internet läuft. Er gibt sie
über die 3,5-mm-Klinke aus. Gesteuert wird er per Smartphone-Browser im Heimnetz. Das Handy ist nur
die Fernbedienung, Abspielen und Streamen übernimmt allein der Pi.

| Anforderung | Umsetzung |
|---|---|
| Steuerung per Handy ohne App | Weboberfläche, die sich als App auf den Startbildschirm legen lässt (PWA) |
| Pi greift selbst auf Navidrome zu | Subsonic-API mit Token-Login |
| Läuft auf schwacher Hardware (900 MHz, 1 GB RAM) | mpv zum Abspielen, schlankes Python-Backend, Frontend ohne Framework |
| Läuft nach dem Einschalten von selbst | systemd-Dienst, `http://musik.local` per mDNS |

## 2. Architektur

```
┌────────────┐  HTTP + WebSocket   ┌──────────────────────── Raspberry Pi 2 ───────────────────────┐
│ Smartphone │ ──────────────────► │  web/ (HTML/CSS/JS)                                          │
│  Browser   │ ◄────────────────── │  app/main.py   Starlette: REST-API, WebSocket, Cover-Proxy   │
└────────────┘   Live-Zustand      │        │                                                     │
                                   │  app/player.py  Warteschlange & Wiedergabelogik              │
                                   │        │                     │                               │
                                   │  app/mpv.py ── IPC-Socket ── mpv ──► ALSA ──► 3,5-mm-Klinke   │
                                   │        │                     │                               │
                                   │  app/subsonic.py             │ streamt direkt                │
                                   └────────│─────────────────────│───────────────────────────────┘
                                            ▼                     ▼
                                      Navidrome (Internet, Subsonic-API)
```

**Wichtige Entscheidung:** Das Handy bekommt nie Zugangsdaten oder Stream-URLs. Auch die Cover holt
das Backend und reicht sie weiter (`/api/cover/{id}`). Das Passwort bleibt damit auf dem Pi.

## 3. Technikwahl

| Baustein | Wahl | Begründung |
|---|---|---|
| Wiedergabe | **mpv** (`--idle`, JSON-IPC) | Streamt HTTP direkt, puffert den nächsten Titel vor (nahtlose Übergänge), braucht wenig CPU |
| Backend | **Python 3.11+**, Starlette, uvicorn, httpx, websockets | Alles reine Python-Pakete, auf dem Pi 2 muss nichts kompiliert werden (FastAPI/pydantic bräuchten Rust) |
| Frontend | Vanilla JS als ES-Modul, ohne Build-Schritt | Lädt auf dem Pi schnell, kein Node auf dem Pi nötig |
| Live-Updates | WebSocket | Titelwechsel und Pause erscheinen sofort auf allen verbundenen Handys |
| Konfiguration | TOML (`tomllib` aus der Standardbibliothek) | Gut lesbar, keine zusätzliche Abhängigkeit |
| Betrieb | systemd + avahi | Autostart, Neustart bei Absturz, Adresse `musik.local` |

## 4. Verzeichnisstruktur

```
music_player/
├── app/
│   ├── __main__.py      Einstieg: python -m app [--config PFAD] [--port N]
│   ├── config.py        Lädt und prüft config.toml
│   ├── subsonic.py      Subsonic-Client und Normalisierung der Daten
│   ├── mpv.py           mpv-Prozess und IPC-Client mit Absturz-Neustart
│   ├── player.py        Warteschlange, Weiterschalten, Fehler, Scrobbling, Speichern
│   └── main.py          HTTP-Routen, WebSocket, Fehlerbehandlung
├── web/
│   ├── index.html       Grundgerüst: Ansicht, Mini-Player, Tab-Leiste, Aktionsmenü
│   ├── app.js           Router, Ansichten, WebSocket-Client
│   ├── style.css        Dunkles, mobiles Layout
│   ├── manifest.webmanifest, icon.svg
├── deploy/
│   ├── install.sh       Läuft auf dem Pi: Pakete, venv, Audio, systemd
│   └── deploy.sh        Läuft auf dem PC: rsync auf den Pi und install.sh ausführen
├── config.example.toml  Vorlage für config.toml (config.toml wird nicht eingecheckt)
├── requirements.txt
└── data/                Laufzeitdaten (state.json, ggf. mpv.sock), wird nicht eingecheckt
```

## 5. Komponenten im Detail

### 5.1 `subsonic.py` – Navidrome-Anbindung

- **Login:** Bei jeder Anfrage wird ein neues Salt `s` erzeugt und der Token `t = md5(passwort + s)`
  mitgeschickt. Das Passwort selbst geht nie über die Leitung.
- **Antworten normalisieren:** Die Funktionen `song()`, `album()`, `artist()` und `playlist()` reduzieren die
  Rohdaten auf die Felder, die die Oberfläche braucht. Dadurch bleiben Warteschlange und WebSocket-Nachrichten klein.
- **Stream-URL:** `stream_url(id)` erzeugt eine URL mit Login-Daten, die mpv direkt abspielt. Mit
  `format=raw` kommt die Originaldatei. Ist `max_bitrate` gesetzt, transkodiert Navidrome.
- **Genutzte Endpunkte:** `ping`, `getPlaylists`, `getPlaylist`, `getArtists`, `getArtist`, `getAlbum`,
  `getAlbumList2`, `search3`, `getSong`, `getRandomSongs`, `getCoverArt`, `stream`, `scrobble`.

### 5.2 `mpv.py` – Steuerung des Players

- Startet mpv mit `--idle --no-video --no-config --ytdl=no --prefetch-playlist=yes` und einem
  IPC-Socket. Liegt `XDG_RUNTIME_DIR` vor, kommt der Socket dorthin (systemd: `/run/music-player`),
  sonst nach `data/`.
- `command()` schickt JSON-Befehle mit `request_id` und wartet auf die passende Antwort (Timeout 10 s).
  Ereignisse wie `property-change`, `start-file`, `end-file` und `file-loaded` gehen an den Player.
- **Supervisor:** Beendet sich mpv, ruft der Supervisor zuerst `on_exit()` auf, damit der Player Position
  und Zustand sichert. Nach 2 s startet er mpv neu und meldet die beobachteten Properties wieder an.

### 5.3 `player.py` – Wiedergabelogik (Kernstück)

**Grundprinzip:** Die Warteschlange im Python-Code ist die Wahrheit. mpv bekommt immer nur zwei Einträge:

```
mpv-Playlist:  [ aktueller Titel , nächster Titel ]
                     ▲                   ▲
               _cur_entry          _next_entry   (eindeutige mpv-Eintrags-IDs)
```

So kann mpv den nächsten Titel vorpuffern, und Änderungen an der Warteschlange bleiben trotzdem einfach.

**Weiterschalten:** mpv meldet `start-file` mit einer `playlist_entry_id`. Nur wenn diese ID gleich
`_next_entry` ist, rückt der Player weiter (`_take_next`). Danach baut `_sync_next` die mpv-Playlist neu
auf: `playlist-clear` entfernt alles außer dem aktuellen Eintrag, dann wird der neue nächste Titel angehängt.
Veraltete Ereignisse, etwa wenn der Nutzer inzwischen etwas anderes gestartet hat, tragen eine andere ID
und werden ignoriert. Das ist robuster als die Auswertung von `playlist-pos`.

**Welcher Eintrag ist gemeint?** Der nächste Titel wird als Objekt gemerkt (`_next_song`) und nicht als
Index. Verschiebt oder löscht der Nutzer gleichzeitig Titel, findet der Player den richtigen Eintrag
trotzdem über die Objekt-Identität (`_index_of`).

**Nebenläufigkeit:** Alle Änderungen am Zustand laufen unter einem `asyncio.Lock`. Ereignisse von mpv
und Befehle von der Oberfläche können sich also nicht in die Quere kommen.

**Fehlerbehandlung:**

| Situation | Verhalten |
|---|---|
| Titel lässt sich nicht laden (`end-file`, Grund `error`) | Fehlerzähler +1 |
| mpv springt selbst zum nächsten Eintrag | normales Weiterschalten |
| mpv läuft danach leer (idle) | Der fehlerhafte Eintrag wird über die Eintrags-ID bestimmt und der Titel danach gestartet |
| 3 Fehler in Folge | Wiedergabe stoppt mit dem Hinweis „ist Navidrome erreichbar?“ (verhindert Durchrasen bei Netzausfall) |
| Ein Titel lädt erfolgreich (`file-loaded`) | Zähler wird auf 0 gesetzt |
| mpv stürzt ab | Die Position wird gesichert, mpv neu gestartet, beim nächsten Play geht es dort weiter |

**Wiederholen:** `off`, `all` (nach dem letzten Titel weiter bei 0) und `one` (der nächste Eintrag ist derselbe
Titel). Drückt man manuell „Weiter“, wird `one` ignoriert.

**Mischen** ist eine Aktion, kein Modus. Der aktuelle Titel rückt an Position 0, der Rest wird gemischt.

**Scrobbling:** Beim Start eines Titels geht `submission=false` an Navidrome („läuft gerade“). Nach der halben
Laufzeit (höchstens 4 min, mindestens 15 s) folgt `submission=true`. Das prüft ein Ticker alle 5 s.

**Speichern:** Damit die SD-Karte geschont wird, gibt es zwei Dateien in `data/`:

| Datei | Inhalt | Wird geschrieben |
|---|---|---|
| `queue.json` | die Warteschlange, bei großen Playlists mehrere hundert KB | nur wenn sie sich ändert, erkannt an `queue_version` |
| `state.json` | Index, Position, Lautstärke, Wiederholen (~80 Byte) | bei Titelwechsel, Pause, Bedienung und alle 60 s während der Wiedergabe (`SAVE_INTERVAL`) |

- Geschrieben wird atomar über eine `.tmp`-Datei mit anschließendem Umbenennen, das übersteht Stromausfälle.
  Die Warteschlange kommt immer zuerst, damit der Index nie auf eine ältere Warteschlange zeigt.
- Das Schreiben läuft in einem Thread (`asyncio.to_thread`), damit lange Warteschlangen die App nicht blockieren.
  Ein eigener Lock verhindert, dass sich zwei Schreibvorgänge überholen.
- Beim Start werden beide Dateien geladen. Der Index wird auf die Länge der Warteschlange begrenzt. Eine
  `state.json` im alten Format, in der die Warteschlange noch mit drin stand, wird automatisch übernommen.
- Mit `autoplay = true` spielt der Pi nach dem Einschalten direkt weiter.

**Limits:** Die Warteschlange fasst höchstens 2000 Titel (`MAX_QUEUE`).

### 5.4 `main.py` – HTTP-Schnittstelle

- **Quellen auflösen:** Die Oberfläche schickt nur `{type, id}`, das Backend holt die Titel selbst:
  `playlist`, `album`, `artist` (alle Alben), `song` oder `random` (`size`, Standard 50).
- **Cover-Proxy:** Ein Cache im Speicher (LRU, 150 Bilder) plus `Cache-Control: max-age=7 Tage`, damit das
  Handy die Bilder ebenfalls zwischenspeichert.
- **Fehler:** Navidrome-Fehler werden zu `502 {"error": "..."}`, ungültige Eingaben zu `400`.
  Die Oberfläche zeigt `error` als Toast an.

### 5.5 Frontend (`web/`)

- **Router über den Hash:** `#/now`, `#/playlists`, `#/playlist/ID`, `#/library/<typ>`, `#/artist/ID`,
  `#/album/ID`, `#/search`, `#/queue`. Jede Ansicht bekommt eine `alive()`-Funktion. Hat der Nutzer
  schon weiternavigiert, werden langsame Antworten verworfen.
- **Position:** Der Server schickt keine laufenden Positionsupdates, das würde den Pi belasten. Der Client
  rechnet ab der letzten Meldung lokal weiter (`position()`).
- **Verbindung:** Bricht der WebSocket ab, verbindet der Client mit Backoff neu (bis 8 s). Beim Zurückkehren
  in den Tab verbindet er sofort neu und holt den Zustand. Alle 20 s schickt er einen Ping.
- **Sicherheit:** Alle Texte aus Navidrome laufen durch `esc()`, damit Namen wie `<Lieblinge>` kein HTML einschleusen.
- Fehlende Cover ersetzt ein globaler `error`-Listener durch einen Platzhalter.

## 6. API-Referenz

Alle POST-Endpunkte erwarten JSON. Die Antwort ist `{"ok": true}`, sofern nichts anderes angegeben ist.

### Wiedergabe

| Methode | Pfad | Body | Wirkung |
|---|---|---|---|
| GET | `/api/state` | – | aktueller Zustand (siehe unten) |
| POST | `/api/player/play` · `pause` · `toggle` · `next` · `prev` · `stop` | – | Steuerung. `prev` springt bei mehr als 5 s an den Titelanfang zurück. |
| POST | `/api/player/seek` | `{"position": 83.5}` | Spulen (Sekunden) |
| POST | `/api/player/volume` | `{"volume": 0–100}` | Lautstärke (in mpv geregelt) |
| POST | `/api/player/repeat` | `{"mode": "off"\|"all"\|"one"}` | Wiederholen |

### Warteschlange

| Methode | Pfad | Body | Wirkung |
|---|---|---|---|
| GET | `/api/queue` | – | `{"queue": [...], "index": n, "version": v}` |
| POST | `/api/queue/play` | `{"type", "id", "index"?, "shuffle"?}` | Warteschlange ersetzen und abspielen, Antwort enthält `count` |
| POST | `/api/queue/add` | `{"type", "id", "mode": "now"\|"next"\|"end"}` | einfügen, Antwort enthält `count` |
| POST | `/api/queue/jump` | `{"index"}` | zu einem Titel springen |
| POST | `/api/queue/remove` | `{"index"}` | Titel entfernen |
| POST | `/api/queue/move` | `{"from", "to"}` | Titel verschieben |
| POST | `/api/queue/shuffle` · `clear` | – | mischen / leeren |

### Bibliothek

| Pfad | Ergebnis |
|---|---|
| `GET /api/library/playlists` | Liste der Playlists |
| `GET /api/library/playlist/{id}` | Playlist mit `songs` |
| `GET /api/library/artists` | alle Künstler |
| `GET /api/library/artist/{id}` | Künstler mit `albums` |
| `GET /api/library/album/{id}` | Album mit `songs` |
| `GET /api/library/albums?type=…&offset=…` | 40 Alben. `type`: `newest`, `random`, `recent`, `frequent`, `alphabeticalByName`, `starred` |
| `GET /api/library/search?q=…` | `{"artists", "albums", "songs"}` |
| `GET /api/cover/{id}?size=48–800` | Bild |

### WebSocket `/api/ws`

Der Server schickt direkt nach dem Verbinden und danach bei jeder Änderung (zusammengefasst über 50 ms):

```json
{
  "type": "state",
  "state": {
    "status": "playing",          // playing | paused | stopped
    "current": { "id": "...", "title": "...", "artist": "...", "artistId": "...",
                 "album": "...", "albumId": "...", "coverArt": "...", "duration": 215, "track": 3 },
    "index": 4,
    "position": 37.2,
    "duration": 215,
    "volume": 70,
    "repeat": "off",
    "queue_length": 25,
    "queue_version": 12,          // ändert sich → Client lädt /api/queue neu
    "mpv_connected": true,
    "error": null
  }
}
```

Der Client schickt nur `ping`-Texte, um die Verbindung offen zu halten.

## 7. Konfiguration

Alle Schlüssel aus `config.toml` (Vorlage: `config.example.toml`):

| Abschnitt | Schlüssel | Standard | Bedeutung |
|---|---|---|---|
| `navidrome` | `url`, `username`, `password` | – (Pflicht) | Zugang zum Server |
| | `max_bitrate` | `0` | `0` = Original, sonst kbit/s für das Transkodieren |
| | `transcode_format` | `mp3` | Zielformat beim Transkodieren |
| `server` | `host` / `port` | `0.0.0.0` / `80` | Adresse des Webservers. `--port` überschreibt den Port |
| `player` | `audio_device` | `auto` | mpv-Audiogerät. `install.sh` setzt die Klinke ein |
| | `mpv` | `mpv` | Pfad zur mpv-Binärdatei |
| | `default_volume` | `70` | Lautstärke beim allerersten Start |
| | `autoplay` | `false` | nach dem Einschalten weiterspielen |
| `storage` | `data_dir` | `data` | Ort für `state.json` |

Den Pfad zur Konfiguration kann man auch über die Umgebungsvariable `MUSIC_PLAYER_CONFIG` setzen.

## 8. Betrieb auf dem Pi

- **Dienst:** `/etc/systemd/system/music-player.service` wird von `install.sh` erzeugt. Er läuft als normaler
  Benutzer mit der Gruppe `audio`. `CAP_NET_BIND_SERVICE` erlaubt Port 80 ohne root, `Restart=always` sorgt
  für einen Neustart nach Abstürzen.
- **Audio:** Der Hardware-Pegel der Klinke wird auf 0 dB fixiert (`amixer`, `alsactl store`). Die Lautstärke
  regelt nur mpv.
- **Logs:** `journalctl -u music-player -f`. Die httpx-Anfragen werden bewusst nicht geloggt, weil die URLs Login-Tokens enthalten.
- **Updates:** `./deploy/deploy.sh benutzer@musik.local`. `config.toml` und `data/` auf dem Pi bleiben dabei unangetastet.

## 9. Tests

Während der Entwicklung lief alles gegen zwei nachgebaute Gegenstellen:

- einen **Fake-Navidrome** (Starlette-App, prüft den Token-Login und enthält einen absichtlich kaputten Titel)
- ein **Fake-mpv** (spricht das JSON-IPC-Protokoll inklusive Eintrags-IDs, jeder Titel dauert 4 s)

Geprüft wurden:
- automatisches Weiterschalten, Überspringen kaputter Titel, Pause, Vor/Zurück, Spulen und Lautstärke
- alle Wiederholen-Modi und alle Operationen auf der Warteschlange
- WebSocket-Updates
- mpv-Absturz mit Fortsetzen und App-Neustart mit Fortsetzen
- alle Ansichten im Browser bei 390 × 844 px, ohne Konsolenfehler

**Noch nicht getestet:** echtes mpv auf dem Pi und ein echter Navidrome-Server. Das ist der erste Schritt nach der Installation.

## 10. Bekannte Grenzen

- Es gibt keine Anmeldung an der Weboberfläche. Jeder im Heimnetz kann steuern, also den Port nicht ins Internet freigeben.
- Kein HTTPS im Heimnetz. Deshalb gibt es auch keinen Service Worker, „Zum Startbildschirm“ legt nur eine Verknüpfung an.
- Android löst `.local`-Adressen nicht immer auf. Abhilfe ist eine feste IP über den Router.
- Der analoge Ausgang des Pi 2 rauscht hörbar. Abhilfe ist ein USB-DAC, danach `audio_device` anpassen.
- Neu sortiert wird über das Menü (nach oben/unten), Drag & Drop gibt es nicht.
- Voraussetzung ist mpv ab 0.33, wegen `playlist_entry_id`. Raspberry Pi OS bringt eine neuere Version mit.

## 11. Ideen für später

- Favoriten (Sterne, `star`/`unstar`)
- Schlaf-Timer und Wecker
- Eine physische Taste oder einen Drehregler am GPIO für Play/Pause und Lautstärke
- Eine PIN für die Weboberfläche
- Drag & Drop in der Warteschlange
- Zufallsmix nach Genre oder Jahr (`getRandomSongs` mit `genre`, `fromYear`, `toYear`)
