"""Persistent player progress: best scores, gems, skins, missions, settings."""

from __future__ import annotations

from dataclasses import dataclass, field

from .missions import Mission, completed_by
from .skins import DEFAULT_SKIN, SKIN_IDS

SAVE_VERSION = 1


@dataclass
class RunResult:
    new_best: bool
    daily_new_best: bool
    missions: list
    gems_earned: int


@dataclass
class SaveData:
    best: int = 0
    gems: int = 0
    skin: str = DEFAULT_SKIN
    owned: list = field(default_factory=lambda: [DEFAULT_SKIN])
    missions_done: list = field(default_factory=list)
    daily_date: str = ""
    daily_best: int = 0
    runs: int = 0
    sound: bool = True
    shake: bool = True          # screen shake and flashes (off = reduced motion)

    def to_dict(self) -> dict:
        return {
            "version": SAVE_VERSION,
            "best": self.best,
            "gems": self.gems,
            "skin": self.skin,
            "owned": list(self.owned),
            "missions_done": list(self.missions_done),
            "daily_date": self.daily_date,
            "daily_best": self.daily_best,
            "runs": self.runs,
            "sound": self.sound,
            "shake": self.shake,
        }

    @classmethod
    def from_dict(cls, data) -> SaveData:
        """Build from stored data, ignoring anything missing or malformed."""
        save = cls()
        if not isinstance(data, dict):
            return save

        for key in ("best", "gems", "daily_best", "runs"):
            v = data.get(key)
            if isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                setattr(save, key, v)
        for key in ("sound", "shake"):
            if isinstance(data.get(key), bool):
                setattr(save, key, data[key])
        if isinstance(data.get("daily_date"), str):
            save.daily_date = data["daily_date"]

        owned = data.get("owned")
        if isinstance(owned, list):
            save.owned = [s for s in dict.fromkeys(owned) if s in SKIN_IDS]
        if DEFAULT_SKIN not in save.owned:
            save.owned.insert(0, DEFAULT_SKIN)
        if data.get("skin") in save.owned:
            save.skin = data["skin"]

        done = data.get("missions_done")
        if isinstance(done, list):
            save.missions_done = [m for m in done if isinstance(m, str)]
        return save

    def daily_best_for(self, key: str) -> int:
        return self.daily_best if self.daily_date == key else 0

    def record_run(self, stats: dict, daily: str | None = None) -> RunResult:
        """Fold a finished run into progress. `daily` is the day key for daily runs."""
        score = stats.get("score", 0)
        new_best = score > self.best
        if new_best:
            self.best = score

        daily_new_best = False
        if daily is not None:
            if self.daily_date != daily:
                self.daily_date, self.daily_best = daily, 0
            if score > self.daily_best:
                self.daily_best = score
                daily_new_best = True

        missions: list[Mission] = completed_by(stats, self.missions_done)
        self.missions_done.extend(m.id for m in missions)
        earned = stats.get("gems", 0) + sum(m.reward for m in missions)
        self.gems += earned
        self.runs += 1
        return RunResult(new_best, daily_new_best, missions, earned)
