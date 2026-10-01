"""Score, gems and the combo multiplier for one run.

Each safe landing scores the current multiplier. Catching a gem mid-jump grows
the combo (and multiplier, up to MAX_MULTIPLIER); a jump without a gem resets it.
"""

from dataclasses import dataclass

MAX_MULTIPLIER = 5


@dataclass
class RunScore:
    score: int = 0
    gems: int = 0
    combo: int = 0
    best_multiplier: int = 1
    jumps: int = 0
    near_misses: int = 0
    _gem_this_jump: bool = False

    @property
    def multiplier(self) -> int:
        return min(1 + self.combo, MAX_MULTIPLIER)

    def on_jump(self) -> None:
        self.jumps += 1
        self._gem_this_jump = False

    def on_gem(self) -> None:
        self.gems += 1
        self.combo += 1
        self._gem_this_jump = True
        self.best_multiplier = max(self.best_multiplier, self.multiplier)

    def on_land(self, near_miss: bool = False) -> int:
        if not self._gem_this_jump:
            self.combo = 0
        self._gem_this_jump = False
        points = self.multiplier
        self.score += points
        if near_miss:
            self.near_misses += 1
        return points

    def stats(self) -> dict:
        return {
            "score": self.score,
            "gems": self.gems,
            "best_multiplier": self.best_multiplier,
            "jumps": self.jumps,
            "near_misses": self.near_misses,
        }
