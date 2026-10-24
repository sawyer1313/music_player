"""Minimaler Client für die Subsonic-API, wie Navidrome sie anbietet."""

import asyncio
import hashlib
import secrets
from urllib.parse import urlencode

import httpx

API_VERSION = "1.16.1"
CLIENT_NAME = "pi-player"


class SubsonicError(Exception):
    pass


def song(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "title": raw.get("title", ""),
        "artist": raw.get("artist", ""),
        "artistId": raw.get("artistId"),
        "album": raw.get("album", ""),
        "albumId": raw.get("albumId"),
        "coverArt": raw.get("coverArt"),
        "duration": raw.get("duration", 0),
        "track": raw.get("track"),
    }


def album(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "name": raw.get("name") or raw.get("title", ""),
        "artist": raw.get("artist", ""),
        "artistId": raw.get("artistId"),
        "coverArt": raw.get("coverArt"),
        "year": raw.get("year"),
        "songCount": raw.get("songCount", 0),
        "duration": raw.get("duration", 0),
    }


def artist(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "name": raw.get("name", ""),
        "albumCount": raw.get("albumCount", 0),
        "coverArt": raw.get("coverArt"),
    }


def playlist(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "name": raw.get("name", ""),
        "songCount": raw.get("songCount", 0),
        "duration": raw.get("duration", 0),
        "coverArt": raw.get("coverArt"),
        "owner": raw.get("owner"),
    }


class Subsonic:
    def __init__(self, url: str, username: str, password: str,
                 max_bitrate: int = 0, transcode_format: str = "mp3"):
        self.base = url.rstrip("/") + "/rest/"
        self.username = username
        self.password = password
        self.max_bitrate = max_bitrate
        self.transcode_format = transcode_format
        self.http = httpx.AsyncClient(timeout=20, follow_redirects=True)

    async def close(self):
        await self.http.aclose()

    def _auth(self) -> dict:
        salt = secrets.token_hex(8)
        token = hashlib.md5((self.password + salt).encode()).hexdigest()
        return {"u": self.username, "t": token, "s": salt,
                "v": API_VERSION, "c": CLIENT_NAME, "f": "json"}

    async def _get(self, endpoint: str, **params) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        r = await self.http.get(self.base + endpoint, params={**self._auth(), **params})
        r.raise_for_status()
        body = r.json().get("subsonic-response", {})
        if body.get("status") != "ok":
            raise SubsonicError(body.get("error", {}).get("message", "Unbekannter Fehler"))
        return body

    def stream_url(self, song_id: str) -> str:
        params = {**self._auth(), "id": song_id}
        if self.max_bitrate:
            params.update(maxBitRate=self.max_bitrate, format=self.transcode_format)
        else:
            params["format"] = "raw"
        return self.base + "stream?" + urlencode(params)

    async def cover(self, cover_id: str, size: int) -> tuple[bytes, str]:
        r = await self.http.get(self.base + "getCoverArt",
                                params={**self._auth(), "id": cover_id, "size": size})
        r.raise_for_status()
        ctype = r.headers.get("content-type", "image/jpeg")
        if "json" in ctype or "xml" in ctype:
            raise SubsonicError("Kein Cover")
        return r.content, ctype

    async def ping(self):
        await self._get("ping")

    async def playlists(self) -> list[dict]:
        body = await self._get("getPlaylists")
        return [playlist(p) for p in body.get("playlists", {}).get("playlist", [])]

    async def playlist(self, playlist_id: str) -> dict:
        raw = (await self._get("getPlaylist", id=playlist_id))["playlist"]
        return {**playlist(raw), "songs": [song(s) for s in raw.get("entry", [])]}

    async def artists(self) -> list[dict]:
        body = await self._get("getArtists")
        result = []
        for index in body.get("artists", {}).get("index", []):
            result.extend(artist(a) for a in index.get("artist", []))
        return result

    async def artist(self, artist_id: str) -> dict:
        raw = (await self._get("getArtist", id=artist_id))["artist"]
        return {**artist(raw), "albums": [album(a) for a in raw.get("album", [])]}

    async def album(self, album_id: str) -> dict:
        raw = (await self._get("getAlbum", id=album_id))["album"]
        return {**album(raw), "songs": [song(s) for s in raw.get("song", [])]}

    async def artist_songs(self, artist_id: str) -> list[dict]:
        albums = (await self.artist(artist_id))["albums"]
        details = await asyncio.gather(*(self.album(a["id"]) for a in albums))
        return [s for d in details for s in d["songs"]]

    async def album_list(self, kind: str, size: int = 40, offset: int = 0) -> list[dict]:
        body = await self._get("getAlbumList2", type=kind, size=size, offset=offset)
        return [album(a) for a in body.get("albumList2", {}).get("album", [])]

    async def search(self, query: str) -> dict:
        body = await self._get("search3", query=query,
                               artistCount=10, albumCount=20, songCount=40)
        res = body.get("searchResult3", {})
        return {
            "artists": [artist(a) for a in res.get("artist", [])],
            "albums": [album(a) for a in res.get("album", [])],
            "songs": [song(s) for s in res.get("song", [])],
        }

    async def song(self, song_id: str) -> dict:
        return song((await self._get("getSong", id=song_id))["song"])

    async def random_songs(self, size: int = 50) -> list[dict]:
        body = await self._get("getRandomSongs", size=size)
        return [song(s) for s in body.get("randomSongs", {}).get("song", [])]

    async def scrobble(self, song_id: str, submission: bool):
        await self._get("scrobble", id=song_id, submission=str(submission).lower())
