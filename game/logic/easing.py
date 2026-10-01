"""Easing helpers for smooth UI and camera motion."""

import math


def clamp01(t: float) -> float:
    return 0.0 if t < 0 else 1.0 if t > 1 else t


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_out_cubic(t: float) -> float:
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def ease_in_out_sine(t: float) -> float:
    t = clamp01(t)
    return -(math.cos(math.pi * t) - 1) / 2


def ease_out_back(t: float, s: float = 1.70158) -> float:
    t = clamp01(t) - 1
    return t * t * ((s + 1) * t + s) + 1
