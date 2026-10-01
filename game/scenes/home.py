import math

import pygame

from ..config import WIDTH
from ..logic.daily import daily_key, today_utc
from ..logic.missions import active_missions
from ..logic.skins import get_skin
from ..render import text
from ..render.colors import CYAN, DIM, GOLD, LIME, MAGENTA, TEXT, skin_colors
from ..render.glow import draw_glow
from ..render.ui import Button, draw_gem_count
from ..render.world_view import draw_orb, draw_planet, ring_circle
from .base import Scene

ORBIT_R = 130


class HomeScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.play = Button((WIDTH // 2, 830), (460, 124), "PLAY", CYAN, 60, delay=0.05)
        self.daily = Button((WIDTH // 2, 968), (460, 104), "DAILY", GOLD, 40, delay=0.12)
        self.skins = Button((WIDTH // 2 - 119, 1088), (222, 86), "SKINS", MAGENTA, 32, delay=0.19)
        self.settings = Button((WIDTH // 2 + 119, 1088), (222, 86), "OPTIONS", DIM, 32, delay=0.24)
        self.buttons = (self.play, self.daily, self.skins, self.settings)
        self.t = 0.0

    def enter(self, **kwargs) -> None:
        self.t = 0.0
        best = self.app.save.daily_best_for(daily_key(today_utc()))
        self.daily.sub = f"Today's best: {best}" if best else "Same level for everyone today"

    def tap(self, pos) -> None:
        if self.play.hit(pos):
            self.app.audio.play("click")
            self.app.go("play")
        elif self.daily.hit(pos):
            self.app.audio.play("click")
            self.app.go("play", daily=True)
        elif self.skins.hit(pos):
            self.app.audio.play("click")
            self.app.go("skins")
        elif self.settings.hit(pos):
            self.app.audio.play("click")
            self.app.go("settings")

    def key(self, key: int) -> None:
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            self.app.go("play")
        elif key == pygame.K_ESCAPE and not self.app.web:
            self.app.running = False

    def update(self, dt: float) -> None:
        self.t += dt
        self.app.stars.update(dt)
        for b in self.buttons:
            b.update(dt)

    def draw(self, surf) -> None:
        self.app.draw_backdrop(surf)
        save = self.app.save

        bob = math.sin(self.t * 1.6) * 6
        text.draw(surf, "ORBIT", 112, CYAN, (WIDTH // 2, 160 + bob), glow=1.0)
        text.draw(surf, "HOP", 112, MAGENTA, (WIDTH // 2, 272 + bob), glow=1.0)

        # Demo orbit with the equipped skin.
        cx, cy = WIDTH // 2, 520
        draw_planet(surf, cx, cy, self.t)
        ring_circle(surf, (0, 170, 210), cx, cy, ORBIT_R, 1.0, 3)
        a = self.t * 1.6
        core, glow = skin_colors(get_skin(save.skin), self.t)
        for i in range(10, 0, -1):
            b = a - i * 0.045
            draw_glow(surf, (cx + ORBIT_R * math.cos(b), cy - ORBIT_R * math.sin(b)),
                      8 + 16 * (1 - i / 10), glow, 0.5 * (1 - i / 10))
        draw_orb(surf, (cx + ORBIT_R * math.cos(a), cy - ORBIT_R * math.sin(a)), core, glow)

        text.draw(surf, "BEST", 24, DIM, (WIDTH // 2, 694), face=text.BODY)
        text.draw(surf, str(save.best), 50, TEXT, (WIDTH // 2, 730), face=text.NUMBER, glow=0.5)
        draw_gem_count(surf, (30, 48), save.gems)

        for b in self.buttons:
            b.draw(surf, self.t)

        missions = active_missions(save.missions_done)
        if missions:
            text.draw(surf, "MISSIONS", 20, LIME, (WIDTH // 2, 1166), glow=0.5)
            for i, m in enumerate(missions):
                text.draw(surf, f"{m.text}   +{m.reward}", 24, (150, 165, 210),
                          (WIDTH // 2, 1198 + i * 28), face=text.BODY)
