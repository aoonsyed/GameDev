"""Neon-on-deep-space palette."""

BG = (11, 16, 38)            # #0B1026
BG_LIGHT = (20, 28, 64)
CYAN = (0, 235, 255)
MAGENTA = (255, 43, 214)
LIME = (160, 255, 60)
GOLD = (255, 200, 40)
WHITE = (240, 248, 255)
TEXT = (215, 230, 255)
DIM = (90, 110, 170)
PANEL = (16, 24, 56)


def scale(color, k: float):
    k = max(0.0, min(1.0, k))
    return (int(color[0] * k), int(color[1] * k), int(color[2] * k))


def mix(a, b, t: float):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def hue(h: float, s: float = 0.85, v: float = 1.0):
    """HSV -> RGB (colorsys isn't in pygbag's browser Python)."""
    h = (h % 1.0) * 6
    i = int(h)
    f = h - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))[i % 6]
    return (int(r * 255), int(g * 255), int(b * 255))


def skin_colors(skin, time: float):
    """(core, glow) for a skin, cycling hue for animated skins."""
    if skin.animated:
        return hue(time * 0.25, 0.35), hue(time * 0.25)
    return skin.core, skin.glow
