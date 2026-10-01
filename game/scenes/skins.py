import pygame

from ..config import WIDTH
from ..logic import skins
from ..logic.easing import clamp01, ease_out_cubic
from ..render import text
from ..render.colors import CYAN, DIM, LIME, MAGENTA, TEXT, mix, skin_colors
from ..render.ui import Button, panel_sprites, draw_gem, draw_gem_count
from ..render.world_view import draw_orb
from .base import Scene

CARD_W, CARD_H = 312, 160
COLS_X = (WIDTH // 2 - 166, WIDTH // 2 + 166)
TOP = 260
ROW_STEP = 176


class SkinsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.back = Button((WIDTH // 2, 1180), (300, 88), "BACK", DIM, 36, delay=0.2)
        self.cards = []
        for i, skin in enumerate(skins.SKINS):
            rect = pygame.Rect(0, 0, CARD_W, CARD_H)
            rect.center = (COLS_X[i % 2], TOP + (i // 2) * ROW_STEP)
            self.cards.append((rect, skin))
        self.t = 0.0
        self.denied = None   # (skin_id, time) for a little shake on "can't afford"

    def enter(self, **kwargs) -> None:
        self.t = 0.0
        self.denied = None

    def tap(self, pos) -> None:
        if self.back.hit(pos):
            self.app.audio.play("click")
            self.app.go("home")
            return
        for rect, skin in self.cards:
            if rect.collidepoint(pos):
                outcome = skins.select(self.app.save, skin.id)
                if outcome == "locked":
                    self.denied = (skin.id, self.t)
                    self.app.audio.play("deny")
                else:
                    self.app.audio.play("best" if outcome == "bought" else "click")
                    self.app.persist()
                return

    def key(self, key: int) -> None:
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.app.go("home")

    def update(self, dt: float) -> None:
        self.t += dt
        self.app.stars.update(dt)
        self.back.update(dt)

    def draw(self, surf) -> None:
        self.app.draw_backdrop(surf)
        save = self.app.save
        text.draw(surf, "SKINS", 64, MAGENTA, (WIDTH // 2, 110), glow=1.0)
        draw_gem_count(surf, (30, 48), save.gems)

        for i, (rect, skin) in enumerate(self.cards):
            intro = ease_out_cubic(clamp01((self.t - i * 0.03) / 0.35))
            if intro <= 0:
                continue
            r = rect.move(0, int((1 - intro) * 50))
            if self.denied and self.denied[0] == skin.id and self.t - self.denied[1] < 0.3:
                r = r.move(int(8 * ((self.t * 60) % 2 - 0.5) * 2), 0)
            owned = skin.id in save.owned
            equipped = skin.id == save.skin
            border = LIME if equipped else CYAN if owned else (70, 85, 140)
            panel, rim, pad = panel_sprites(r.size, border, 26)
            if equipped or owned:
                surf.blit(rim, (r.x - pad, r.y - pad), special_flags=pygame.BLEND_RGB_ADD)
            panel.set_alpha(int(255 * intro))
            surf.blit(panel, r)
            panel.set_alpha(255)

            core, glow = skin_colors(skin, self.t)
            draw_orb(surf, (r.left + 72, r.centery), core, glow, 26)
            text.draw(surf, skin.name.upper(), 28, TEXT, midleft=(r.left + 126, r.centery - 22),
                      glow=0.3, alpha=intro)
            if equipped:
                text.draw(surf, "EQUIPPED", 20, LIME, midleft=(r.left + 126, r.centery + 22),
                          glow=0.5, alpha=intro)
            elif owned:
                text.draw(surf, "TAP TO EQUIP", 20, CYAN, midleft=(r.left + 126, r.centery + 22),
                          alpha=intro)
            else:
                afford = save.gems >= skin.cost
                color = LIME if afford else mix(LIME, (60, 70, 100), 0.65)
                draw_gem(surf, (r.left + 136, r.centery + 22), 10, color)
                text.draw(surf, str(skin.cost), 28, TEXT if afford else DIM,
                          midleft=(r.left + 154, r.centery + 22), face=text.NUMBER, alpha=intro)

        self.back.draw(surf, self.t)
