"""Buttons, icons, screen shake and overlays."""

import math
import random

import pygame

from ..config import HEIGHT, WIDTH
from ..logic.easing import clamp01, ease_out_back, ease_out_cubic
from . import text
from .colors import BG, CYAN, LIME, TEXT, mix, scale
from .glow import draw_glow

_button_cache: dict = {}


def panel_sprites(size, color, radius):
    """Glass panel (per-pixel alpha) plus a blurred neon rim for additive blending."""
    key = (size, color, radius)
    if key not in _button_cache:
        w, h = size
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        top, bottom = mix((22, 30, 72), color, 0.16), (12, 16, 44)
        for y in range(h):
            # Vertical gradient clipped to the rounded shape below.
            pygame.draw.line(panel, (*mix(top, bottom, y / h), 235), (0, y), (w, y))
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
        panel.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.rect(panel, (*mix(color, (255, 255, 255), 0.25), 255), (0, 0, w, h),
                         width=3, border_radius=radius)
        pygame.draw.line(panel, (255, 255, 255, 40), (radius, 6), (w - radius, 6), 2)

        pad = 22
        rim = pygame.Surface((w + pad * 2, h + pad * 2))
        rim.fill((0, 0, 0))
        pygame.draw.rect(rim, scale(color, 0.9), (pad, pad, w, h), width=7, border_radius=radius)
        rim = pygame.transform.gaussian_blur(rim, 9)
        _button_cache[key] = (panel, rim, pad)
    return _button_cache[key]


class Button:
    def __init__(self, center, size, label: str, color=CYAN, font_size: int = 44, sub: str = "",
                 delay: float = 0.0):
        self.rect = pygame.Rect(0, 0, *size)
        self.rect.center = center
        self.label = label
        self.color = color
        self.font_size = font_size
        self.sub = sub
        self.delay = delay   # entrance animation offset, seconds after the scene opens
        self.press = 0.0     # 1 right after a tap, eases back to 0

    def hit(self, pos) -> bool:
        if self.rect.collidepoint(pos):
            self.press = 1.0
            return True
        return False

    def update(self, dt: float) -> None:
        self.press = max(0.0, self.press - dt * 5)

    def draw(self, surf: pygame.Surface, scene_time: float = 10.0) -> None:
        intro = clamp01((scene_time - self.delay) / 0.45)
        if intro <= 0:
            return
        radius = min(self.rect.height // 2, 34)
        panel, rim, pad = panel_sprites(self.rect.size, self.color, radius)
        dy = (1 - ease_out_back(intro)) * 70 + self.press * 4
        x, y = self.rect.x, self.rect.y + dy
        surf.blit(rim, (x - pad, y - pad), special_flags=pygame.BLEND_RGB_ADD)
        if self.press > 0:
            draw_glow(surf, self.rect.center, self.rect.width * 0.45, self.color, self.press * 0.5)
        if intro < 1:
            panel.set_alpha(int(255 * ease_out_cubic(intro)))
        surf.blit(panel, (x, y))
        panel.set_alpha(255)
        cx, cy = self.rect.centerx, self.rect.centery + dy
        alpha = ease_out_cubic(intro)
        if self.sub:
            text.draw(surf, self.label, self.font_size, TEXT, (cx, cy - 14), glow=0.5, alpha=alpha)
            text.draw(surf, self.sub, 24, mix(self.color, TEXT, 0.3), (cx, cy + 24),
                      face=text.BODY, alpha=alpha)
        else:
            text.draw(surf, self.label, self.font_size, TEXT, (cx, cy + 2), glow=0.5, alpha=alpha)


def draw_gem(surf: pygame.Surface, center, size: float, color=LIME, spin: float = 0.0,
             glow: float = 0.0) -> None:
    cx, cy = center
    if glow > 0:
        draw_glow(surf, center, size * 3, color, glow)
    w = size * (0.55 + 0.45 * abs(math.cos(spin)))
    pts = [(cx, cy - size), (cx + w, cy), (cx, cy + size), (cx - w, cy)]
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, mix(color, (255, 255, 255), 0.6), [(cx, cy - size), (cx + w * 0.5, cy - size * 0.1),
                                                                 (cx, cy), (cx - w * 0.5, cy - size * 0.1)])
    pygame.draw.aalines(surf, (255, 255, 255), True, pts)


def draw_gem_count(surf: pygame.Surface, pos, count: int, size: int = 34) -> None:
    x, y = pos
    draw_gem(surf, (x + 14, y), 14, glow=0.5)
    text.draw(surf, str(count), size, TEXT, midleft=(x + 38, y), face=text.NUMBER, glow=0.3)


def draw_pill(surf: pygame.Surface, center, label: str, color, size: int = 34) -> None:
    w, h = text.size_of(label, size, text.NUMBER)
    rect = pygame.Rect(0, 0, w + 34, h + 12)
    rect.center = center
    draw_glow(surf, center, rect.width * 0.6, color, 0.35)
    pygame.draw.rect(surf, (14, 20, 50), rect, border_radius=rect.height // 2)
    pygame.draw.rect(surf, color, rect, width=3, border_radius=rect.height // 2)
    text.draw(surf, label, size, color, rect.center, face=text.NUMBER, glow=0.6)


class Shake:
    def __init__(self):
        self.amount = 0.0
        self.enabled = True

    def add(self, amount: float) -> None:
        if self.enabled:
            self.amount = min(40.0, self.amount + amount)

    def update(self, dt: float) -> None:
        self.amount = max(0.0, self.amount - dt * 70)

    def offset(self):
        if self.amount <= 0:
            return 0, 0
        a = self.amount
        return random.uniform(-a, a), random.uniform(-a, a)


class Overlay:
    """Full-screen tint blitted with surface alpha (cheaper than per-pixel alpha)."""

    def __init__(self, color=BG):
        self.surf = pygame.Surface((WIDTH, HEIGHT))
        self.color = color
        self.surf.fill(color)

    def draw(self, target: pygame.Surface, alpha: float, color=None) -> None:
        if alpha <= 0:
            return
        if color is not None and color != self.color:
            self.color = color
            self.surf.fill(color)
        self.surf.set_alpha(int(max(0, min(255, alpha))))
        target.blit(self.surf, (0, 0))
