"""Serve the generated site/ directory without relying on the current working directory."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve the generated Baylor Sing scrollytelling site."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to. Defaults to 8080.",
    )
    parser.add_argument(
        "--bind",
        default="127.0.0.1",
        help="Interface to bind to. Defaults to 127.0.0.1.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    handler = partial(SimpleHTTPRequestHandler, directory=str(SITE_DIR))

    with ThreadingHTTPServer((args.bind, args.port), handler) as server:
        print(f"Serving {SITE_DIR} at http://{args.bind}:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
