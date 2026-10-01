import math
import random

import pygame

from ..config import CENTER, WIDTH
from ..logic.daily import daily_seed, today_utc
from ..logic.scoring import RunScore
from ..logic.skins import get_skin
from ..logic.world import TIMEOUT, World
from ..render import text
from ..render.colors import BG, CYAN, DIM, GOLD, LIME, MAGENTA, TEXT, WHITE, skin_colors
from ..render.particles import Particles
from ..render.ui import Button, Overlay, draw_gem_count, draw_pill
from ..render.world_view import WorldView
from .base import Scene

SLOWMO_TIME = 0.3      # real seconds of slow motion after a near miss
SLOWMO_SCALE = 0.35
DEATH_DELAY = 0.55     # crash -> game over screen


class PlayScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.particles = Particles()
        self.overlay = Overlay()
        self.pause_rect = pygame.Rect(WIDTH - 104, 22, 80, 80)
        self.resume = Button((WIDTH // 2, 700), (420, 116), "RESUME", CYAN, 48)
        self.home = Button((WIDTH // 2, 850), (300, 88), "HOME", DIM, 36)

    def enter(self, daily: bool = False, **kwargs) -> None:
        self.daily = daily
        seed = daily_seed(today_utc()) if daily else random.randrange(1, 2**31)
        self.world = World(seed)
        self.score = RunScore()
        self.view = WorldView()
        self.particles.clear()
        self.floaters = []     # [text, x, y, age, color]
        self.paused = False
        self.pause_t = 0.0
        self.score_pop = 0.0
        self.slowmo = 0.0
        self.flash = 0.0
        self.dead_time = 0.0
        self.hint = True
        self.t = 0.0

    # --- input -----------------------------------------------------------
    def tap(self, pos) -> None:
        if self.paused:
            if self.resume.hit(pos):
                self.paused = False
            elif self.home.hit(pos):
                self.app.go("home")
            return
        if self.pause_rect.collidepoint(pos) and self.world.state != "dead":
            self.pause()
            return
        self._jump()

    def key(self, key: int) -> None:
        if key in (pygame.K_SPACE, pygame.K_UP, pygame.K_RETURN):
            if self.paused:
                self.paused = False
            else:
                self._jump()
        elif key in (pygame.K_ESCAPE, pygame.K_p):
            if self.paused:
                self.paused = False
            else:
                self.pause()

    def pause(self) -> None:
        if self.world.state != "dead" and not self.paused:
            self.paused = True
            self.pause_t = 0.0

    def _jump(self) -> None:
        if self.world.jump():
            self.score.on_jump()
            self.hint = False
            self.app.audio.play("jump")

    # --- simulation ------------------------------------------------------
    def update(self, dt: float) -> None:
        self.t += dt
        self.app.stars.update(dt)
        self.resume.update(dt)
        self.home.update(dt)
        self.score_pop = max(0.0, self.score_pop - dt * 4)
        if self.paused:
            self.pause_t += dt
            return

        scale = SLOWMO_SCALE if self.slowmo > 0 else 1.0
        self.slowmo = max(0.0, self.slowmo - dt)
        self.flash = max(0.0, self.flash - dt * 4)
        wdt = dt * scale

        old_ring = self.world.current
        cx, cy = CENTER
        for ev in self.world.update(wdt):
            kind = ev[0]
            if kind == "gem":
                self.score.on_gem()
                self.app.audio.play("gem")
                x, y = self.view.orb_pos(self.world, cx, cy)
                self.particles.burst(x, y, LIME, count=14, speed=260, life=0.5)
                self._float(f"x{self.score.multiplier}", x, y - 40, LIME)
            elif kind == "land":
                near = ev[1]
                points = self.score.on_land(near)
                self.score_pop = 1.0
                self.view.on_land(old_ring)
                self.app.stars.kick()
                self.app.shake.add(5)
                self.app.audio.play_land(self.score.combo)
                x, y = self.view.orb_pos(self.world, cx, cy)
                self.particles.burst(x, y, CYAN, count=10, speed=200, life=0.4, size=5)
                if points > 1:
                    self._float(f"+{points}", x, y - 50, GOLD)
                if near:
                    self.slowmo = SLOWMO_TIME
                    if self.app.save.shake:
                        self.flash = 1.0
                    self.app.audio.play("near")
                    self._float("NEAR MISS!", WIDTH // 2, 360, MAGENTA)
            elif kind == "level":
                self._float("SPEED UP", WIDTH // 2, 320, CYAN)
            elif kind == "crash":
                if ev[1] == TIMEOUT:
                    self._float("TOO SLOW!", WIDTH // 2, 360, MAGENTA)
                self.app.shake.add(26)
                self.app.audio.play("crash")
                x, y = self.view.orb_pos(self.world, cx, cy)
                self.particles.burst(x, y, MAGENTA, count=40, speed=520, life=0.9, size=9)
                self.particles.burst(x, y, WHITE, count=12, speed=300, life=0.5, size=5)

        self.view.update(wdt, self.world)
        self.particles.update(wdt)
        if self.world.state == "dead":
            self.dead_time += dt
            if self.dead_time >= DEATH_DELAY:
                self.app.go("gameover", stats=self.score.stats(), daily=self.daily)

        for f in self.floaters:
            f[3] += dt
            f[2] -= 60 * dt
        self.floaters = [f for f in self.floaters if f[3] < 0.9]

    def _float(self, label, x, y, color) -> None:
        self.floaters.append([label, x, y, 0.0, color])

    # --- drawing ---------------------------------------------------------
    def draw(self, surf) -> None:
        self.app.draw_backdrop(surf)
        ox, oy = self.app.shake.offset()
        cx, cy = CENTER[0] + ox, CENTER[1] + oy
        colors = skin_colors(get_skin(self.app.save.skin), self.t)
        self.view.draw(surf, self.world, cx, cy, colors, show_orb=self.world.state != "dead")
        self.particles.draw(surf, ox, oy)

        # HUD
        size = 104 + int(self.score_pop * 16) // 4 * 4
        text.draw(surf, str(self.score.score), size, TEXT, (WIDTH // 2, 160), face=text.NUMBER, glow=0.7)
        if self.score.multiplier > 1:
            draw_pill(surf, (WIDTH // 2, 252), f"x{self.score.multiplier}", LIME)
        draw_gem_count(surf, (30, 62), self.score.gems)
        if self.daily:
            text.draw(surf, "DAILY", 20, GOLD, topleft=(32, 96), glow=0.5)
        if self.world.state != "dead":
            r = self.pause_rect
            pygame.draw.aacircle(surf, DIM, r.center, 32, 3)
            pygame.draw.rect(surf, TEXT, (r.centerx - 11, r.centery - 13, 7, 26), border_radius=2)
            pygame.draw.rect(surf, TEXT, (r.centerx + 4, r.centery - 13, 7, 26), border_radius=2)

        if self.hint:
            k = 0.55 + 0.45 * math.sin(self.t * 4)
            text.draw(surf, "TAP TO JUMP", 36, CYAN, (WIDTH // 2, 1110), glow=0.6, alpha=k)
            text.draw(surf, "Land between the spikes. Jump before the fuse burns out.", 22, DIM,
                      (WIDTH // 2, 1160), face=text.BODY)

        for label, x, y, age, color in self.floaters:
            k = 1 - age / 0.9
            text.draw(surf, label, 40, color, (x, y), face=text.NUMBER if label[0] in "+x" else text.DISPLAY,
                      glow=0.8, alpha=k)

        if self.flash > 0:
            self.overlay.draw(surf, 70 * self.flash, WHITE)

        if self.paused:
            self.overlay.draw(surf, min(200, self.pause_t * 900), BG)
            text.draw(surf, "PAUSED", 72, CYAN, (WIDTH // 2, 520), glow=1.0)
            self.resume.draw(surf, self.pause_t)
            self.home.draw(surf, self.pause_t)
