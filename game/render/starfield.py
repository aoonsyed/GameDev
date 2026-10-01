"""Three-layer parallax starfield drifting down the screen."""

import math
import random

import pygame

from ..config import HEIGHT, WIDTH


class Starfield:
    LAYERS = ((45, 10.0, 1, 0.45), (26, 22.0, 1.5, 0.7), (12, 42.0, 2, 1.0))  # count, speed, size, brightness

    def __init__(self, seed: int = 7):
        rng = random.Random(seed)
        self.stars = []
        for count, speed, size, bright in self.LAYERS:
            for _ in range(count):
                self.stars.append([rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT),
                                   speed, size, bright, rng.uniform(0, math.tau)])
        self.boost = 0.0
        self.time = 0.0

    def kick(self, amount: float = 6.0) -> None:
        self.boost = max(self.boost, amount)

    def update(self, dt: float) -> None:
        self.time += dt
        mult = 1.0 + self.boost
        self.boost = max(0.0, self.boost - dt * 12)
        for s in self.stars:
            s[1] += s[2] * mult * dt
            if s[1] > HEIGHT:
                s[1] -= HEIGHT
                s[0] = random.uniform(0, WIDTH)

    def draw(self, surf: pygame.Surface) -> None:
        t = self.time * 2
        for x, y, _, size, bright, phase in self.stars:
            k = bright * (0.7 + 0.3 * math.sin(t + phase))
            c = int(235 * k)
            color = (c, c, min(255, c + 20))
            if size == 1:
                surf.set_at((int(x), int(y)), color)
            else:
                pygame.draw.aacircle(surf, color, (x, y), size)
