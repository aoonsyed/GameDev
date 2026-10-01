"""Save/load progress: browser localStorage on the web, a JSON file on desktop."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .logic.progress import SaveData

SAVE_KEY = "orbit_hop_save_v1"


def default_save_path() -> Path:
    override = os.environ.get("ORBIT_HOP_SAVE")
    if override:
        return Path(override)
    return Path.home() / ".orbit_hop" / "save.json"


class Storage:
    def __init__(self, path=None, web: bool | None = None):
        self.web = sys.platform == "emscripten" if web is None else web
        self.path = Path(path) if path else default_save_path()

    def load(self) -> SaveData:
        try:
            raw = self._read()
            return SaveData.from_dict(json.loads(raw)) if raw else SaveData()
        except Exception:
            # A corrupt or unreadable save must never stop the game starting.
            return SaveData()

    def save(self, data: SaveData) -> bool:
        try:
            self._write(json.dumps(data.to_dict()))
            return True
        except Exception:
            return False

    def _read(self):
        if self.web:
            from platform import window  # pygbag's bridge to the browser
            return window.localStorage.getItem(SAVE_KEY)
        if self.path.exists():
            return self.path.read_text(encoding="utf-8")
        return None

    def _write(self, raw: str) -> None:
        if self.web:
            from platform import window
            window.localStorage.setItem(SAVE_KEY, raw)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(raw, encoding="utf-8")
        os.replace(tmp, self.path)
