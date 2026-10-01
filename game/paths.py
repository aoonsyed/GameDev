"""Locate bundled assets in source checkouts, pygbag builds and PyInstaller exes."""

import sys
from pathlib import Path


def base_dir() -> Path:
    frozen = getattr(sys, "_MEIPASS", None)  # set inside a PyInstaller bundle
    return Path(frozen) if frozen else Path(__file__).resolve().parent.parent


def asset_path(*parts: str) -> Path:
    return base_dir().joinpath("assets", *parts)
