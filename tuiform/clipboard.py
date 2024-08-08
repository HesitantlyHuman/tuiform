import time
import curses
from typing import Tuple
import clipman

from tuiform.element import TUIElement, DrawFrame
from tuiform.screen import ScreenCoord
from tuiform.enums import NavigationInput

CLIPBOARD_AVAILABLE = False

try:
    clipman.init()
    CLIPBOARD_AVAILABLE = True
except:
    pass


class CopyableObject(TUIElement):
    IS_INTERACTABLE = True

    COPY_ICON = "⧉"
    MESSAGE_DISPLAY_TIME = 1

    copied: bool
    selected: bool
    hovered: bool
    copied_timestamp: float

    def __init__(
        self,
        content: TUIElement,
        text_to_copy: str,
        copy_button_style: int = 0,
        copy_button_highlight_style: int = None,
    ):
        super().__init__()
        self.content = content
        self.text_to_copy = text_to_copy
        self.copy_button_style = copy_button_style
        if copy_button_highlight_style is None:
            copy_button_highlight_style = self.copy_button_style | curses.A_BOLD
        self.copy_button_highlight_style = copy_button_highlight_style
        self.hovered = False
        self.selected = False
        self.copied = False
        self.copied_timestamp = 0

    def get_size(
        self, width_constraint: int | None = None, height_constraint: int | None = None
    ) -> Tuple[int, int]:
        if width_constraint is not None:
            width_constraint = width_constraint - 2

        content_width, content_height = self.content.get_size(
            width_constraint=width_constraint, height_constraint=height_constraint
        )

        return content_width + 2, content_height

    async def frame(self, draw_frame: DrawFrame) -> None:
        self.draw_frame = draw_frame
        if not self.draw_frame.is_drawable:
            return

        # We need to reserve the far right column for the copy button
        wrapped_object_frame = draw_frame.subframe(
            (
                ScreenCoord(0, 0),
                ScreenCoord(draw_frame.width - 3, draw_frame.height - 1),
            )
        )
        await self.content.frame(wrapped_object_frame)

    async def navigation_update(self, navigation_input: NavigationInput) -> None:
        if navigation_input is NavigationInput.NONE:
            return

        match navigation_input:
            case NavigationInput.INTERACT:
                self.copied = True

        if self.parent is not None:
            await self.parent.navigation_update(navigation_input)

    async def draw(self) -> None:
        if not self.draw_frame.is_drawable:
            return

        if self.hovered or self.is_active():
            style = self.copy_button_highlight_style
        else:
            style = self.copy_button_style

        self.draw_frame.draw(
            self.draw_frame.width - 1,
            0,
            CopyableObject.COPY_ICON,
            style,
        )

        if time.time() < self.copied_timestamp + CopyableObject.MESSAGE_DISPLAY_TIME:
            # TODO: query the size of the screen so that we can push this overlay
            # message around to always show up
            # TODO: Give the messages borders
            if CLIPBOARD_AVAILABLE:
                self.draw_frame.draw(
                    self.draw_frame.width - 10,
                    -1,
                    "(Copied to clipboard)",
                    overlay=True,
                    z=1,
                )
            else:
                self.draw_frame.draw(
                    self.draw_frame.width - 76,
                    -1,
                    "(Install `xsel` or `xclip` if you want to be able to copy to your clipboard)",
                    overlay=True,
                    z=1,
                )

        await self.content.draw()

    async def update(
        self, event_code: int, mouse_x: int, mouse_y: int, mouse_button: int
    ) -> None:
        if not self.draw_frame.is_drawable:
            return

        if event_code == curses.KEY_MOUSE:
            if self.draw_frame.contains(mouse_x, mouse_y) and mouse_button in [
                curses.BUTTON1_PRESSED,
                curses.BUTTON1_CLICKED,
                curses.BUTTON1_RELEASED,
            ]:
                self.selected = True

            local_x, local_y = self.draw_frame.local(mouse_x, mouse_y)
            if local_x == self.draw_frame.width - 1 and local_y == 0:
                self.hovered = True
                if mouse_button in [
                    curses.BUTTON1_PRESSED,
                    curses.BUTTON1_CLICKED,
                    curses.BUTTON1_RELEASED,
                ]:
                    self.copied = True
            else:
                self.hovered = False

        await self.content.update(
            event_code=event_code,
            mouse_x=mouse_x,
            mouse_y=mouse_y,
            mouse_button=mouse_button,
        )

    async def execute(self) -> None:
        if self.copied:
            self.copied = False
            self.copied_timestamp = time.time()
            if CLIPBOARD_AVAILABLE:
                clipman.set(self.text_to_copy)
        await self.content.execute()

    def __repr__(self) -> str:
        return f"CopyableText(content={self.content}, text_to_copy={repr(self.text_to_copy)}, copy_button_style={self.copy_button_style})"
