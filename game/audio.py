"""Sound effects, synthesised in code at first tap.

Browsers block audio until the player interacts, so nothing is created or
played until unlock() runs from the first tap. Generating the effects in code
keeps the download tiny; swap in .ogg files from jsfxr later if wanted.
"""

from __future__ import annotations

import io
import math
import random
import struct
from array import array

import pygame

RATE = 22050
LAND_STEPS = 8   # landing pitch rises with the combo


def _synth(f0, f1, dur, shape="square", vol=0.3, noise=0.0, seed=1) -> io.BytesIO:
    rnd = random.Random(seed)
    n = int(RATE * dur)
    samples = array("h")
    phase = 0.0
    attack = RATE * 0.004
    for i in range(n):
        t = i / n
        phase += (f0 + (f1 - f0) * t) / RATE
        p = phase % 1.0
        if shape == "square":
            s = 1.0 if p < 0.5 else -1.0
        elif shape == "triangle":
            s = 4 * abs(p - 0.5) - 1
        else:
            s = math.sin(math.tau * p)
        if noise:
            s = s * (1 - noise) + rnd.uniform(-1, 1) * noise
        env = min(1.0, i / attack) * (1 - t) ** 2
        samples.append(int(s * env * vol * 32767))
    return io.BytesIO(_wav_header(len(samples) * 2) + samples.tobytes())


def _wav_header(data_bytes: int) -> bytes:
    # Mono 16-bit PCM. Written by hand: the `wave` module is missing from
    # pygbag's browser Python, and importing it makes pygbag fetch a bogus
    # PyPI package of the same name.
    return struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + data_bytes, b"WAVE", b"fmt ", 16,
                       1, 1, RATE, RATE * 2, 2, 16, b"data", data_bytes)


def _specs() -> dict:
    specs = {
        "jump": dict(f0=520, f1=900, dur=0.08, vol=0.18),
        "gem": dict(f0=1300, f1=1900, dur=0.12, shape="sine", vol=0.35),
        "near": dict(f0=300, f1=1400, dur=0.28, shape="sine", vol=0.3, noise=0.45),
        "crash": dict(f0=240, f1=40, dur=0.45, vol=0.3, noise=0.6),
        "click": dict(f0=900, f1=700, dur=0.04, vol=0.15),
        "deny": dict(f0=200, f1=140, dur=0.14, vol=0.2),
        "best": dict(f0=520, f1=1040, dur=0.5, shape="triangle", vol=0.35),
    }
    for k in range(LAND_STEPS):
        base = 440 * 2 ** (2 * k / 12)
        specs[f"land{k}"] = dict(f0=base, f1=base * 1.5, dur=0.11, shape="triangle", vol=0.35)
    return specs


class Audio:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.ready = False
        self.failed = False
        self.sounds: dict = {}

    def unlock(self) -> None:
        if self.ready or self.failed:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(buffer=512)
            for name, spec in _specs().items():
                self.sounds[name] = pygame.mixer.Sound(file=_synth(**spec))
            self.ready = True
        except Exception:
            # No audio device (or the browser refused): play silently.
            self.failed = True

    def play(self, name: str) -> None:
        if self.enabled and self.ready:
            sound = self.sounds.get(name)
            if sound:
                sound.play()

    def play_land(self, combo: int) -> None:
        self.play(f"land{min(combo, LAND_STEPS - 1)}")
