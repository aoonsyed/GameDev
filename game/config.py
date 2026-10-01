"""Shared constants. No pygame imports."""

WIDTH = 720          # logical resolution, portrait
HEIGHT = 1280
STEP = 1 / 60        # fixed simulation timestep (seconds)
MAX_FRAME = 0.25     # longest frame we simulate; longer gaps are clamped
PAUSE_GAP = 0.5      # a frame gap this long means the tab was hidden / phone locked
CENTER = (WIDTH // 2, 700)  # planet position on screen
