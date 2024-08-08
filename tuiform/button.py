from typing import Callable, Awaitable, Tuple

import curses

from tuiform.enums import NavigationInput
from tuiform.element import TUIElement


# TODO: Only handles single-line text, replace text here with the text wrap stuff
class Button(TUIElement):
    IS_INTERACTABLE = True

    hover: bool
    selected: bool
    clicked: bool

    def __init__(
        self,
        bound_function: Callable[[], Awaitable[None]],
        label: str,
    ):
        super().__init__()
        if "\n" in label:
            raise ValueError(
                "`Button` does not support multiline labels."
            )  # TODO: change this
        self.hover = False
        self.clicked = False
        self.label = label
        self.bound_function = bound_function

    async def navigation_update(self, navigation_input: NavigationInput) -> None:
        if navigation_input is NavigationInput.NONE:
            return

        match navigation_input:
            case NavigationInput.INTERACT:
                self.clicked = True
                return

        if self.parent is not None:
            await self.parent.navigation_update(navigation_input)

    def get_size(
        self, width_constraint: int | None = None, height_constraint: int | None = None
    ) -> Tuple[int, int]:
        return super().get_size(width_constraint, height_constraint)

    async def draw(self) -> None:
        if not self.draw_frame.is_drawable:
            return

        style: int = None
        if self.clicked:
            style = curses.color_pair(1) | curses.A_REVERSE | curses.A_BOLD
        elif self.is_active() or self.hover:
            style = (
                curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE | curses.A_BOLD
            )
        else:
            style = curses.color_pair(1) | curses.A_REVERSE

        # Construct our button text
        width = self.draw_frame.width
        if width < 3:
            text = "[]"
            text = text[:width]
        elif width < 5:
            text = "[" + " " * (width - 2) + "]"
            text = text[:width]
        elif len(self.label) > width - 4:
            text = f"[ {self.label[: width - 5]}… ]"
        else:
            # Pad to center
            padding = (width - 2) - len(self.label)
            l_pad = padding // 2
            r_pad = padding - l_pad
            text = f"[{' ' * l_pad}{self.label}{' ' * r_pad}]"

        height = self.draw_frame.height
        t_pad = height // 2
        b_pad = height - t_pad

        for i in range(t_pad):
            self.draw_frame.draw(
                0,
                i,
                " " * width,
                style,
            )

        self.draw_frame.draw(
            0,
            t_pad,
            text,
            style,
        )

        for i in range(b_pad):
            self.draw_frame.draw(
                0,
                t_pad + 1 + i,
                " " * width,
                style,
            )

    async def update(
        self, event_code: int, mouse_x: int, mouse_y: int, mouse_button: int
    ) -> None:
        if not self.draw_frame.is_drawable:
            return
        if event_code == curses.KEY_MOUSE and self.draw_frame.contains(
            mouse_x, mouse_y
        ):
            # Check if the mouse is within the bounds of the button
            self.hover = True
            if mouse_button in [
                curses.BUTTON1_PRESSED,
                curses.BUTTON1_CLICKED,
                curses.BUTTON1_RELEASED,
            ]:
                self.clicked = True
                self.focus()
        else:
            self.hover = False

    async def execute(self) -> None:
        if self.clicked:
            await self.bound_function()
            self.clicked = False

    async def select(self) -> None:
        self.focus()

    def __repr__(self) -> str:
        return f"Button(label={repr(self.label)})"
