from datetime import date

import pytest

from game.logic import missions, skins
from game.logic.daily import daily_key, daily_seed, today_utc
from game.logic.difficulty import LEVEL_STEP, MAX_HAZARDS, difficulty_for, level_for
from game.logic.easing import clamp01, ease_in_out_sine, ease_out_back, ease_out_cubic, lerp
from game.logic.scoring import MAX_MULTIPLIER, RunScore
from game.logic.world import World


# --- difficulty --------------------------------------------------------------
def test_level_rises_every_ten_rings():
    assert level_for(0) == 0
    assert level_for(LEVEL_STEP - 1) == 0
    assert level_for(LEVEL_STEP) == 1
    assert level_for(-5) == 0


def test_difficulty_increases_then_caps():
    prev = difficulty_for(0)
    for rings in range(LEVEL_STEP, 300, LEVEL_STEP):
        d = difficulty_for(rings)
        assert d.rel_min >= prev.rel_min and d.rel_max >= prev.rel_max
        assert d.hazard_count >= prev.hazard_count
        assert d.reaction <= prev.reaction
        prev = d
    assert difficulty_for(10_000) == difficulty_for(1_000)
    assert difficulty_for(10_000).hazard_count <= MAX_HAZARDS


def test_orb_always_moves_relative_to_rings():
    # Otherwise the orb could sit still relative to a ring and never need to jump.
    for rings in range(0, 200, LEVEL_STEP):
        d = difficulty_for(rings)
        assert 0.5 < d.rel_min <= d.rel_max
        assert d.reaction >= 0.35


# --- scoring -----------------------------------------------------------------
def test_landing_without_gems_scores_one():
    s = RunScore()
    s.on_jump()
    assert s.on_land() == 1
    assert s.score == 1 and s.multiplier == 1


def test_gems_build_combo_and_multiplier():
    s = RunScore()
    for expected in (2, 3, 4):
        s.on_jump()
        s.on_gem()
        assert s.on_land() == expected
    assert s.score == 9
    assert s.gems == 3
    assert s.best_multiplier == 4


def test_jump_without_gem_resets_combo():
    s = RunScore()
    s.on_jump(); s.on_gem(); s.on_land()
    s.on_jump()
    assert s.on_land() == 1
    assert s.combo == 0
    assert s.best_multiplier == 2


def test_multiplier_caps():
    s = RunScore()
    for _ in range(20):
        s.on_jump(); s.on_gem(); s.on_land()
    assert s.multiplier == MAX_MULTIPLIER


def test_near_misses_counted():
    s = RunScore()
    s.on_jump(); s.on_land(near_miss=True)
    s.on_jump(); s.on_land()
    assert s.stats()["near_misses"] == 1
    assert set(s.stats()) == {"score", "gems", "best_multiplier", "jumps", "near_misses"}


# --- daily -------------------------------------------------------------------
def test_daily_seed_is_stable_and_varies_by_day():
    d = date(2026, 10, 1)
    assert daily_seed(d) == daily_seed(date(2026, 10, 1))
    seeds = {daily_seed(date(2026, 10, day)) for day in range(1, 31)}
    assert len(seeds) == 30
    assert 0 <= daily_seed(d) < 2**32


def test_daily_level_identical_for_everyone():
    seed = daily_seed(date(2026, 10, 1))
    a, b = World(seed), World(seed)
    for i in range(1, 30):
        assert a._make_ring(i) == b._make_ring(i)


def test_daily_key_format():
    assert daily_key(date(2026, 1, 5)) == "2026-01-05"
    assert isinstance(today_utc(), date)


# --- missions ----------------------------------------------------------------
def test_three_active_missions_in_order():
    active = missions.active_missions([])
    assert [m.id for m in active] == [m.id for m in missions.MISSIONS[:3]]
    done = [missions.MISSIONS[0].id]
    assert missions.active_missions(done)[0] == missions.MISSIONS[1]


def test_completed_only_counts_active_missions():
    stats = {"score": 1000, "gems": 0, "near_misses": 0, "best_multiplier": 1}
    done = missions.completed_by(stats, [])
    assert [m.id for m in done] == ["score_10"]   # score_50/150 are not active yet


def test_mission_ids_unique():
    ids = [m.id for m in missions.MISSIONS]
    assert len(ids) == len(set(ids))


# --- skins -------------------------------------------------------------------
class FakeSave:
    def __init__(self, gems):
        self.gems = gems
        self.owned = [skins.DEFAULT_SKIN]
        self.skin = skins.DEFAULT_SKIN


def test_buy_and_equip_skin():
    save = FakeSave(100)
    assert skins.select(save, "acid") == "bought"
    assert save.gems == 60 and "acid" in save.owned and save.skin == "acid"
    assert skins.select(save, "pulse") == "equipped"
    assert save.gems == 60 and save.skin == "pulse"


def test_cannot_buy_without_gems():
    save = FakeSave(10)
    assert skins.select(save, "prism") == "locked"
    assert save.gems == 10 and save.skin == skins.DEFAULT_SKIN
    assert skins.select(save, "nope") == "locked"


def test_skin_catalogue():
    assert 8 <= len(skins.SKINS) <= 12
    assert skins.get_skin("missing").id == skins.DEFAULT_SKIN
    assert skins.get_skin(skins.DEFAULT_SKIN).cost == 0


# --- easing ------------------------------------------------------------------
@pytest.mark.parametrize("fn", [ease_out_cubic, ease_in_out_sine, ease_out_back])
def test_easing_endpoints(fn):
    assert fn(0) == pytest.approx(0, abs=1e-9)
    assert fn(1) == pytest.approx(1)
    assert fn(-1) == fn(0) and fn(2) == fn(1)


def test_lerp_and_clamp():
    assert lerp(10, 20, 0.5) == 15
    assert clamp01(-1) == 0 and clamp01(3) == 1 and clamp01(0.3) == 0.3
