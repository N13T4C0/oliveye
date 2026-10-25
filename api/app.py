"""Vercel entrypoint: the platform loads the top-level `app` from this file."""

from pathlib import Path

from oliveye_api import create_app

app = create_app(Path(__file__).resolve().parent / "data")
