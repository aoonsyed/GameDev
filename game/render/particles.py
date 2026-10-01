"""Pooled particles: a fixed ring buffer so the browser never allocates mid-run."""

import math
import random

import pygame

from .glow import draw_glow


class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color", "active")

    def __init__(self):
        self.active = False


class Particles:
    def __init__(self, capacity: int = 220):
        self.pool = [_Particle() for _ in range(capacity)]
        self._next = 0

    def spawn(self, x, y, vx, vy, life, size, color) -> None:
        p = self.pool[self._next]
        self._next = (self._next + 1) % len(self.pool)
        p.x, p.y, p.vx, p.vy = x, y, vx, vy
        p.life = p.max_life = life
        p.size, p.color, p.active = size, color, True

    def burst(self, x, y, color, count=18, speed=320, life=0.6, size=7) -> None:
        for _ in range(count):
            a = random.uniform(0, math.tau)
            v = speed * random.uniform(0.3, 1.0)
            self.spawn(x, y, math.cos(a) * v, math.sin(a) * v,
                       life * random.uniform(0.6, 1.0), size * random.uniform(0.6, 1.2), color)

    def update(self, dt: float) -> None:
        drag = 0.92 ** (dt * 60)
        for p in self.pool:
            if p.active:
                p.life -= dt
                if p.life <= 0:
                    p.active = False
                    continue
                p.vx *= drag
                p.vy *= drag
                p.x += p.vx * dt
                p.y += p.vy * dt

    def clear(self) -> None:
        for p in self.pool:
            p.active = False

    def draw(self, surf: pygame.Surface, ox: float = 0, oy: float = 0) -> None:
        for p in self.pool:
            if p.active:
                k = p.life / p.max_life
                draw_glow(surf, (p.x + ox, p.y + oy), p.size * (1 + k) * 1.6, p.color, k)
