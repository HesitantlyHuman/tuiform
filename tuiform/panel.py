from typing import Optional

import curses

from tuiform.enums import NavigationInput
from tuiform.screen import ScreenCoord
from tuiform.element import TUIElement, DrawFrame

class Panel(TUIElement):
    content: TUIElement
    header: Optional[TUIElement]
    footer: Optional[TUIElement]
    vertical_padding: int
    horizontal_padding: int
    header_height: int
    footer_height: int

    def __init__(
        self,
        content: TUIElement,
        vertical_padding: int = 0,
        horizontal_padding: int = 1,
        header: Optional[TUIElement] = None,
        header_height: int = 1,
        footer: Optional[TUIElement] = None,
        footer_height: int = 1,
    ):
        super().__init__()
        self.content = content
        self.vertical_padding = vertical_padding
        self.horizontal_padding = horizontal_padding
        self.header = header
        self.header_height = header_height
        self.footer = footer
        self.footer_height = footer_height
        self.active = False

        if self.header is not None:
            self.add_child(self.header)
        self.add_child(self.content)
        if self.footer is not None:
            self.add_child(self.footer)

    async def frame(self, draw_frame: DrawFrame) -> None:
        self.draw_frame = draw_frame
        inner_frame = self.draw_frame.pad(1, 1)
        content_top = 0
        content_bottom = inner_frame.height - 1

        # Calculate the bounds for the header
        if self.header is not None:
            header_bottom = (self.header_height - 1) + (2 * self.vertical_padding)
            header_frame = inner_frame.subframe(
                (
                    ScreenCoord(0, 0),
                    ScreenCoord(
                        inner_frame.width - 1,
                        header_bottom,
                    ),
                )
            )
            header_frame = header_frame.pad(
                self.horizontal_padding, self.vertical_padding
            )
            await self.header.frame(header_frame)
            if header_frame.is_drawable:
                content_top = header_bottom + 2 + 2 * self.vertical_padding

        # Calculate the bounds for the footer
        if self.footer is not None:
            total_footer_size = 2 * self.vertical_padding + self.footer_height
            footer_top = (content_bottom - total_footer_size) + 1
            footer_frame = inner_frame.subframe(
                (
                    ScreenCoord(0, footer_top),
                    ScreenCoord(
                        inner_frame.width - 1,
                        inner_frame.height - 1,
                    ),
                )
            )
            footer_frame = footer_frame.pad(
                self.horizontal_padding, self.vertical_padding
            )
            await self.footer.frame(footer_frame)
            if footer_frame.is_drawable:
                content_bottom = footer_top - (2 + 2 * self.vertical_padding)

        # Calculate the bounds for the content
        content_frame = inner_frame.subframe(
            (
                ScreenCoord(0, content_top),
                ScreenCoord(inner_frame.width - 1, content_bottom),
            )
        )
        content_frame = content_frame.pad(
            self.horizontal_padding, self.vertical_padding
        )
        await self.content.frame(content_frame)

    async def navigation_update(self, navigation_input: NavigationInput) -> None:
        if navigation_input is NavigationInput.NONE:
            return

        if len(self.children) == 0:
            if self.parent is not None:
                await self.parent.navigation_update(navigation_input)
            return

        # TODO: figure out a better way for the TUIElements to query
        # their focusable children
        match navigation_input:
            case NavigationInput.UP:
                if not self.focusable_children[0].is_focused():
                    self.focus_prev()
                    return
            case NavigationInput.DOWN:
                if not self.focusable_children[-1].is_focused():
                    self.focus_next()
                    return
            case NavigationInput.FIRST:
                if not self.focusable_children[0].is_focused():
                    self.focus(last=False)
                    return
            case NavigationInput.LAST:
                if not self.focusable_children[-1].is_focused():
                    self.focus(last=True)
                    return

        if self.parent is not None:
            await self.parent.navigation_update(navigation_input)

    async def draw(self) -> None:
        if not self.draw_frame.is_drawable:
            return

        if self.is_focused():
            style = curses.color_pair(0)
        else:
            style = curses.color_pair(0) | curses.A_DIM

        for y in [0, self.draw_frame.height - 1]:
            border = "─" * (self.draw_frame.width - 2)
            self.draw_frame.draw(1, y, border, style)

        for x in [0, self.draw_frame.width - 1]:
            for y in range(1, self.draw_frame.height - 1):
                self.draw_frame.draw(x, y, "│", style)

        self.draw_frame.draw(0, 0, "╭", style)
        self.draw_frame.draw(self.draw_frame.width - 1, 0, "╮", style)
        self.draw_frame.draw(
            self.draw_frame.width - 1, self.draw_frame.height - 1, "╯", style
        )
        self.draw_frame.draw(0, self.draw_frame.height - 1, "╰", style)

        if self.header is not None:
            if self.header.draw_frame.is_drawable:
                separator = "─" * (self.draw_frame.width - 2)
                header_separator_height = 1 + self.header_height
                self.draw_frame.draw(1, header_separator_height, separator, style)
                self.draw_frame.draw(0, header_separator_height, "├", style)
                self.draw_frame.draw(
                    self.draw_frame.width - 1, header_separator_height, "┤", style
                )

            await self.header.draw()

        if self.footer is not None:
            if self.footer.draw_frame.is_drawable:
                separator = "─" * (self.draw_frame.width - 2)
                footer_separator_height = self.draw_frame.height - (
                    2 + self.footer_height + 2 * self.vertical_padding
                )
                self.draw_frame.draw(1, footer_separator_height, separator, style)
                self.draw_frame.draw(0, footer_separator_height, "├", style)
                self.draw_frame.draw(
                    self.draw_frame.width - 1, footer_separator_height, "┤", style
                )

            await self.footer.draw()

        await self.content.draw()

    async def update(
        self, event_code: int, mouse_x: int, mouse_y: int, mouse_button: int
    ) -> None:
        if self.header is not None:
            await self.header.update(event_code, mouse_x, mouse_y, mouse_button)

        if self.footer is not None:
            await self.footer.update(event_code, mouse_x, mouse_y, mouse_button)

        await self.content.update(event_code, mouse_x, mouse_y, mouse_button)

    async def execute(self) -> None:
        if self.header is not None:
            await self.header.execute()

        if self.footer is not None:
            await self.footer.execute()

        await self.content.execute()

    def __repr__(self) -> str:
        return f"Panel(content={self.content}, header={self.header}, footer={self.footer}, horizontal_padding={self.horizontal_padding}, vertical_padding={self.vertical_padding})"

