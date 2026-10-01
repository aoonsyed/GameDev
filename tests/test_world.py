import math
import random

import pytest

from game.logic.difficulty import ORB_SPEED, difficulty_for
from game.logic.world import (
    TIMEOUT, GAP, GEM_RADIUS, HIT_PAD, INNER_RADIUS, JUMP_TIME, OUTER_RADIUS, SPIKE, TAU,
    Hazard, Ring, World, arc_distance, generate_ring, min_gap,
)

STEP = 1 / 60


def gaps_between(ring):
    hs = sorted(ring.hazards, key=lambda h: h.start)
    return [(hs[(i + 1) % len(hs)].start - (h.start + h.width)) % TAU for i, h in enumerate(hs)]


def run_jump(world):
    """Jump and step until the jump resolves. Returns all events."""
    assert world.jump()
    events = []
    for _ in range(int(JUMP_TIME / STEP) + 5):
        events += world.update(STEP)
        if world.state != "jump":
            break
    return events


def test_arc_distance_wraps():
    assert arc_distance(0.1, TAU - 0.1) == pytest.approx(0.2)
    assert arc_distance(1.0, 1.0) == 0


def test_hazard_contains_across_zero():
    h = Hazard(TAU - 0.2, 0.4)
    assert h.contains(0.1)
    assert h.contains(TAU - 0.1)
    assert not h.contains(0.3)
    assert h.contains(0.25, pad=0.06)


def test_hazard_edge_distance():
    h = Hazard(1.0, 0.5)
    assert h.edge_distance(1.2) == 0
    assert h.edge_distance(0.8) == pytest.approx(0.2)
    assert h.edge_distance(1.7) == pytest.approx(0.2)


@pytest.mark.parametrize("rings_landed", [0, 10, 40, 80, 500])
def test_generated_rings_are_always_passable(rings_landed):
    diff = difficulty_for(rings_landed)
    for seed in range(200):
        ring = generate_ring(random.Random(seed), diff)
        rel = ORB_SPEED - ring.spin
        assert diff.rel_min <= rel <= diff.rel_max
        assert 1 <= len(ring.hazards) <= diff.hazard_count
        assert min(gaps_between(ring)) >= min_gap(diff, rel) - 1e-9
        assert sum(h.width for h in ring.hazards) < TAU
        if ring.gem is not None:
            assert all(not h.contains(ring.gem, HIT_PAD) for h in ring.hazards)


def test_gaps_only_appear_at_higher_levels():
    early = [generate_ring(random.Random(s), difficulty_for(0)) for s in range(50)]
    assert all(h.kind == SPIKE for r in early for h in r.hazards)
    late = [generate_ring(random.Random(s), difficulty_for(100)) for s in range(50)]
    assert any(h.kind == GAP for r in late for h in r.hazards)


def test_same_seed_same_rings():
    a, b = World(1234), World(1234)
    assert a.next.hazards == b.next.hazards
    assert a._make_ring(57).hazards == b._make_ring(57).hazards
    assert World(1235).next.hazards != a.next.hazards


def test_start_ring_is_safe():
    w = World(1)
    for _ in range(600):
        assert w.update(STEP) == []
    assert w.state == "orbit"


def test_jump_moves_orb_outward_and_lands():
    w = World(1)
    w.next = Ring([], spin=0.0, index=1)
    assert w.orb_distance == INNER_RADIUS
    w.jump()
    assert not w.jump()          # no double jump mid-air
    w.update(JUMP_TIME / 2)
    assert INNER_RADIUS < w.orb_distance < OUTER_RADIUS
    events = run_jump_rest(w)
    assert ("land", False) in events
    assert w.rings_landed == 1 and w.state == "orbit"
    assert w.current.index == 1 and w.next.index == 2


def run_jump_rest(w):
    events = []
    for _ in range(60):
        events += w.update(STEP)
        if w.state != "jump":
            break
    return events


def test_landing_on_spike_crashes():
    w = World(1)
    w.orb_angle = 1.0
    w.next = Ring([Hazard(0.8, 0.4, SPIKE)], spin=0.0, index=1)
    events = run_jump(w)
    assert ("crash", SPIKE) in events
    assert w.state == "dead" and w.crash_kind == SPIKE
    assert w.orb_distance == pytest.approx(OUTER_RADIUS)
    assert w.update(STEP) == []        # dead worlds stay put
    assert not w.jump()


def test_landing_into_gap_crashes():
    w = World(1)
    w.orb_angle = 3.0
    w.next = Ring([Hazard(2.9, 0.3, GAP)], spin=0.0, index=1)
    assert ("crash", GAP) in run_jump(w)


def test_near_miss_when_landing_close_to_hazard():
    w = World(1)
    w.orb_angle = 2.0
    # Hazard edge sits just outside the hitbox.
    w.next = Ring([Hazard(2.0 + HIT_PAD + 0.03, 0.3)], spin=0.0, index=1)
    assert ("land", True) in run_jump(w)


def test_fuse_burns_out_on_landed_ring():
    w = World(1)
    w.next = Ring([], spin=0.0, index=1)
    run_jump(w)
    assert w.fuse == pytest.approx(difficulty_for(2).fuse)
    assert w.fuse_fraction == pytest.approx(1.0)
    events = []
    for _ in range(int(w.fuse / STEP) + 2):
        events += w.update(STEP)
    assert ("crash", TIMEOUT) in events
    assert w.fuse_fraction == 0.0
    assert w.orb_distance == INNER_RADIUS


def test_start_ring_has_no_fuse_and_landed_rings_are_safe_to_orbit():
    w = World(1)
    assert w.fuse is None and w.fuse_fraction == 1.0
    w.next = Ring([Hazard(0.0, 3.0)], spin=0.0, index=1)
    w.orb_angle = 4.0
    run_jump(w)
    assert w.state == "orbit"
    # The conquered ring's hazards no longer hurt while orbiting.
    for _ in range(int(w.fuse / STEP) - 2):
        w.update(STEP)
    assert w.state == "orbit"


def test_gem_collected_when_jumping_through_it():
    w = World(1)
    w.orb_angle = 1.0
    w.next = Ring([], spin=0.0, gem=1.0, index=1)
    events = run_jump(w)
    assert ("gem",) in events
    assert events.index(("gem",)) < events.index(("land", False))


def test_gem_missed_when_far_away():
    w = World(1)
    w.orb_angle = 1.0
    w.next = Ring([], spin=0.0, gem=1.0 + 60 / GEM_RADIUS, index=1)
    assert ("gem",) not in run_jump(w)


def test_ring_rotation_moves_hazards():
    ring = Ring([Hazard(0.0, 0.2)], spin=1.0)
    assert ring.hazard_at(0.1)
    ring.update(1.0)
    assert not ring.hazard_at(0.1)
    assert ring.hazard_at(1.1)
    assert ring.to_world(ring.local(2.5)) == pytest.approx(2.5)


def test_level_event_every_ten_rings():
    w = World(1)
    events = []
    for _ in range(10):
        w.next = Ring([], spin=0.0, index=w.rings_landed + 1)
        events += run_jump(w)
    assert ("level", 1) in events
    assert w.difficulty.level == 1


def test_clearance_without_hazards_is_infinite():
    assert Ring().clearance(1.0) == math.inf


REACT_FRAMES = 12     # a human needs ~0.2 s after landing before tapping again
SLACK_FRAMES = 2      # and can't time a tap better than +-2 frames


def plan_jump(w, rng):
    """A frame to jump on that a human could hit, picked at random among valid ones.

    Returns None if no such frame exists before the fuse burns out: the player
    was trapped by the level, which must never happen.
    """
    horizon = int(w.fuse / STEP) - 1 if w.fuse is not None else 60 * 20
    flight = math.ceil(JUMP_TIME / STEP - 1e-9)
    nxt = w.next

    def safe(k):
        a = w.orb_angle + ORB_SPEED * k * STEP
        local = (a - nxt.rotation - nxt.spin * (k + flight) * STEP) % TAU
        return all(not h.contains(local, HIT_PAD + 0.01) for h in nxt.hazards)

    valid = [k for k in range(REACT_FRAMES, horizon - SLACK_FRAMES)
             if all(safe(k + d) for d in range(-SLACK_FRAMES, SLACK_FRAMES + 1))]
    return rng.choice(valid) if valid else None


@pytest.mark.parametrize("seed", range(40))
def test_level_never_traps_a_careful_player(seed):
    rng = random.Random(seed)
    w = World(seed)
    while w.rings_landed < 150:
        k = plan_jump(w, rng)
        assert k is not None, f"trapped on ring {w.rings_landed} (level {w.difficulty.level})"
        for _ in range(k):
            w.update(STEP)
        assert w.state == "orbit"
        events = run_jump(w)
        assert w.state == "orbit", events
