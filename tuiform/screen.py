class ScreenCoord:
    __slots__ = ["x", "y"]

    x: int
    y: int

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"ScreenCoord(x={self.x}, y={self.y})"
