"""Speed and spawn curves. Difficulty rises every LEVEL_STEP rings landed.

What the player feels is the orb's speed *relative* to the next ring (`rel`):
it sets how fast the landing spot sweeps past hazards. Every ring you land on
burns a fuse; the fuse always outlasts the longest possible wait for a safe
landing plus a reaction budget, so rings get faster and tighter without ever
trapping the player.
"""

from dataclasses import dataclass

LEVEL_STEP = 10
MAX_LEVEL = 12
MAX_HAZARDS = 6
ORB_SPEED = 1.3     # rad/s the orb travels around the planet (constant; rel sets the pace)
HIT_PAD = 0.05      # orb half-width in radians used for collisions (forgiving)


@dataclass(frozen=True)
class Difficulty:
    level: int
    rel_min: float       # rad/s range of orb speed relative to a ring
    rel_max: float
    hazard_count: int    # spikes + gaps wanted per ring (fewer if they don't fit)
    hazard_min: float    # angular width range of one hazard
    hazard_max: float
    window: float        # seconds every safe landing window lasts, at least
    reaction: float      # seconds of fuse beyond the longest possible wait
    gap_chance: float    # chance a hazard is a gap instead of a spike

    @property
    def longest_wait(self) -> float:
        """Worst case for the landing spot to sweep past one hazard."""
        return (self.hazard_max + 2 * HIT_PAD) / self.rel_min

    @property
    def fuse(self) -> float:
        """Seconds the orb may stay on a landed ring before it collapses."""
        return self.longest_wait + self.reaction


def level_for(rings_landed: int) -> int:
    return min(max(rings_landed, 0) // LEVEL_STEP, MAX_LEVEL)


def difficulty_for(rings_landed: int) -> Difficulty:
    lv = level_for(rings_landed)
    return Difficulty(
        level=lv,
        rel_min=0.9 + 0.035 * lv,
        rel_max=1.2 + 0.035 * lv,
        hazard_count=min(2 + (lv + 1) // 2, MAX_HAZARDS),
        hazard_min=0.22,
        hazard_max=0.42,
        window=max(0.22, 0.45 - 0.02 * lv),
        reaction=max(0.45, 1.0 - 0.045 * lv),
        gap_chance=0.0 if lv < 2 else min(0.1 * lv, 0.4),
    )
