"""App shell: window, input, fixed-timestep loop and scene switching."""

from __future__ import annotations

import asyncio
import math
import sys
import time

import pygame

from .audio import Audio
from .config import HEIGHT, MAX_FRAME, PAUSE_GAP, STEP, WIDTH
from .logic.easing import ease_out_cubic
from .paths import base_dir
from .render import text
from .render.background import build_background
from .render.colors import BG, DIM
from .render.starfield import Starfield
from .render.ui import Overlay, Shake
from .scenes.gameover import GameOverScene
from .scenes.home import HomeScene
from .scenes.play import PlayScene
from .scenes.settings import SettingsScene
from .scenes.skins import SkinsScene
from .scenes.splash import SplashScene
from .storage import Storage

FADE_TIME = 0.28
TAP_DEBOUNCE = 0.06    # ignore duplicate touch+mouse events for one tap
JUMP_KEYS = (pygame.K_SPACE, pygame.K_UP, pygame.K_RETURN)


class App:
    def __init__(self, *, web: bool | None = None, storage: Storage | None = None,
                 window_size=(540, 960)):
        self.web = sys.platform == "emscripten" if web is None else web
        pygame.init()
        pygame.display.set_caption("Orbit Hop")
        if self.web:
            # pygbag scales the canvas to the page; draw straight to it.
            self.window = pygame.display.set_mode((WIDTH, HEIGHT))
            self.screen = self.window
        else:
            icon = base_dir() / "favicon.png"
            if icon.exists():
                pygame.display.set_icon(pygame.image.load(str(icon)))
            self.window = pygame.display.set_mode(window_size, pygame.RESIZABLE)
            self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()

        self.storage = storage or Storage(web=self.web)
        self.save = self.storage.load()
        self.audio = Audio()
        self.shake = Shake()
        self.stars = Starfield()
        self.background = build_background()
        self.apply_settings()

        self.clock = pygame.time.Clock()
        self.fade = Overlay(BG)
        self.fade_t = 1.0
        self.time = 0.0
        self.last_tap = -1.0
        self.running = True
        self.show_fps = False
        self.frame_ms = 16.7

        self.scenes = {
            "splash": SplashScene(self),
            "home": HomeScene(self),
            "play": PlayScene(self),
            "gameover": GameOverScene(self),
            "skins": SkinsScene(self),
            "settings": SettingsScene(self),
        }
        self.scene_name = ""
        self.go("splash")

    # --- scenes & settings ------------------------------------------------
    def go(self, name: str, **kwargs) -> None:
        self.scene_name = name
        self.scene = self.scenes[name]
        self.scene.enter(**kwargs)
        self.fade_t = 0.0

    def draw_backdrop(self, surf) -> None:
        surf.blit(self.background, (0, 0))
        self.stars.draw(surf)

    def persist(self) -> None:
        self.storage.save(self.save)

    def apply_settings(self) -> None:
        self.audio.enabled = self.save.sound
        self.shake.enabled = self.save.shake
        if not self.save.shake:
            self.shake.amount = 0.0

    # --- input ------------------------------------------------------------
    def viewport(self) -> pygame.Rect:
        """Where the logical 720x1280 screen sits inside the window (letterboxed)."""
        ww, wh = self.window.get_size()
        s = min(ww / WIDTH, wh / HEIGHT)
        w, h = int(WIDTH * s), int(HEIGHT * s)
        return pygame.Rect((ww - w) // 2, (wh - h) // 2, w, h)

    def to_logical(self, pos):
        if self.screen is self.window:
            return pos
        vp = self.viewport()
        return ((pos[0] - vp.x) * WIDTH / vp.w, (pos[1] - vp.y) * HEIGHT / vp.h)

    def tap(self, pos) -> None:
        if self.time - self.last_tap < TAP_DEBOUNCE:
            return
        self.last_tap = self.time
        self.audio.unlock()     # browsers allow audio only after a user gesture
        self.scene.tap(pos)

    def handle_event(self, e) -> None:
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if not getattr(e, "touch", False):   # touches arrive as FINGERDOWN too
                self.tap(self.to_logical(e.pos))
        elif e.type == pygame.FINGERDOWN:
            ww, wh = self.window.get_size()
            self.tap(self.to_logical((e.x * ww, e.y * wh)))
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F3:
                self.show_fps = not self.show_fps
                return
            if e.key in JUMP_KEYS:
                self.audio.unlock()
            self.scene.key(e.key)
        elif e.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWHIDDEN, pygame.WINDOWMINIMIZED):
            self.scene.pause()

    # --- loop -------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.time += dt
        self.shake.update(dt)
        self.fade_t = min(1.0, self.fade_t + dt / FADE_TIME)
        self.scene.update(dt)

    def draw(self) -> None:
        self.scene.draw(self.screen)
        self.fade.draw(self.screen, 255 * (1 - ease_out_cubic(self.fade_t)))
        if self.show_fps:
            fps = 1000 / max(self.frame_ms, 0.1)
            text.draw(self.screen, f"{fps:4.0f} fps  {self.frame_ms:4.1f} ms", 22, DIM,
                      topleft=(12, HEIGHT - 34), face=text.BODY)
        if self.screen is not self.window:
            self.window.fill((0, 0, 0))
            vp = self.viewport()
            self.window.blit(pygame.transform.smoothscale(self.screen, vp.size), vp)
        pygame.display.flip()

    def frame(self, frame_dt: float) -> None:
        """Process input, simulate exactly the elapsed time, then draw once.

        The frame's time is split into equal substeps no longer than STEP, so
        physics stays stable while motion matches any refresh rate (60, 90,
        120, 144 Hz) with no judder.
        """
        for e in pygame.event.get():
            self.handle_event(e)
        if frame_dt > PAUSE_GAP:
            # The tab was hidden or the phone locked: don't let the run play on.
            self.scene.pause()
        dt = min(frame_dt, MAX_FRAME)
        steps = max(1, math.ceil(dt / STEP - 1e-6))
        for _ in range(steps):
            self.update(dt / steps)
        self.draw()
        self.frame_ms += (frame_dt * 1000 - self.frame_ms) * 0.05

    async def run(self) -> None:
        last = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            self.frame(now - last)
            last = now
            # pygbag needs this yield every frame or the browser tab freezes.
            await asyncio.sleep(0)
            if not self.web:
                self.clock.tick(60)
        self.persist()
        if not self.web:
            pygame.quit()
