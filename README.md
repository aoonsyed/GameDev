# Orbit Hop

**One tap. Infinite orbits.** A one-thumb neon arcade game in Python
(pygame-ce), playable in any phone or desktop browser via pygbag.

A glowing orb circles a planet. Tap to launch it to the next ring — land
between the spikes and gaps. Each ring you land on lights a fuse, so jump again
before it burns out. Catch gems mid-jump to build a score multiplier.

## Run it

```bash
pip install -r requirements-dev.txt
python main.py                      # desktop (space / click / tap to jump)
pip install pygbag
pygbag .                            # browser test at http://localhost:8000
pygbag --build --archive .          # build/web.zip for itch.io
pytest --cov                        # tests + logic coverage
```

## Layout

```
main.py                 async entry point (pygbag needs the await each frame)
game/logic/             pure Python, no pygame — fully unit-tested
  world.py              rings, orb, jumps, collisions, fuse
  difficulty.py         speed / hazard curves (level up every 10 rings)
  scoring.py            score, gems, combo multiplier
  daily.py              date-seeded daily challenge (UTC)
  missions.py, skins.py, progress.py (save data)
game/render/            code-drawn visuals: glow, particles, starfield, rings
game/scenes/            splash, home, play, game over, skins, settings
game/audio.py           sound effects synthesised at the first tap
game/storage.py         localStorage on the web, ~/.orbit_hop/save.json on desktop
tests/                  pytest (logic + a headless smoke test of every screen)
tools/make_icon.py      regenerates favicon.png
```

## Fairness guarantee

Hazards rotate, so a careless generator can create rings with no safe jump.
Gaps are sized from the orb's speed relative to each ring, and a landed ring's
fuse always outlasts the longest possible wait for a safe landing plus a
reaction budget. `tests/test_world.py::test_level_never_traps_a_careful_player`
proves it with a bot that waits ≥0.2 s after landing and has only ±2 frames of
timing precision, across 40 seeds × 150 rings.

## CI/CD

| Workflow | Trigger | What it does |
|---|---|---|
| `test.yml` | every push / PR | pytest; logic coverage must stay ≥ 80% |
| `deploy-web.yml` | tag `v*` | pygbag build → GitHub Pages + itch.io `html5` channel |
| `build-desktop.yml` | tag `v*` | PyInstaller `OrbitHop.exe` → itch.io `windows` channel |

One-time setup: Settings → Pages → Source: **GitHub Actions**; add the secret
`BUTLER_API_KEY` (itch.io API key) and the variables `ITCH_USER` / `ITCH_GAME`.
The itch.io steps are skipped until the secret exists.

Release: `git tag v0.1.0 && git push origin v0.1.0`.
