import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    navidrome_url: str
    username: str
    password: str
    max_bitrate: int
    transcode_format: str
    host: str
    port: int
    audio_device: str
    mpv: str
    default_volume: int
    autoplay: bool
    data_dir: Path


def load_config(path: str | None = None) -> Config:
    path = Path(path or os.environ.get("MUSIC_PLAYER_CONFIG") or ROOT / "config.toml")
    if not path.exists():
        raise SystemExit(f"Konfiguration fehlt: {path} (Vorlage: config.example.toml)")
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    nav = raw.get("navidrome", {})
    server = raw.get("server", {})
    player = raw.get("player", {})
    storage = raw.get("storage", {})

    for key in ("url", "username", "password"):
        if not nav.get(key):
            raise SystemExit(f"config: [navidrome] {key} ist nicht gesetzt")

    data_dir = Path(storage.get("data_dir", "data"))
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir

    return Config(
        navidrome_url=nav["url"].rstrip("/"),
        username=nav["username"],
        password=nav["password"],
        max_bitrate=int(nav.get("max_bitrate", 0)),
        transcode_format=nav.get("transcode_format", "mp3"),
        host=server.get("host", "0.0.0.0"),
        port=int(server.get("port", 8080)),
        audio_device=player.get("audio_device", "auto"),
        mpv=player.get("mpv", "mpv"),
        default_volume=int(player.get("default_volume", 70)),
        autoplay=bool(player.get("autoplay", False)),
        data_dir=data_dir,
    )
