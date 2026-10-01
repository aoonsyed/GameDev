"""Rings, orb state and collisions. Pure Python: no pygame imports.

The orb circles the inner ring; one tap launches it straight out to the next
ring, which carries rotating hazards (spikes and gaps). Landing on a hazard
ends the run. Landing safely conquers the ring: its hazards retract and a
fuse starts; if the fuse burns out before the next jump the ring collapses.

Angles are radians, counter-clockwise, with 0 pointing right. Hazard and gem
angles are stored in the ring's local frame and rotate with the ring.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .difficulty import HIT_PAD, ORB_SPEED, Difficulty, difficulty_for

TAU = math.tau

INNER_RADIUS = 170.0                  # logical px: the ring being orbited
OUTER_RADIUS = 300.0                  # logical px: the ring to jump to
GEM_RADIUS = (INNER_RADIUS + OUTER_RADIUS) / 2
JUMP_TIME = 0.26                      # seconds between rings
NEAR_MISS_ARC = 0.07                  # landing this close to a hazard is a near miss
GEM_CHANCE = 0.6
GEM_CATCH_PX = 34.0

SPIKE = "spike"
GAP = "gap"
TIMEOUT = "timeout"


def arc_distance(a: float, b: float) -> float:
    """Shortest angular distance between two angles."""
    d = (a - b) % TAU
    return min(d, TAU - d)


@dataclass
class Hazard:
    start: float          # local angle where the hazard begins
    width: float          # angular width (counter-clockwise from start)
    kind: str = SPIKE

    def contains(self, local: float, pad: float = 0.0) -> bool:
        return (local - self.start + pad) % TAU <= self.width + 2 * pad

    def edge_distance(self, local: float) -> float:
        if self.contains(local):
            return 0.0
        return min(arc_distance(local, self.start),
                   arc_distance(local, self.start + self.width))


@dataclass
class Ring:
    hazards: list = field(default_factory=list)
    spin: float = 0.0                 # rad/s
    rotation: float = 0.0
    gem: float | None = None          # local angle of a gem on the approach to this ring
    index: int = 0

    def update(self, dt: float) -> None:
        self.rotation = (self.rotation + self.spin * dt) % TAU

    def local(self, world_angle: float) -> float:
        return (world_angle - self.rotation) % TAU

    def to_world(self, local: float) -> float:
        return (local + self.rotation) % TAU

    def hazard_at(self, world_angle: float) -> Hazard | None:
        local = self.local(world_angle)
        for h in self.hazards:
            if h.contains(local, HIT_PAD):
                return h
        return None

    def clearance(self, world_angle: float) -> float:
        """Angular room between the orb's edge and the nearest hazard."""
        if not self.hazards:
            return math.inf
        local = self.local(world_angle)
        return min(h.edge_distance(local) for h in self.hazards) - HIT_PAD


def min_gap(diff: Difficulty, rel: float) -> float:
    """Smallest safe arc: the landing spot stays clear for `diff.window` seconds."""
    return 2 * HIT_PAD + rel * diff.window


def generate_ring(rng: random.Random, diff: Difficulty, index: int = 0) -> Ring:
    """Build a ring whose every gap is at least min_gap() wide."""
    rel = rng.uniform(diff.rel_min, diff.rel_max)
    gap = min_gap(diff, rel)
    widths = [rng.uniform(diff.hazard_min, diff.hazard_max) for _ in range(diff.hazard_count)]
    while len(widths) > 1 and sum(widths) + gap * len(widths) > TAU:
        widths.pop()
    n = len(widths)

    # Share the leftover arc randomly between the gaps.
    spare = TAU - sum(widths) - gap * n
    cuts = sorted(rng.uniform(0, spare) for _ in range(n - 1))
    extras = [b - a for a, b in zip([0.0] + cuts, cuts + [spare])]

    hazards = []
    angle = rng.uniform(0, TAU)
    for w, extra in zip(widths, extras):
        kind = GAP if rng.random() < diff.gap_chance else SPIKE
        hazards.append(Hazard(angle % TAU, w, kind))
        angle += w + gap + extra

    gem = None
    if rng.random() < GEM_CHANCE:
        # Centre of a random gap: gems also hint at a safe landing spot.
        i = rng.randrange(n)
        h, nxt = hazards[i], hazards[(i + 1) % n]
        gap_start = h.start + h.width
        gap_len = (nxt.start - gap_start) % TAU
        gem = (gap_start + gap_len / 2) % TAU

    # The landing spot always sweeps forward across the ring at `rel`.
    return Ring(hazards, ORB_SPEED - rel, rotation=0.0, gem=gem, index=index)


class World:
    """One run. Call jump() on tap and update(dt) every fixed step.

    update() returns events: ("gem",), ("land", near_miss), ("level", n),
    ("crash", kind) where kind is SPIKE, GAP or TIMEOUT.
    """

    def __init__(self, seed: int):
        self.seed = seed
        self.rings_landed = 0
        self.difficulty = difficulty_for(0)
        self.orb_angle = math.pi / 2
        self.state = "orbit"            # "orbit" | "jump" | "dead"
        self.jump_t = 0.0               # 0..1 progress of the current jump
        self.fuse: float | None = None  # seconds left on this ring; None = no limit
        self.fuse_total = 1.0
        self.crash_kind: str | None = None
        self._crash_distance = INNER_RADIUS
        self._gem_checked = False
        self.current = Ring(index=0)    # the start ring is safe: tap when ready
        self.next = self._make_ring(1)

    def _make_ring(self, index: int) -> Ring:
        # Each ring has its own RNG, so ring N is identical for every player
        # with the same seed, however they played rings 0..N-1.
        rng = random.Random(self.seed * 1_000_003 + index)
        return generate_ring(rng, difficulty_for(index), index)

    @property
    def fuse_fraction(self) -> float:
        """1 = fuse just lit, 0 = burnt out. Always 1 on the start ring."""
        if self.fuse is None:
            return 1.0
        return max(0.0, self.fuse / self.fuse_total)

    @property
    def orb_distance(self) -> float:
        """Orb distance from the planet centre, in logical px."""
        if self.state == "jump":
            return INNER_RADIUS + (OUTER_RADIUS - INNER_RADIUS) * min(self.jump_t, 1.0)
        if self.state == "dead":
            return self._crash_distance
        return INNER_RADIUS

    def jump(self) -> bool:
        if self.state != "orbit":
            return False
        self.state = "jump"
        self.jump_t = 0.0
        self._gem_checked = False
        return True

    def update(self, dt: float) -> list:
        events: list = []
        if self.state == "dead":
            return events
        self.current.update(dt)
        self.next.update(dt)

        if self.state == "orbit":
            self.orb_angle = (self.orb_angle + ORB_SPEED * dt) % TAU
            if self.fuse is not None:
                self.fuse -= dt
                if self.fuse <= 0:
                    self._crash(TIMEOUT, events)
            return events

        self.jump_t += dt / JUMP_TIME
        if (not self._gem_checked and self.next.gem is not None
                and self.orb_distance >= GEM_RADIUS):
            self._gem_checked = True
            gem_world = self.next.to_world(self.next.gem)
            if arc_distance(gem_world, self.orb_angle) * GEM_RADIUS <= GEM_CATCH_PX:
                self.next.gem = None
                events.append(("gem",))
        if self.jump_t >= 1.0:
            self._land(events)
        return events

    def _land(self, events: list) -> None:
        hit = self.next.hazard_at(self.orb_angle)
        if hit:
            self.jump_t = 1.0
            self._crash(hit.kind, events)
            return
        near = self.next.clearance(self.orb_angle) < NEAR_MISS_ARC
        old_level = self.difficulty.level
        self.rings_landed += 1
        self.current = self.next
        self.current.gem = None
        self.next = self._make_ring(self.rings_landed + 1)
        self.difficulty = difficulty_for(self.rings_landed)
        # Budget for the *next* ring, the one the player now has to time.
        self.fuse = self.fuse_total = difficulty_for(self.rings_landed + 1).fuse
        self.state = "orbit"
        self.jump_t = 0.0
        events.append(("land", near))
        if self.difficulty.level > old_level:
            events.append(("level", self.difficulty.level))

    def _crash(self, kind: str, events: list) -> None:
        self._crash_distance = self.orb_distance
        self.state = "dead"
        self.crash_kind = kind
        events.append(("crash", kind))
