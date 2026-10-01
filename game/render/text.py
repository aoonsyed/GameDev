"""Fonts and cached text rendering with blurred neon glow."""

import pygame

from ..paths import asset_path

DISPLAY = "display"     # Orbitron (OFL): titles and buttons
BODY = "body"           # Exo 2 (OFL): small readable text
NUMBER = "number"       # Exo 2 bold: scores and counts (Orbitron's zero is slashed)

_fonts: dict = {}
_cache: dict = {}
_MAX_CACHE = 400


def font(size: int, face: str = DISPLAY) -> pygame.font.Font:
    key = (face, size)
    f = _fonts.get(key)
    if f is None:
        path = asset_path("fonts", f"{BODY if face == NUMBER else face}.ttf")
        f = pygame.font.Font(str(path) if path.exists() else None, size)
        if face == NUMBER:
            f.bold = True
        _fonts[key] = f
    return f


def _glow_for(img_text: str, size: int, color, face: str, strength: float):
    """Blurred, colour-tinted copy of the text for additive blending."""
    base = font(size, face).render(img_text, True, color)
    pad = max(8, size // 4)
    w, h = base.get_size()
    glow = pygame.Surface((w + pad * 2, h + pad * 2))
    glow.fill((0, 0, 0))
    glow.blit(base, (pad, pad))
    glow = pygame.transform.gaussian_blur(glow, max(3, size // 9))
    k = int(255 * min(1.0, strength))
    if k < 255:
        glow.fill((k, k, k), special_flags=pygame.BLEND_RGB_MULT)
    return glow, pad


def _get(text: str, size: int, color, face: str, glow: float):
    key = (text, size, color, face, glow)
    entry = _cache.get(key)
    if entry is None:
        if len(_cache) > _MAX_CACHE:
            _cache.clear()
        img = font(size, face).render(text, True, color)
        entry = (img, _glow_for(text, size, color, face, glow) if glow > 0 else None)
        _cache[key] = entry
    return entry


def size_of(text: str, size: int, face: str = DISPLAY):
    return font(size, face).size(text)


def draw(surf: pygame.Surface, text: str, size: int, color, center=None, *, topleft=None,
         midleft=None, midright=None, face: str = DISPLAY, glow: float = 0.0,
         alpha: float = 1.0) -> pygame.Rect:
    """Draw text. `glow` 0..1 adds a soft neon halo; `alpha` fades it out."""
    if alpha <= 0:
        return pygame.Rect(0, 0, 0, 0)
    # Quantise so fading text reuses a handful of cached glows.
    g = round(glow * alpha * 4) / 4
    img, glow_entry = _get(text, size, color, face, g)
    rect = img.get_rect()
    if center is not None:
        rect.center = (int(center[0]), int(center[1]))
    elif topleft is not None:
        rect.topleft = topleft
    elif midleft is not None:
        rect.midleft = midleft
    elif midright is not None:
        rect.midright = midright
    if glow_entry is not None:
        glow_img, pad = glow_entry
        surf.blit(glow_img, (rect.x - pad, rect.y - pad), special_flags=pygame.BLEND_RGB_ADD)
    if alpha < 1:
        img.set_alpha(int(255 * alpha))
        surf.blit(img, rect)
        img.set_alpha(255)
    else:
        surf.blit(img, rect)
    return rect
