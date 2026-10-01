"""Pre-rendered deep-space backdrop: gradient, soft nebulae and a vignette.

Built once at start-up so each frame costs a single blit.
"""

import random

import pygame

from ..config import HEIGHT, WIDTH
from .colors import mix

TOP = (8, 12, 34)
BOTTOM = (20, 10, 44)


def build_background(seed: int = 3) -> pygame.Surface:
    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        pygame.draw.line(bg, mix(TOP, BOTTOM, y / HEIGHT), (0, y), (WIDTH, y))

    # Nebulae: big soft blobs drawn small, blurred, then scaled up (cheap and smooth).
    rng = random.Random(seed)
    small = pygame.Surface((WIDTH // 8, HEIGHT // 8))
    small.fill((0, 0, 0))
    blobs = ((0, 70, 110), (90, 10, 90), (30, 20, 110), (0, 60, 80), (70, 0, 60))
    for color in blobs:
        x = rng.uniform(0, small.get_width())
        y = rng.uniform(0, small.get_height())
        r = rng.uniform(14, 30)
        pygame.draw.circle(small, color, (int(x), int(y)), int(r))
    small = pygame.transform.gaussian_blur(small, 10)
    nebula = pygame.transform.smoothscale(small, (WIDTH, HEIGHT))
    nebula.fill((150, 150, 150), special_flags=pygame.BLEND_RGB_MULT)
    bg.blit(nebula, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    # Vignette: darken towards the corners.
    vig = pygame.Surface((WIDTH // 8, HEIGHT // 8))
    vig.fill((150, 150, 150))
    pygame.draw.ellipse(vig, (255, 255, 255), vig.get_rect().inflate(-6, -10))
    vig = pygame.transform.gaussian_blur(vig, 8)
    vig = pygame.transform.smoothscale(vig, (WIDTH, HEIGHT))
    bg.blit(vig, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    return bg
