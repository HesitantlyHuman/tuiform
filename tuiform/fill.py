from tuiform.element import TUIElement

class Fill(TUIElement):
    fill_char: str
    style: int

    def __init__(self, fill_char: str, style: int) -> None:
        super().__init__()
        self.fill_char = fill_char
        self.style = style

    async def draw(self) -> None:
        for y in range(self.draw_frame.height):
            self.draw_frame.draw(
                0, y, self.fill_char * self.draw_frame.width, self.style
            )

    def __repr__(self) -> str:
        return f"Fill(fill_char={repr(self.fill_char)}, style={self.style})"