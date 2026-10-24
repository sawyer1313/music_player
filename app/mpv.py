"""Startet mpv im Hintergrund und spricht über dessen JSON-IPC-Socket mit ihm."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Awaitable, Callable

log = logging.getLogger("mpv")


class MpvError(Exception):
    pass


class Mpv:
    def __init__(self, binary: str, socket_path: Path, audio_device: str, volume: int,
                 on_event: Callable[[dict], Awaitable[None]],
                 on_exit: Callable[[], Awaitable[None]]):
        self.binary = binary
        self.socket_path = socket_path
        self.audio_device = audio_device
        self.volume = volume
        self.on_event = on_event
        self.on_exit = on_exit
        self.proc: asyncio.subprocess.Process | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.pending: dict[int, asyncio.Future] = {}
        self.next_id = 1
        self.observed: list[str] = []
        self.connected = False
        self._supervisor: asyncio.Task | None = None
        self._stopping = False

    async def start(self):
        await self._spawn()
        self._supervisor = asyncio.create_task(self._supervise())

    async def stop(self):
        self._stopping = True
        if self._supervisor:
            self._supervisor.cancel()
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), 5)
            except asyncio.TimeoutError:
                self.proc.kill()

    async def _spawn(self):
        if self.socket_path.exists():
            self.socket_path.unlink()
        args = [
            self.binary,
            "--idle=yes",
            "--no-video",
            "--no-terminal",
            "--no-config",
            "--ytdl=no",
            "--prefetch-playlist=yes",
            "--cache=yes",
            "--demuxer-max-bytes=16MiB",
            "--network-timeout=20",
            "--volume-max=100",
            f"--volume={self.volume}",
            f"--audio-device={self.audio_device}",
            f"--input-ipc-server={self.socket_path}",
        ]
        self.proc = await asyncio.create_subprocess_exec(
            *args, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL)

        for _ in range(100):
            if self.socket_path.exists():
                break
            if self.proc.returncode is not None:
                raise MpvError(f"mpv beendet sich sofort (Code {self.proc.returncode})")
            await asyncio.sleep(0.1)
        else:
            raise MpvError("mpv-Socket erscheint nicht")

        reader, self.writer = await asyncio.open_unix_connection(str(self.socket_path))
        self.connected = True
        asyncio.create_task(self._read(reader))
        for i, name in enumerate(self.observed, start=1):
            await self.command("observe_property", i, name)
        log.info("mpv läuft (pid %s)", self.proc.pid)

    async def _supervise(self):
        """Startet mpv neu, falls es abstürzt."""
        while not self._stopping:
            await self.proc.wait()
            if self._stopping:
                return
            log.warning("mpv beendet (Code %s), starte neu", self.proc.returncode)
            self.connected = False
            try:
                await self.on_exit()  # vor dem Neustart, damit der Player den Zustand sichert
                await asyncio.sleep(2)
                await self._spawn()
            except Exception:
                log.exception("Neustart von mpv fehlgeschlagen")

    async def _read(self, reader: asyncio.StreamReader):
        try:
            while line := await reader.readline():
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if "request_id" in msg:
                    fut = self.pending.pop(msg["request_id"], None)
                    if fut and not fut.done():
                        if msg.get("error") == "success":
                            fut.set_result(msg.get("data"))
                        else:
                            fut.set_exception(MpvError(msg.get("error")))
                elif "event" in msg:
                    asyncio.create_task(self._dispatch(msg))
        finally:
            self.connected = False
            for fut in self.pending.values():
                if not fut.done():
                    fut.set_exception(MpvError("Verbindung zu mpv verloren"))
            self.pending.clear()

    async def _dispatch(self, msg: dict):
        try:
            await self.on_event(msg)
        except Exception:
            log.exception("Fehler bei mpv-Ereignis %s", msg.get("event"))

    async def command(self, *args):
        if not self.connected or not self.writer:
            raise MpvError("mpv nicht verbunden")
        req_id = self.next_id
        self.next_id += 1
        fut = asyncio.get_running_loop().create_future()
        self.pending[req_id] = fut
        self.writer.write(json.dumps({"command": list(args), "request_id": req_id}).encode() + b"\n")
        await self.writer.drain()
        return await asyncio.wait_for(fut, 10)

    async def get(self, prop: str, default=None):
        try:
            return await self.command("get_property", prop)
        except (MpvError, asyncio.TimeoutError):
            return default

    async def set(self, prop: str, value):
        return await self.command("set_property", prop, value)

    async def observe(self, name: str):
        self.observed.append(name)
        if self.connected:
            await self.command("observe_property", len(self.observed), name)


def default_socket_path(data_dir: Path) -> Path:
    run_dir = os.environ.get("XDG_RUNTIME_DIR")
    return Path(run_dir) / "music-player-mpv.sock" if run_dir else data_dir / "mpv.sock"
