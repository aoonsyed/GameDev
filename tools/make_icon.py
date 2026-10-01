"""Draw favicon.png (used by pygbag, itch.io and the desktop window) in code.

    python tools/make_icon.py
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from game.render.colors import BG, CYAN, MAGENTA  # noqa: E402
from game.render.glow import draw_glow  # noqa: E402
from game.render.world_view import draw_orb  # noqa: E402

SIZE = 256


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    s = pygame.Surface((SIZE, SIZE))
    s.fill(BG)
    c = SIZE // 2
    draw_glow(s, (c, c), 110, (0, 90, 120))
    pygame.draw.circle(s, CYAN, (c, c), 92, 8)
    pygame.draw.circle(s, (20, 28, 64), (c, c), 44)
    pygame.draw.circle(s, MAGENTA, (c, c), 44, 5)
    draw_orb(s, (c + 65, c - 65), (200, 255, 255), CYAN, 24)
    pygame.image.save(s, str(ROOT / "favicon.png"))
    print("wrote favicon.png")


if __name__ == "__main__":
    main()
