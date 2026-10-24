import asyncio
import contextlib
import logging
from collections import OrderedDict

import httpx
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from .config import ROOT, Config
from .player import Player
from .subsonic import Subsonic, SubsonicError

log = logging.getLogger("app")
WEB_DIR = ROOT / "web"
ALBUM_LIST_TYPES = {"newest", "random", "recent", "frequent", "alphabeticalByName", "starred"}


def create_app(cfg: Config) -> Starlette:
    sub = Subsonic(cfg.navidrome_url, cfg.username, cfg.password,
                   cfg.max_bitrate, cfg.transcode_format)
    player = Player(cfg, sub)
    covers: OrderedDict[str, tuple[bytes, str]] = OrderedDict()

    @contextlib.asynccontextmanager
    async def lifespan(app):
        await player.start()
        try:
            await sub.ping()
            log.info("Verbunden mit Navidrome: %s", cfg.navidrome_url)
        except Exception as e:
            log.error("Navidrome nicht erreichbar (%s) – läuft trotzdem weiter", e)
        yield
        await player.stop()
        await sub.close()

    async def body(request: Request) -> dict:
        try:
            data = await request.json()
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    async def resolve(src: dict) -> list[dict]:
        kind, item_id = src.get("type"), src.get("id")
        if kind == "playlist":
            return (await sub.playlist(item_id))["songs"]
        if kind == "album":
            return (await sub.album(item_id))["songs"]
        if kind == "artist":
            return await sub.artist_songs(item_id)
        if kind == "song":
            return [await sub.song(item_id)]
        if kind == "random":
            return await sub.random_songs(int(src.get("size", 50)))
        raise HTTPException(400, f"Unbekannte Quelle: {kind}")

    # ---------- Wiedergabe ----------

    async def get_state(request):
        return JSONResponse(await player.state())

    async def player_action(request):
        action = request.path_params["action"]
        actions = {"play": player.play, "pause": player.pause, "toggle": player.toggle,
                   "next": player.next, "prev": player.prev, "stop": player.stop_playback}
        if action not in actions:
            raise HTTPException(404)
        await actions[action]()
        return JSONResponse({"ok": True})

    async def seek(request):
        await player.seek((await body(request)).get("position", 0))
        return JSONResponse({"ok": True})

    async def volume(request):
        await player.set_volume((await body(request)).get("volume", 50))
        return JSONResponse({"ok": True})

    async def repeat(request):
        try:
            await player.set_repeat((await body(request)).get("mode", "off"))
        except ValueError as e:
            raise HTTPException(400, str(e))
        return JSONResponse({"ok": True})

    # ---------- Warteschlange ----------

    async def get_queue(request):
        return JSONResponse({"queue": player.queue, "index": player.index,
                             "version": player.queue_version})

    async def queue_play(request):
        data = await body(request)
        songs = await resolve(data)
        if not songs:
            raise HTTPException(404, "Keine Titel gefunden")
        await player.replace_queue(songs, int(data.get("index", 0)), bool(data.get("shuffle")))
        return JSONResponse({"ok": True, "count": len(songs)})

    async def queue_add(request):
        data = await body(request)
        songs = await resolve(data)
        mode = data.get("mode", "end")
        if mode not in ("now", "next", "end"):
            raise HTTPException(400, "mode muss now, next oder end sein")
        await player.add(songs, mode)
        return JSONResponse({"ok": True, "count": len(songs)})

    async def queue_action(request):
        action = request.path_params["action"]
        data = await body(request)
        if action == "jump":
            await player.jump(int(data.get("index", 0)))
        elif action == "remove":
            await player.remove(int(data.get("index", -1)))
        elif action == "move":
            await player.move(int(data.get("from", -1)), int(data.get("to", -1)))
        elif action == "shuffle":
            await player.shuffle()
        elif action == "clear":
            await player.clear()
        else:
            raise HTTPException(404)
        return JSONResponse({"ok": True})

    # ---------- Bibliothek ----------

    async def lib_playlists(request):
        return JSONResponse(await sub.playlists())

    async def lib_playlist(request):
        return JSONResponse(await sub.playlist(request.path_params["id"]))

    async def lib_artists(request):
        return JSONResponse(await sub.artists())

    async def lib_artist(request):
        return JSONResponse(await sub.artist(request.path_params["id"]))

    async def lib_album(request):
        return JSONResponse(await sub.album(request.path_params["id"]))

    async def lib_albums(request):
        kind = request.query_params.get("type", "newest")
        if kind not in ALBUM_LIST_TYPES:
            raise HTTPException(400, "Unbekannter Typ")
        offset = int(request.query_params.get("offset", 0))
        return JSONResponse(await sub.album_list(kind, 40, offset))

    async def lib_search(request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return JSONResponse({"artists": [], "albums": [], "songs": []})
        return JSONResponse(await sub.search(q))

    async def cover(request):
        cover_id = request.path_params["id"]
        size = max(48, min(int(request.query_params.get("size", 300)), 800))
        key = f"{cover_id}:{size}"
        if key in covers:
            covers.move_to_end(key)
            data, ctype = covers[key]
        else:
            try:
                data, ctype = await sub.cover(cover_id, size)
            except (SubsonicError, httpx.HTTPError):
                return Response(status_code=404)
            covers[key] = (data, ctype)
            if len(covers) > 150:
                covers.popitem(last=False)
        return Response(data, media_type=ctype,
                        headers={"Cache-Control": "public, max-age=604800"})

    # ---------- Live-Updates ----------

    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        q = player.subscribe()

        async def sender():
            await ws.send_json({"type": "state", "state": await player.state()})
            while True:
                await ws.send_json({"type": "state", "state": await q.get()})

        async def receiver():
            while True:
                await ws.receive_text()  # Client schickt nur Pings; wir warten auf das Trennen

        tasks = [asyncio.create_task(sender()), asyncio.create_task(receiver())]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for t in tasks:
                t.cancel()
            player.unsubscribe(q)
            with contextlib.suppress(Exception):
                await ws.close()

    # ---------- Fehlerbehandlung ----------

    async def subsonic_error(request, exc):
        return JSONResponse({"error": f"Navidrome: {exc}"}, status_code=502)

    async def http_error(request, exc):
        return JSONResponse({"error": f"Navidrome nicht erreichbar: {exc}"}, status_code=502)

    async def http_exception(request, exc: HTTPException):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    async def value_error(request, exc):
        return JSONResponse({"error": "Ungültige Eingabe"}, status_code=400)

    async def index(request):
        return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    routes = [
        Route("/", index),
        Route("/api/state", get_state),
        Route("/api/player/seek", seek, methods=["POST"]),
        Route("/api/player/volume", volume, methods=["POST"]),
        Route("/api/player/repeat", repeat, methods=["POST"]),
        Route("/api/player/{action}", player_action, methods=["POST"]),
        Route("/api/queue", get_queue),
        Route("/api/queue/play", queue_play, methods=["POST"]),
        Route("/api/queue/add", queue_add, methods=["POST"]),
        Route("/api/queue/{action}", queue_action, methods=["POST"]),
        Route("/api/library/playlists", lib_playlists),
        Route("/api/library/playlist/{id}", lib_playlist),
        Route("/api/library/artists", lib_artists),
        Route("/api/library/artist/{id}", lib_artist),
        Route("/api/library/album/{id}", lib_album),
        Route("/api/library/albums", lib_albums),
        Route("/api/library/search", lib_search),
        Route("/api/cover/{id}", cover),
        WebSocketRoute("/api/ws", ws_endpoint),
        Mount("/static", StaticFiles(directory=WEB_DIR), name="static"),
    ]
    return Starlette(
        routes=routes,
        lifespan=lifespan,
        exception_handlers={
            SubsonicError: subsonic_error,
            httpx.HTTPError: http_error,
            HTTPException: http_exception,
            ValueError: value_error,
        },
    )
