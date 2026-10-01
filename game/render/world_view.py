"""Draws a World: planet, rings with spikes and gaps, gems and the orb.

When the orb lands, the view eases the landed ring in to the inner radius
while the next ring slides in from outside. Geometry is drawn as filled
polygons with anti-aliased edges, over cheap low-intensity glow bands.
"""

import math

import pygame

from ..config import WIDTH
from ..logic.easing import ease_out_cubic, lerp
from ..logic.world import GAP, GEM_RADIUS, INNER_RADIUS, OUTER_RADIUS, SPIKE, TAU, Ring, World
from .colors import CYAN, DIM, LIME, MAGENTA, mix, scale
from .glow import draw_glow
from .ui import draw_gem

ZOOM_TIME = 0.3
RING_STEP = OUTER_RADIUS - INNER_RADIUS
PLANET_RADIUS = 76
SPIKE_OUT = 24
SPIKE_IN = 14
TRAIL = 16
GLOW_BANDS = ((22, 0.10), (11, 0.22))   # (width, intensity) under every ring core
GLOW_H = 1000                           # height of the additive glow layer around the planet

_planet = None


def _pt(cx, cy, r, a):
    return (cx + r * math.cos(a), cy - r * math.sin(a))


def _arc(cx, cy, r, a0, a1):
    n = max(2, int(abs(a1 - a0) * r / 9) + 1)
    step = (a1 - a0) / (n - 1)
    return [_pt(cx, cy, r, a0 + step * i) for i in range(n)]


def thick_arc(surf, color, cx, cy, r, a0, a1, width, aa=False):
    """Annulus sector from a0 to a1 (radians, a1 > a0) as one filled polygon."""
    outer = _arc(cx, cy, r + width / 2, a0, a1)
    inner = _arc(cx, cy, r - width / 2, a0, a1)
    pygame.draw.polygon(surf, color, outer + inner[::-1])
    if aa:
        pygame.draw.aalines(surf, color, False, outer)
        pygame.draw.aalines(surf, color, False, inner)


def ring_circle(surf, color, cx, cy, r, fade=1.0, core_width=4, glow=None):
    """`glow` = (layer, gx, gy): an additive layer and the centre in its coordinates."""
    if glow:
        layer, gx, gy = glow
        for width, k in GLOW_BANDS:
            pygame.draw.circle(layer, scale(color, k * fade), (gx, gy), int(r + width / 2), width)
    pygame.draw.aacircle(surf, scale(color, fade), (cx, cy), r + core_width / 2, core_width)


def draw_ring(surf, cx, cy, r, ring: Ring, color, fade: float = 1.0, retract: float = 0.0,
              body: bool = True, glow=None):
    """Draw a ring. `retract` 0..1 sinks its spikes and closes its gaps (a conquered ring)."""
    if r <= 4 or fade <= 0:
        return
    gaps = [] if retract >= 0.5 else sorted(
        (h for h in ring.hazards if h.kind == GAP), key=lambda h: h.start)
    if body and gaps:
        spans = []
        for i, g in enumerate(gaps):
            nxt = gaps[(i + 1) % len(gaps)]
            a0 = ring.to_world(g.start + g.width)
            spans.append((a0, a0 + (nxt.start - (g.start + g.width)) % TAU))
        if glow:
            layer, gx, gy = glow
            for width, k in GLOW_BANDS:
                for a0, a1 in spans:
                    thick_arc(layer, scale(color, k * fade), gx, gy, r, a0, a1, width)
        for a0, a1 in spans:
            thick_arc(surf, scale(color, fade), cx, cy, r, a0, a1, 4, aa=True)
        # Glowing caps make the gap edges readable.
        for g in gaps:
            for a in (g.start, g.start + g.width):
                p = _pt(cx, cy, r, ring.to_world(a))
                draw_glow(surf, p, 22, MAGENTA, 0.7 * fade)
                pygame.draw.aacircle(surf, scale(MAGENTA, fade), p, 6)
    elif body:
        ring_circle(surf, color, cx, cy, r, fade, glow=glow)

    if retract >= 1:
        return
    k = fade * (1 - retract)
    fill, edge = scale(MAGENTA, k), scale(mix(MAGENTA, (255, 255, 255), 0.45), k)
    out_len, in_len = SPIKE_OUT * (1 - retract), SPIKE_IN * (1 - retract)
    for h in ring.hazards:
        if h.kind != SPIKE:
            continue
        teeth = max(1, round(h.width * r / 24))
        tw = h.width / teeth
        mid = ring.to_world(h.start + h.width / 2)
        draw_glow(surf, _pt(cx, cy, r, mid), min(80, h.width * r * 0.7 + 24), MAGENTA, 0.5 * k)
        for j in range(teeth):
            a0 = ring.to_world(h.start + j * tw)
            a1, am = a0 + tw, a0 + tw / 2
            b0, b1 = _pt(cx, cy, r, a0), _pt(cx, cy, r, a1)
            out = (b0, _pt(cx, cy, r + out_len, am), b1)
            inn = (b0, _pt(cx, cy, r - in_len, am), b1)
            pygame.draw.polygon(surf, fill, out)
            pygame.draw.polygon(surf, fill, inn)
            pygame.draw.aalines(surf, edge, True, out)
            pygame.draw.aalines(surf, edge, True, inn)


def draw_fuse(surf, cx, cy, r, end_angle: float, fraction: float, time: float, glow=None):
    """The landed ring's fuse: a bright arc trailing the orb that burns away."""
    ring_circle(surf, (50, 80, 130), cx, cy, r, 1.0, 2)
    if fraction <= 0:
        return
    color = CYAN
    if fraction < 0.35:
        color = mix(MAGENTA, (255, 255, 255), 0.25 + 0.25 * math.sin(time * 28))
    a0 = end_angle - fraction * TAU
    if glow:
        layer, gx, gy = glow
        thick_arc(layer, scale(color, 0.28), gx, gy, r, a0, end_angle, 20)
    thick_arc(surf, color, cx, cy, r, a0, end_angle, 5, aa=True)
    spark = _pt(cx, cy, r, a0)
    draw_glow(surf, spark, 26 + 4 * math.sin(time * 40), mix(color, (255, 220, 120), 0.5), 0.9)


def _planet_sprite():
    """Shaded sphere with a lit top-left and a cyan rim, rendered once."""
    global _planet
    if _planet is None:
        r = PLANET_RADIUS
        s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        c = r + 2
        dark, light = (14, 18, 46), (46, 60, 120)
        steps = 40
        for i in range(steps):
            t = i / steps
            rr = r * (1 - t)
            off = r * 0.35 * t
            pygame.draw.circle(s, (*mix(dark, light, t ** 1.4), 255), (c - off, c - off), max(1, rr))
        # Clip the offset circles back to the sphere outline.
        mask = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        pygame.draw.aacircle(mask, (255, 255, 255, 255), (c, c), r)
        s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.aacircle(s, (*scale(CYAN, 0.55), 255), (c, c), r, 2)
        pygame.draw.aacircle(s, (90, 120, 200, 70), (c, c), r * 0.62, 2)
        _planet = s
    return _planet


def draw_planet(surf, cx, cy, time: float, color=CYAN):
    pulse = 0.45 + 0.1 * math.sin(time * 2)
    draw_glow(surf, (cx, cy), PLANET_RADIUS * 2.2, scale(color, 0.45), pulse)
    sprite = _planet_sprite()
    surf.blit(sprite, sprite.get_rect(center=(int(cx), int(cy))))


def draw_orb(surf, pos, core, glow, radius: float = 18):
    draw_glow(surf, pos, radius * 4, glow, 0.55)
    draw_glow(surf, pos, radius * 2.2, glow, 0.9)
    pygame.draw.aacircle(surf, glow, pos, radius)
    pygame.draw.aacircle(surf, core, pos, radius * 0.72)
    pygame.draw.aacircle(surf, (255, 255, 255), (pos[0] - radius * 0.28, pos[1] - radius * 0.28),
                         max(2, radius * 0.24))


class WorldView:
    def __init__(self):
        self.zoom = 1.0
        self.old_ring = None
        self.time = 0.0
        self.trail = []          # recent orb positions relative to the planet
        self.layer = pygame.Surface((WIDTH, GLOW_H))

    def on_land(self, old_ring: Ring) -> None:
        self.zoom = 0.0
        self.old_ring = old_ring

    def update(self, dt: float, world: World) -> None:
        self.time += dt
        self.zoom = min(1.0, self.zoom + dt / ZOOM_TIME)
        if world.state != "dead":
            x, y = self.orb_pos(world, 0, 0)
            self.trail.append((x, y))
            if len(self.trail) > TRAIL:
                del self.trail[0]
        elif self.trail:
            del self.trail[0]

    def radii(self):
        e = ease_out_cubic(self.zoom)
        return lerp(OUTER_RADIUS, INNER_RADIUS, e), lerp(OUTER_RADIUS + RING_STEP, OUTER_RADIUS, e)

    def to_screen_radius(self, d: float) -> float:
        """Map a logical distance (INNER..OUTER) onto the animated radii."""
        cur, nxt = self.radii()
        return cur + (d - INNER_RADIUS) / RING_STEP * (nxt - cur)

    def orb_pos(self, world: World, cx: float, cy: float):
        return _pt(cx, cy, self.to_screen_radius(world.orb_distance), world.orb_angle)

    def draw(self, surf, world: World, cx: float, cy: float, orb_colors, show_orb=True):
        cur, nxt = self.radii()
        e = ease_out_cubic(self.zoom)
        draw_planet(surf, cx, cy, self.time)
        # Soft bands go on a black layer that is *added* to the scene, so they
        # can only brighten the backdrop (drawn directly they leave dark halos).
        top = int(cy) - GLOW_H // 2
        self.layer.fill((0, 0, 0))
        glow = (self.layer, cx, cy - top)
        if self.old_ring is not None and e < 1:
            draw_ring(surf, cx, cy, lerp(INNER_RADIUS, PLANET_RADIUS + 6, e), self.old_ring, CYAN,
                      1 - e, retract=1.0, glow=glow)
        draw_ring(surf, cx, cy, nxt, world.next, mix(CYAN, (90, 140, 255), 0.35), e, glow=glow)
        if world.fuse is None:
            ring_circle(surf, CYAN, cx, cy, cur, glow=glow)
        else:
            # Conquered ring: hazards sink away while the fuse burns.
            draw_ring(surf, cx, cy, cur, world.current, CYAN, retract=e, body=False)
            draw_fuse(surf, cx, cy, cur, world.orb_angle, world.fuse_fraction, self.time, glow)
        surf.blit(self.layer, (0, top), special_flags=pygame.BLEND_RGB_ADD)

        if world.next.gem is not None:
            a = world.next.to_world(world.next.gem)
            pos = _pt(cx, cy, self.to_screen_radius(GEM_RADIUS), a)
            draw_gem(surf, pos, 13 + math.sin(self.time * 6), LIME, self.time * 3, glow=0.8 * e)

        core, glow = orb_colors
        n = len(self.trail)
        for i, (x, y) in enumerate(self.trail):
            k = (i + 1) / (n + 1)
            draw_glow(surf, (cx + x, cy + y), 8 + 22 * k, glow, 0.55 * k)
        if show_orb:
            if world.state == "dead":
                core, glow = scale(core, 0.5), scale(DIM, 0.8)
            draw_orb(surf, self.orb_pos(world, cx, cy), core, glow)
