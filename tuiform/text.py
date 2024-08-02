from typing import Tuple, List

import curses

from tuiform.enums import Orientation
from tuiform.element import TUIElement, DrawFrame
from tuiform.utils.wrap import (
    smart_wrap_text,
    right_pad_line,
    cut_line_with_ellipse,
)


class Text(TUIElement):
    def __init__(
        self, text: str, text_style: int = 0, new_line_character_style: int = 0
    ) -> None:
        super().__init__()
        self.text = text
        self.lines: List[str] = []
        self.new_line_characters: List[Tuple[int, int]] = []
        self.text_style = text_style
        self.new_line_character_style = new_line_character_style

    async def frame(self, draw_frame: DrawFrame) -> None:
        self.draw_frame = draw_frame

        if not self.draw_frame.is_drawable:
            return

        if self.draw_frame.height <= 0 or self.draw_frame.width <= 0:
            return

        # We are using a unicode character in the private use section so that
        # if there are line break characters already in the text we do not
        # format them like the characters we are adding
        real_lines = self.text.split("\n")
        real_lines = [
            line + "\uf026" if idx != len(real_lines) - 1 else line
            for idx, line in enumerate(real_lines)
        ]
        wrapped_lines: List[str] = []
        for line in real_lines:
            wrapped_lines.extend(
                smart_wrap_text(line, target_width=self.draw_frame.width)
            )

        # Now, we need to find our newline characters and take them out because
        # we want to format them differently, also pad or truncate the lines
        formatted_lines: List[str] = []
        new_line_locations: List[Tuple[int, int]] = []
        for line_number, line in enumerate(wrapped_lines):
            if len(line) > self.draw_frame.width:
                line = cut_line_with_ellipse(line, self.draw_frame.width)
            for character_number, character in enumerate(line):
                if character == "\uf026":
                    new_line_locations.append((character_number, line_number))
            line = line.replace("\uf026", "¶")
            line = right_pad_line(line, self.draw_frame.width)
            formatted_lines.append(line)

        if len(formatted_lines) > self.draw_frame.height:
            formatted_lines = formatted_lines[: self.draw_frame.height]
            last_line = cut_line_with_ellipse(
                formatted_lines[-1], self.draw_frame.width
            )
            formatted_lines[-1] = last_line

        self.lines = formatted_lines
        self.new_line_characters = new_line_locations

    async def draw(self) -> None:
        for line_idx, line in enumerate(self.lines):
            self.draw_frame.draw(0, line_idx, line, self.text_style)

        for x, y in self.new_line_characters:
            self.draw_frame.draw(x, y, "¶", self.new_line_character_style)

    def __repr__(self) -> str:
        return f"Text(text={repr(self.text)}, text_style={self.text_style})"


# TODO: fix the value coloring
class DataValue(TUIElement):
    label: str
    value: str

    def __init__(self, label: str, value: str) -> None:
        super().__init__()
        self.label = label + ":"
        self.value = value
        self.label_text_box = Text(
            text=self.label, text_style=curses.color_pair(0) | curses.A_BOLD
        )
        self.value_text_box = Text(
            text=self.value, text_style=curses.color_pair(2) | curses.A_BOLD
        )

    async def frame(self, draw_frame: DrawFrame) -> None:
        if not draw_frame.is_drawable:
            return

        self.draw_frame = draw_frame
        # TODO: how should we handle it when there is not enough space even for the label?
        frames = draw_frame.split(
            [len(self.label) + 1, None], orientation=Orientation.HORIZONTAL
        )
        await self.label_text_box.frame(frames[0])
        await self.value_text_box.frame(frames[1])

    async def draw(self) -> None:
        await self.label_text_box.draw()
        await self.value_text_box.draw()
