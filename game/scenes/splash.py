from ..config import CENTER, WIDTH
from ..logic.easing import clamp01, ease_out_back, ease_out_cubic
from ..render import text
from ..render.colors import CYAN, DIM, MAGENTA
from ..render.world_view import draw_planet
from .base import Scene

DURATION = 1.4


class SplashScene(Scene):
    def enter(self, **kwargs) -> None:
        self.t = 0.0

    def tap(self, pos) -> None:
        self.app.go("home")

    def key(self, key: int) -> None:
        self.app.go("home")

    def update(self, dt: float) -> None:
        self.t += dt
        self.app.stars.update(dt)
        if self.t >= DURATION:
            self.app.go("home")

    def draw(self, surf) -> None:
        self.app.draw_backdrop(surf)
        draw_planet(surf, CENTER[0], CENTER[1], self.t)
        k = ease_out_back(clamp01(self.t / 0.7))
        y = 330 - (1 - k) * 90
        text.draw(surf, "ORBIT", 118, CYAN, (WIDTH // 2, y), glow=1.0)
        text.draw(surf, "HOP", 118, MAGENTA, (WIDTH // 2, y + 120), glow=1.0)
        text.draw(surf, "ONE TAP. INFINITE ORBITS.", 26, DIM, (WIDTH // 2, 1060),
                  face=text.BODY, alpha=ease_out_cubic(clamp01((self.t - 0.4) / 0.5)))
