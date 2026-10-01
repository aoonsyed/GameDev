"""Headless smoke test: boot the real app and click through every screen."""

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
pygame = pytest.importorskip("pygame")

from game.app import App  # noqa: E402
from game.config import STEP  # noqa: E402
from game.storage import Storage  # noqa: E402


@pytest.fixture
def app(tmp_path):
    # pygame stays initialised between tests: quitting would invalidate cached fonts.
    return App(web=False, storage=Storage(tmp_path / "save.json", web=False))


def frames(app, n):
    for _ in range(n):
        app.frame(STEP)


def click(app, pos):
    app.last_tap = -1.0  # bypass the touch/mouse debounce between scripted clicks
    app.tap(pos)
    frames(app, 2)


def test_full_flow(app):
    frames(app, 100)                       # splash -> home
    assert app.scene_name == "home"

    click(app, app.scenes["home"].play.rect.center)
    assert app.scene_name == "play"
    play = app.scenes["play"]
    # Tap repeatedly until the run ends: crashing is guaranteed eventually.
    for _ in range(4000):
        if app.scene_name != "play":
            break
        if play.world.state == "orbit":
            click(app, (360, 1000))
        frames(app, 3)
    assert app.scene_name == "gameover"
    assert app.save.runs == 1

    over = app.scenes["gameover"]
    frames(app, 30)
    click(app, over.retry.rect.center)
    assert app.scene_name == "play"

    click(app, play.pause_rect.center)
    assert play.paused
    click(app, play.home.rect.center)
    assert app.scene_name == "home"


def test_daily_skins_settings(app):
    app.go("home")
    home = app.scenes["home"]
    click(app, home.daily.rect.center)
    assert app.scene_name == "play" and app.scenes["play"].daily
    frames(app, 30)

    app.go("skins")
    app.save.gems = 100
    skins_scene = app.scenes["skins"]
    rect, skin = skins_scene.cards[1]
    click(app, rect.center)
    assert app.save.skin == skin.id
    rect, _ = skins_scene.cards[-1]
    click(app, rect.center)                # can't afford: stays equipped
    assert app.save.skin == skin.id
    frames(app, 30)

    app.go("settings")
    settings = app.scenes["settings"]
    click(app, settings.sound.rect.center)
    assert app.save.sound is False and app.audio.enabled is False
    click(app, settings.shake.rect.center)
    assert app.save.shake is False
    assert app.storage.load().sound is False   # persisted


def test_focus_loss_and_long_frames_pause(app):
    app.go("play")
    play = app.scenes["play"]
    pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    frames(app, 1)
    assert play.paused
    play.paused = False
    app.frame(2.0)                         # tab was hidden for 2 s
    assert play.paused


def test_keyboard_jump_and_letterbox_mapping(app):
    app.go("play")
    play = app.scenes["play"]
    frames(app, 5)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    frames(app, 1)
    assert play.world.state in ("jump", "orbit", "dead") and play.score.jumps == 1
    vp = app.viewport()
    assert app.to_logical(vp.topleft) == (0, 0)
