import argparse
import logging

import uvicorn

from .config import load_config
from .main import create_app


def main():
    parser = argparse.ArgumentParser(description="Pi-Musikplayer für Navidrome")
    parser.add_argument("--config", help="Pfad zur config.toml")
    parser.add_argument("--port", type=int, help="Port überschreiben (z.B. 8080 zum Entwickeln)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # loggt sonst Login-Token mit
    cfg = load_config(args.config)
    if args.port:
        cfg.port = args.port
    uvicorn.run(create_app(cfg), host=cfg.host, port=cfg.port, log_level="warning")


if __name__ == "__main__":
    main()
