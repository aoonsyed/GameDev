"""Orbit Hop entry point.

    python main.py          # desktop
    pygbag .                # browser test at http://localhost:8000
"""

import asyncio

import pygame  # noqa: F401  (pygbag scans main.py imports to bundle pygame-ce)

from game.app import App


async def main():
    app = App()
    await app.run()


asyncio.run(main())
