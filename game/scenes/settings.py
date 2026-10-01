import pygame

from .. import VERSION
from ..config import WIDTH
from ..render import text
from ..render.colors import CYAN, DIM, LIME, MAGENTA
from ..render.ui import Button
from .base import Scene


class SettingsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.sound = Button((WIDTH // 2, 430), (500, 110), "", CYAN, 34, delay=0.05)
        self.shake = Button((WIDTH // 2, 580), (500, 110), "", CYAN, 34, delay=0.12)
        self.back = Button((WIDTH // 2, 1120), (300, 88), "BACK", DIM, 36, delay=0.2)
        self.t = 0.0

    def enter(self, **kwargs) -> None:
        self.t = 0.0
        self._labels()

    def _labels(self) -> None:
        save = self.app.save
        self.sound.label = "SOUND"
        self.sound.sub = "On" if save.sound else "Off"
        self.sound.color = LIME if save.sound else DIM
        self.shake.label = "SHAKE & FLASH"
        self.shake.sub = "On" if save.shake else "Off (reduced motion)"
        self.shake.color = LIME if save.shake else DIM

    def tap(self, pos) -> None:
        save = self.app.save
        if self.sound.hit(pos):
            save.sound = not save.sound
            self.app.apply_settings()
            self.app.audio.play("click")
        elif self.shake.hit(pos):
            save.shake = not save.shake
            self.app.apply_settings()
            self.app.audio.play("click")
        elif self.back.hit(pos):
            self.app.audio.play("click")
            self.app.go("home")
            return
        else:
            return
        self.app.persist()
        self._labels()

    def key(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.app.go("home")

    def update(self, dt: float) -> None:
        self.t += dt
        self.app.stars.update(dt)
        for b in (self.sound, self.shake, self.back):
            b.update(dt)

    def draw(self, surf) -> None:
        self.app.draw_backdrop(surf)
        text.draw(surf, "OPTIONS", 64, MAGENTA, (WIDTH // 2, 200), glow=1.0)
        for b in (self.sound, self.shake, self.back):
            b.draw(surf, self.t)
        text.draw(surf, f"Orbit Hop v{VERSION}", 22, DIM, (WIDTH // 2, 1240), face=text.BODY)
