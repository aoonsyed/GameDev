"""Cached radial glow sprites, blitted with additive blending."""

import pygame

_cache: dict = {}
_MAX_CACHE = 600


def glow_surface(radius: int, color) -> pygame.Surface:
    radius = max(2, int(radius))
    key = (radius, color)
    surf = _cache.get(key)
    if surf is None:
        if len(_cache) > _MAX_CACHE:
            _cache.clear()
        surf = pygame.Surface((radius * 2, radius * 2))
        surf.fill((0, 0, 0))
        steps = max(4, min(16, radius // 2))
        for i in range(steps):
            r = radius * (1 - i / steps)
            k = ((i + 1) / steps) ** 2.2
            c = (int(color[0] * k), int(color[1] * k), int(color[2] * k))
            pygame.draw.circle(surf, c, (radius, radius), max(1, int(r)))
        _cache[key] = surf
    return surf


def draw_glow(target: pygame.Surface, pos, radius, color, strength: float = 1.0) -> None:
    # Quantise radius and strength so animated glows reuse a few cached sprites.
    strength = round(min(1.0, strength) * 8) / 8
    if strength <= 0:
        return
    if strength < 1:
        color = (int(color[0] * strength), int(color[1] * strength), int(color[2] * strength))
    radius = max(2, int(radius) // 4 * 4)
    surf = glow_surface(radius, color)
    target.blit(surf, (pos[0] - radius, pos[1] - radius), special_flags=pygame.BLEND_RGB_ADD)
