"""Short-term goals. Three missions are active at a time, in order."""

from __future__ import annotations

from dataclasses import dataclass

ACTIVE_COUNT = 3


@dataclass(frozen=True)
class Mission:
    id: str
    text: str
    stat: str        # key in RunScore.stats()
    target: int
    reward: int      # gems


MISSIONS = (
    Mission("score_10", "Score 10 in one run", "score", 10, 10),
    Mission("gems_5", "Collect 5 gems in one run", "gems", 5, 15),
    Mission("near_3", "Pull off 3 near misses in one run", "near_misses", 3, 20),
    Mission("combo_3", "Reach a x3 multiplier", "best_multiplier", 3, 20),
    Mission("score_50", "Score 50 in one run", "score", 50, 30),
    Mission("gems_30", "Collect 30 gems in one run", "gems", 30, 40),
    Mission("combo_5", "Reach the x5 multiplier", "best_multiplier", 5, 40),
    Mission("score_150", "Score 150 in one run", "score", 150, 60),
)


def active_missions(done) -> list[Mission]:
    return [m for m in MISSIONS if m.id not in done][:ACTIVE_COUNT]


def completed_by(stats: dict, done) -> list[Mission]:
    """Active missions that this run's stats complete."""
    return [m for m in active_missions(done) if stats.get(m.stat, 0) >= m.target]
