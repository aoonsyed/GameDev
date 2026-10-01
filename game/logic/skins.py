"""Cosmetic orb skins, unlocked with gems."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SKIN = "pulse"


@dataclass(frozen=True)
class Skin:
    id: str
    name: str
    cost: int
    core: tuple
    glow: tuple
    animated: bool = False      # colour cycles over time


SKINS = (
    Skin("pulse", "Pulse", 0, (200, 255, 255), (0, 200, 255)),
    Skin("acid", "Acid", 40, (230, 255, 200), (140, 255, 40)),
    Skin("nova", "Nova", 60, (255, 210, 245), (255, 40, 200)),
    Skin("solar", "Solar", 90, (255, 245, 200), (255, 190, 30)),
    Skin("comet", "Comet", 120, (255, 255, 255), (150, 170, 255)),
    Skin("ember", "Ember", 160, (255, 225, 200), (255, 110, 30)),
    Skin("void", "Void", 200, (225, 205, 255), (140, 60, 255)),
    Skin("flare", "Flare", 260, (255, 210, 210), (255, 40, 70)),
    Skin("tide", "Tide", 330, (205, 255, 240), (0, 230, 170)),
    Skin("prism", "Prism", 500, (255, 255, 255), (255, 255, 255), animated=True),
)

SKIN_IDS = tuple(s.id for s in SKINS)
_BY_ID = {s.id: s for s in SKINS}


def get_skin(skin_id: str) -> Skin:
    return _BY_ID.get(skin_id, _BY_ID[DEFAULT_SKIN])


def select(save, skin_id: str) -> str:
    """Equip an owned skin, or buy and equip one.

    Returns "equipped", "bought" or "locked". `save` is a SaveData (anything
    with gems, owned and skin attributes).
    """
    if skin_id not in _BY_ID:
        return "locked"
    if skin_id in save.owned:
        save.skin = skin_id
        return "equipped"
    cost = _BY_ID[skin_id].cost
    if save.gems < cost:
        return "locked"
    save.gems -= cost
    save.owned.append(skin_id)
    save.skin = skin_id
    return "bought"
