import math

import pygame

from ..config import WIDTH
from ..logic.daily import daily_key, today_utc
from ..logic.easing import clamp01, ease_out_back, ease_out_cubic
from ..render import text
from ..render.colors import CYAN, DIM, GOLD, LIME, MAGENTA, TEXT
from ..render.particles import Particles
from ..render.ui import Button, draw_gem
from .base import Scene

INPUT_LOCK = 0.3   # ignore taps meant for the crashed run


class GameOverScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.retry = Button((WIDTH // 2, 990), (460, 128), "RETRY", CYAN, 60, delay=0.15)
        self.home = Button((WIDTH // 2, 1132), (300, 88), "HOME", DIM, 36, delay=0.22)
        self.particles = Particles(140)

    def enter(self, stats: dict, daily: bool = False, **kwargs) -> None:
        self.stats = stats
        self.daily = daily
        self.t = 0.0
        save = self.app.save
        self.day = daily_key(today_utc())
        self.result = save.record_run(stats, self.day if daily else None)
        self.app.persist()
        self.particles.clear()
        self.celebrate = (self.result.new_best or self.result.daily_new_best) and stats["score"] > 0
        if self.celebrate:
            self.app.audio.play("best")
            self.app.shake.add(14)
            for color in (GOLD, MAGENTA, CYAN):
                self.particles.burst(WIDTH // 2, 380, color, count=30, speed=700, life=1.4, size=9)

    def tap(self, pos) -> None:
        if self.t < INPUT_LOCK:
            return
        if self.retry.hit(pos):
            self.app.go("play", daily=self.daily)
        elif self.home.hit(pos):
            self.app.audio.play("click")
            self.app.go("home")

    def key(self, key: int) -> None:
        if self.t < INPUT_LOCK:
            return
        if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_UP):
            self.app.go("play", daily=self.daily)
        elif key == pygame.K_ESCAPE:
            self.app.go("home")

    def update(self, dt: float) -> None:
        self.t += dt
        self.app.stars.update(dt)
        self.particles.update(dt)
        self.retry.update(dt)
        self.home.update(dt)

    def draw(self, surf) -> None:
        self.app.draw_backdrop(surf)
        ox, oy = self.app.shake.offset()
        self.particles.draw(surf, ox, oy)
        save, res = self.app.save, self.result

        text.draw(surf, "DAILY RUN" if self.daily else "GAME OVER", 40, DIM, (WIDTH // 2, 190), glow=0.4)
        k = ease_out_back(clamp01(self.t / 0.4))
        size = max(12, int(170 * k) // 4 * 4)   # step sizes so few glyph sizes get cached
        text.draw(surf, str(self.stats["score"]), size, TEXT, (WIDTH // 2 + ox, 370 + oy),
                  face=text.NUMBER, glow=0.8)

        fade = ease_out_cubic(clamp01((self.t - 0.25) / 0.4))
        if self.celebrate:
            pulse = 0.8 + 0.2 * math.sin(self.t * 8)
            label = "NEW BEST!" if res.new_best else "TODAY'S BEST!"
            text.draw(surf, label, 50, GOLD, (WIDTH // 2, 510), glow=pulse, alpha=fade)

        best = save.daily_best_for(self.day) if self.daily else save.best
        text.draw(surf, "TODAY'S BEST" if self.daily else "BEST", 22, DIM, (WIDTH // 2, 570),
                  face=text.BODY, alpha=fade)
        text.draw(surf, str(best), 40, TEXT, (WIDTH // 2, 606), face=text.NUMBER, alpha=fade)

        gems = f"+{res.gems_earned}"
        w = text.size_of(gems, 36, text.NUMBER)[0]
        x0 = WIDTH // 2 - (w + 40) // 2
        if fade > 0.5:
            draw_gem(surf, (x0 + 13, 660), 14, LIME, self.t * 3, glow=0.6)
        text.draw(surf, gems, 36, LIME, midleft=(x0 + 40, 660), face=text.NUMBER, glow=0.5, alpha=fade)

        y = 740
        for m in res.missions:
            text.draw(surf, "MISSION COMPLETE", 20, MAGENTA, (WIDTH // 2, y), glow=0.6, alpha=fade)
            text.draw(surf, f"{m.text}   +{m.reward}", 26, TEXT, (WIDTH // 2, y + 30),
                      face=text.BODY, alpha=fade)
            y += 74

        self.retry.draw(surf, self.t)
        self.home.draw(surf, self.t)
