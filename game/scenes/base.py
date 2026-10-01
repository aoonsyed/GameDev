class Scene:
    """A screen. The App forwards taps (in logical coords), keys and fixed-step updates."""

    def __init__(self, app):
        self.app = app

    def enter(self, **kwargs) -> None:
        pass

    def tap(self, pos) -> None:
        pass

    def key(self, key: int) -> None:
        pass

    def pause(self) -> None:
        """Called when the tab is hidden, the window loses focus or the phone locks."""

    def update(self, dt: float) -> None:
        pass

    def draw(self, surf) -> None:
        pass
