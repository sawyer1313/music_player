"""Warteschlange + Wiedergabe.

Unsere Warteschlange ist die Wahrheit. mpv bekommt immer nur [aktueller Titel, nächster Titel],
damit es den nächsten vorpuffern und nahtlos überblenden kann. Jeder mpv-Playlisteintrag hat eine
eindeutige ID; meldet mpv per "start-file", dass es den vorgepufferten Eintrag startet, rücken wir
in der Warteschlange weiter.
"""

import asyncio
import json
import logging
import random
import time
from pathlib import Path

from .mpv import Mpv, default_socket_path
from .subsonic import Subsonic

log = logging.getLogger("player")

REPEAT_MODES = ("off", "all", "one")
MAX_QUEUE = 2000
SAVE_INTERVAL = 60  # Sekunden zwischen Positions-Sicherungen während der Wiedergabe


class Player:
    def __init__(self, cfg, subsonic: Subsonic):
        self.cfg = cfg
        self.sub = subsonic
        # Zwei Dateien, um die SD-Karte zu schonen: die große Warteschlange wird nur bei
        # Änderungen geschrieben, die kleine Zustandsdatei (Index, Position, ...) öfter.
        self.state_file: Path = cfg.data_dir / "state.json"
        self.queue_file: Path = cfg.data_dir / "queue.json"
        self._saved_queue_version = 0
        self._save_lock = asyncio.Lock()
        self.queue: list[dict] = []
        self.index = -1
        self.repeat = "off"
        self.volume = cfg.default_volume
        self.paused = False
        self.loaded = False          # hat mpv den aktuellen Titel geladen?
        self.resume_position = 0.0   # Startposition, wenn noch nichts geladen ist
        self.queue_version = 0
        self.error: str | None = None
        self._pending_seek: float | None = None
        self._last_pos = 0.0                   # zuletzt gesehene Position (für mpv-Absturz)
        self._scrobbled = False
        self._cur_entry: int | None = None     # mpv-Eintrags-ID des aktuellen Titels
        self._next_entry: int | None = None    # mpv-Eintrags-ID des vorgepufferten Titels
        self._next_song: dict | None = None    # welcher Eintrag der Warteschlange das ist
        self._failed_entry: int | None = None
        self._failures = 0                     # fehlgeschlagene Titel in Folge
        self._lock = asyncio.Lock()
        self._listeners: set[asyncio.Queue] = set()
        self._dirty = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self.mpv = Mpv(cfg.mpv, default_socket_path(cfg.data_dir), cfg.audio_device,
                       self.volume, self._on_event, self._on_mpv_exit)

    # ---------- Lebenszyklus ----------

    async def start(self):
        self.cfg.data_dir.mkdir(parents=True, exist_ok=True)
        self._load_state()
        self.mpv.volume = self.volume
        for prop in ("pause", "idle-active", "volume"):
            await self.mpv.observe(prop)
        await self.mpv.start()
        self._tasks = [asyncio.create_task(self._broadcaster()),
                       asyncio.create_task(self._ticker())]
        if self.cfg.autoplay and self.queue:
            await self.play()

    async def stop(self):
        await self._save_state()
        for t in self._tasks:
            t.cancel()
        await self.mpv.stop()

    async def _on_mpv_exit(self):
        async with self._lock:
            if self.loaded:
                self.resume_position = self._last_pos
            self.loaded = False
            self._reset_entries()
            self._notify()

    # ---------- Hilfsfunktionen ----------

    @property
    def current(self) -> dict | None:
        return self.queue[self.index] if 0 <= self.index < len(self.queue) else None

    def _next_index(self, manual: bool = False) -> int | None:
        if not self.queue:
            return None
        if self.repeat == "one" and not manual:
            return self.index
        if self.index + 1 < len(self.queue):
            return self.index + 1
        return 0 if self.repeat in ("all", "one") else None

    async def _load_current(self, start: float = 0.0, paused: bool = False, user: bool = True):
        song = self.current
        if not song:
            return
        if user:
            self.error = None
            self._failures = 0
        self._pending_seek = start if start > 1 else None
        self._reset_entries()
        await self.mpv.set("pause", paused)
        await self.mpv.command("loadfile", self.sub.stream_url(song["id"]), "replace")
        self._cur_entry = await self._last_entry_id()
        self.loaded = True
        self.paused = paused
        self.resume_position = 0.0
        await self._sync_next()
        self._track_started()

    async def _sync_next(self):
        """Sorgt dafür, dass in mpv genau [aktuell, nächster] liegt."""
        if not self.loaded:
            self._reset_entries()
            return
        # Hat mpv gerade eben schon auf den vorgepufferten Titel gewechselt? Dann erst nachziehen.
        if self._next_entry is not None:
            playlist = await self.mpv.get("playlist") or []
            if any(e.get("current") and e.get("id") == self._next_entry for e in playlist):
                self._take_next(self._next_entry)
        await self.mpv.command("playlist-clear")  # entfernt alles außer dem aktuellen Eintrag
        nxt = self._next_index()
        self._next_song = self.queue[nxt] if nxt is not None else None
        self._next_entry = None
        if nxt is not None:
            await self.mpv.command("loadfile", self.sub.stream_url(self.queue[nxt]["id"]), "append")
            self._next_entry = await self._last_entry_id()

    async def _last_entry_id(self) -> int | None:
        playlist = await self.mpv.get("playlist") or []
        return playlist[-1].get("id") if playlist else None

    def _reset_entries(self):
        self._cur_entry = self._next_entry = self._next_song = None

    def _index_of(self, song: dict | None) -> int | None:
        return next((i for i, s in enumerate(self.queue) if s is song), None)

    def _take_next(self, entry_id: int):
        """mpv spielt jetzt den vorgepufferten Titel -> Warteschlange nachziehen."""
        idx = self._index_of(self._next_song)
        if idx is None:  # wurde gerade aus der Warteschlange entfernt
            idx = min(self.index + 1, len(self.queue) - 1)
        self.index = idx
        self._cur_entry, self._next_entry, self._next_song = entry_id, None, None
        self._track_started()

    def _track_started(self):
        self._scrobbled = False
        if song := self.current:
            asyncio.create_task(self._scrobble(song["id"], False))
        self._notify()

    async def _scrobble(self, song_id: str, submission: bool):
        try:
            await self.sub.scrobble(song_id, submission)
        except Exception as e:
            log.debug("Scrobble fehlgeschlagen: %s", e)

    async def _stop_playback(self):
        self.loaded = False
        self._reset_entries()
        self.paused = False
        self.resume_position = 0.0
        try:
            await self.mpv.command("stop")
        except Exception:
            pass

    # ---------- mpv-Ereignisse ----------

    async def _on_event(self, msg: dict):
        event = msg["event"]
        if event == "property-change":
            name, data = msg.get("name"), msg.get("data")
            if name == "idle-active" and data:
                await self._on_idle()
            elif name == "pause" and data is not None:
                self.paused = bool(data)
                self._notify()
            elif name == "volume" and data is not None:
                self.volume = round(data)
                self._notify()
        elif event == "start-file":
            await self._on_start_file(msg.get("playlist_entry_id"))
        elif event == "file-loaded":
            self._failures = 0
            if self._pending_seek:
                pos, self._pending_seek = self._pending_seek, None
                try:
                    await self.mpv.command("seek", pos, "absolute")
                except Exception:
                    pass
            self._notify()
        elif event == "end-file" and msg.get("reason") == "error":
            self._failures += 1
            self._failed_entry = msg.get("playlist_entry_id")
            self.error = "Ein Titel konnte nicht abgespielt werden und wurde übersprungen"
            log.warning("Titel nicht abspielbar: %s", msg.get("file_error"))
            self._notify()

    async def _on_start_file(self, entry_id: int | None):
        async with self._lock:
            # Nur der vorgepufferte Eintrag zählt; veraltete Ereignisse haben eine andere ID
            if not self.loaded or entry_id is None or entry_id != self._next_entry:
                return
            self._take_next(entry_id)
            await self._sync_next()
            await self._save_state()

    async def _on_idle(self):
        async with self._lock:
            if not self.loaded or not await self.mpv.get("idle-active", False):
                return
            if self._failures:
                # mpv ist leer gelaufen, weil der zuletzt versuchte Titel kaputt war -> überspringen
                failed = self.index
                if self._failed_entry is not None and self._failed_entry == self._next_entry:
                    idx = self._index_of(self._next_song)
                    failed = self.index if idx is None else idx
                if self._failures < 3 and self._skip_after(failed):
                    await self._load_current(user=False)
                    await self._save_state()
                    return
                if self._failures >= 3:
                    self.error = "Mehrere Titel nacheinander nicht abspielbar – ist Navidrome erreichbar?"
            # Ende der Warteschlange erreicht (oder aufgegeben)
            self.loaded = False
            self._reset_entries()
            self.paused = False
            self.resume_position = 0.0
            self._notify()
            await self._save_state()

    def _skip_after(self, failed: int) -> bool:
        self.index = failed
        nxt = self._next_index(manual=True)
        if nxt is None or nxt == failed:
            return False
        self.index = nxt
        return True

    # ---------- Steuerung ----------

    async def play(self):
        async with self._lock:
            if self.loaded:
                await self.mpv.set("pause", False)
            elif self.queue:
                if self.index < 0:
                    self.index = 0
                await self._load_current(self.resume_position)

    async def pause(self):
        async with self._lock:
            if self.loaded:
                await self.mpv.set("pause", True)
                await self._save_state()

    async def toggle(self):
        if self.loaded and not self.paused:
            await self.pause()
        else:
            await self.play()

    async def stop_playback(self):
        async with self._lock:
            await self._stop_playback()
            self._notify()

    async def next(self):
        async with self._lock:
            nxt = self._next_index(manual=True)
            if nxt is None:
                await self._stop_playback()
                self._notify()
                return
            self.index = nxt
            await self._load_current(paused=self.paused and self.loaded)
            await self._save_state()

    async def prev(self):
        async with self._lock:
            if not self.queue:
                return
            if self.loaded and (await self.mpv.get("time-pos") or 0) > 5:
                await self.mpv.command("seek", 0, "absolute")
                return
            if self.index > 0:
                self.index -= 1
            elif self.repeat == "all":
                self.index = len(self.queue) - 1
            await self._load_current(paused=self.paused and self.loaded)
            await self._save_state()

    async def seek(self, position: float):
        async with self._lock:
            position = max(0.0, float(position))
            if self.loaded:
                await self.mpv.command("seek", position, "absolute")
            else:
                self.resume_position = position
            self._notify()

    async def set_volume(self, volume: int):
        self.volume = max(0, min(100, int(volume)))
        await self.mpv.set("volume", self.volume)
        self._notify()

    async def set_repeat(self, mode: str):
        if mode not in REPEAT_MODES:
            raise ValueError(f"Unbekannter Modus: {mode}")
        async with self._lock:
            self.repeat = mode
            await self._sync_next()
            self._notify()
            await self._save_state()

    # ---------- Warteschlange ----------

    async def _queue_changed(self):
        self.queue_version += 1
        await self._sync_next()
        self._notify()
        await self._save_state()

    async def replace_queue(self, songs: list[dict], start: int = 0, shuffle: bool = False):
        songs = songs[:MAX_QUEUE]
        if not songs:
            return
        if shuffle:
            random.shuffle(songs)
            start = 0
        async with self._lock:
            self.queue = songs
            self.index = max(0, min(start, len(songs) - 1))
            self.queue_version += 1
            await self._load_current()
            await self._save_state()

    async def add(self, songs: list[dict], mode: str = "end"):
        """mode: 'now' (sofort spielen), 'next' (als Nächstes) oder 'end' (hinten anhängen)."""
        async with self._lock:
            songs = songs[:max(0, MAX_QUEUE - len(self.queue))]
            if not songs:
                return
            was_empty = not self.queue
            if mode in ("now", "next") and self.queue:
                pos = self.index + 1
                self.queue[pos:pos] = songs
            else:
                pos = len(self.queue)
                self.queue.extend(songs)
            if was_empty or mode == "now":
                self.index = pos if not was_empty else 0
                self.queue_version += 1
                await self._load_current()
                await self._save_state()
            else:
                await self._queue_changed()

    async def jump(self, index: int):
        async with self._lock:
            if 0 <= index < len(self.queue):
                self.index = index
                await self._load_current()
                await self._save_state()

    async def remove(self, index: int):
        async with self._lock:
            if not 0 <= index < len(self.queue):
                return
            self.queue.pop(index)
            if index < self.index:
                self.index -= 1
            elif index == self.index:
                if self.index >= len(self.queue):
                    self.index = len(self.queue) - 1
                    await self._stop_playback()
                elif self.loaded:
                    await self._load_current(paused=self.paused)
            if not self.queue:
                self.index = -1
            await self._queue_changed()

    async def move(self, src: int, dst: int):
        async with self._lock:
            n = len(self.queue)
            if not (0 <= src < n and 0 <= dst < n) or src == dst:
                return
            self.queue.insert(dst, self.queue.pop(src))
            if src == self.index:
                self.index = dst
            elif src < self.index <= dst:
                self.index -= 1
            elif dst <= self.index < src:
                self.index += 1
            await self._queue_changed()

    async def shuffle(self):
        """Mischt alle Titel außer dem aktuellen, der aktuelle wandert nach vorn."""
        async with self._lock:
            if len(self.queue) < 2:
                return
            cur = self.current
            rest = [s for i, s in enumerate(self.queue) if i != self.index]
            random.shuffle(rest)
            self.queue = ([cur] if cur else []) + rest
            self.index = 0 if cur else -1
            await self._queue_changed()

    async def clear(self):
        async with self._lock:
            await self._stop_playback()
            self.queue = []
            self.index = -1
            await self._queue_changed()

    # ---------- Zustand für die Oberfläche ----------

    async def state(self) -> dict:
        position = self.resume_position
        if self.loaded:
            position = self._last_pos = await self.mpv.get("time-pos", 0) or 0
        if not self.loaded:
            status = "stopped"
        else:
            status = "paused" if self.paused else "playing"
        cur = self.current
        return {
            "status": status,
            "current": cur,
            "index": self.index,
            "position": round(position, 2),
            "duration": cur["duration"] if cur else 0,
            "volume": self.volume,
            "repeat": self.repeat,
            "queue_length": len(self.queue),
            "queue_version": self.queue_version,
            "mpv_connected": self.mpv.connected,
            "error": self.error,
        }

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=8)
        self._listeners.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._listeners.discard(q)

    def _notify(self):
        self._dirty.set()

    async def _broadcaster(self):
        while True:
            await self._dirty.wait()
            await asyncio.sleep(0.05)  # mehrere Änderungen zusammenfassen
            self._dirty.clear()
            try:
                state = await self.state()
            except Exception:
                log.exception("Zustand nicht lesbar")
                continue
            for q in list(self._listeners):
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(state)

    async def _ticker(self):
        """Scrobbelt nach halber Laufzeit und speichert regelmäßig die Position."""
        last_save = time.monotonic()
        while True:
            await asyncio.sleep(5)
            if not self.loaded or self.paused:
                continue
            cur = self.current
            pos = self._last_pos = await self.mpv.get("time-pos", 0) or 0
            if cur and not self._scrobbled and pos > min(max(cur["duration"], 30) / 2, 240):
                self._scrobbled = True
                asyncio.create_task(self._scrobble(cur["id"], True))
            if time.monotonic() - last_save > SAVE_INTERVAL:
                last_save = time.monotonic()
                await self._save_state(pos)

    # ---------- Speichern / Laden ----------

    async def _save_state(self, position: float | None = None):
        if position is None:
            position = self.resume_position
            if self.loaded:
                position = await self.mpv.get("time-pos", 0) or 0
        state = {"index": self.index, "position": round(position, 1),
                 "volume": self.volume, "repeat": self.repeat}
        version = self.queue_version
        queue = list(self.queue) if version != self._saved_queue_version else None

        def write():
            # Warteschlange zuerst, damit der Index nie auf eine ältere Warteschlange zeigt
            if queue is not None:
                _atomic_write(self.queue_file, {"queue": queue})
            _atomic_write(self.state_file, state)

        async with self._save_lock:
            try:
                # im Thread, damit eine lange Warteschlange die App auf dem Pi 2 nicht stocken lässt
                await asyncio.to_thread(write)
                if queue is not None:
                    self._saved_queue_version = version
            except OSError:
                log.exception("Zustand konnte nicht gespeichert werden")

    def _load_state(self):
        try:
            data = json.loads(self.state_file.read_text())
        except (OSError, ValueError):
            return
        try:
            queue = json.loads(self.queue_file.read_text()).get("queue", [])
        except (OSError, ValueError):
            # altes Format: Warteschlange steckte in state.json -> beim nächsten Speichern umziehen
            queue = data.get("queue", [])
            self._saved_queue_version = -1
        self.queue = queue[:MAX_QUEUE]
        self.index = min(int(data.get("index", -1)), len(self.queue) - 1) if self.queue else -1
        self.resume_position = float(data.get("position", 0))
        self.volume = int(data.get("volume", self.volume))
        if data.get("repeat") in REPEAT_MODES:
            self.repeat = data["repeat"]


def _atomic_write(path: Path, data: dict):
    """Schreibt über eine .tmp-Datei und benennt um – übersteht Stromausfälle."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False))
    tmp.replace(path)
