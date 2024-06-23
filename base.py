from typing import Tuple, Callable, Awaitable, Optional, List, Self

import curses
from enum import Enum


class ScreenCoord:
    __slots__ = ["x", "y"]

    x: int
    y: int

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"ScreenCoord(x={self.x}, y={self.y})"


class Orientation(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class DrawFrame:
    screen: "curses._CursesWindow"
    bounds: Tuple[ScreenCoord, ScreenCoord]

    def __init__(
        self,
        screen: "curses._CursesWindow",
        bounds: Optional[Tuple[ScreenCoord, ScreenCoord]] = None,
    ):
        self.screen = screen
        self.bounds = bounds

    # TODO: change this so that we never return none instead of a draw frame
    # instead, we will return draw frames with invalid bounds, and those draw frames
    # will not draw anything when the draw method is called

    # This way, we don't have to check for None when we call draw in the components
    def draw(self, x: int, y: int, text: str, style: int = None):
        if x < 0 or y < 0:
            raise ValueError("x and y must be positive")

        adjusted_x = x + self.bounds[0].x
        adjusted_y = y + self.bounds[0].y

        if adjusted_x > self.bounds[1].x or adjusted_y > self.bounds[1].y:
            return

        # Now, lets trim the text to fit within the bounds
        if len(text) + adjusted_x > self.bounds[1].x:
            text = text[: (self.bounds[1].x - adjusted_x) + 1]

        if style is not None:
            self.screen.addstr(adjusted_y, adjusted_x, text, style)
        else:
            self.screen.addstr(adjusted_y, adjusted_x, text)

    def pad(self, horizontal: int, vertical: int) -> "DrawFrame":
        return DrawFrame(
            self.screen,
            (
                ScreenCoord(self.bounds[0].x + horizontal, self.bounds[0].y + vertical),
                ScreenCoord(self.bounds[1].x - horizontal, self.bounds[1].y - vertical),
            ),
        )

    def subframe(self, bounds: Tuple[ScreenCoord, ScreenCoord]) -> "DrawFrame":
        # TODO: fix this to only return a frame which is within the bounds of the current frame
        # additionally, if the bounds are outside of the current frame, return None
        relative_bounds = (
            ScreenCoord(bounds[0].x + self.bounds[0].x, bounds[0].y + self.bounds[0].y),
            ScreenCoord(bounds[1].x + self.bounds[0].x, bounds[1].y + self.bounds[0].y),
        )
        return DrawFrame(self.screen, relative_bounds)

    def split(
        self, splits: int | List[int | float | None], orientation: Orientation
    ) -> List[Self | None]:
        """
        Splits the frame into N subframes based on the orientation and the splits provided.

        If splits is an int, the frame will be split into that many equal parts. If
        splits is a list, the frame will be split by allocating the splits on a first-come
        first-serve basis. If one of these elements is an int, that will be the length of the
        subframe. If it is a float, it will be the percentage of the total length of the frame.
        If it is None, it will be allocated from the remaining length, split evenly among the
        remaining Nones.

        It is possible to not have enough splits to fill the frame, in which case the remaining
        space will be left empty. Additionally, it is possible to have too many splits, in which
        case some of the returned values may be None.

        Args:
            splits (int | List[int, float, None]): The number of splits to make or the lengths
                of the splits.
            orientation (Orientation): The orientation to split the frame in.

        Returns:
            List[DrawFrame | None]: The subframes created by the split.
        """
        match orientation:
            case Orientation.HORIZONTAL:
                length_to_split = (self.bounds[1].x - self.bounds[0].x) + 1
            case Orientation.VERTICAL:
                length_to_split = (self.bounds[1].y - self.bounds[0].y) + 1

        # If just an int, split into that many equal parts
        if isinstance(splits, int):
            lengths = [length_to_split // splits] * splits
            leftovers = length_to_split % splits
            # Now iterate from the end of the lengths list and add the leftovers
            idx = 0
            while leftovers > 0:
                lengths[idx] += 1
                leftovers -= 1
                idx += 1
        elif isinstance(splits, list):
            # Iterate through the list and calculate the lengths
            # We will keep the Nones for now
            desired_lengths = [None] * len(splits)
            num_nones = 0
            remaining_length = length_to_split
            for i, split in enumerate(splits):
                if split is None:
                    num_nones += 1
                elif isinstance(split, float):
                    desired_lengths[i] = int(length_to_split * split)
                    remaining_length -= desired_lengths[i]
                elif isinstance(split, int):
                    desired_lengths[i] = split
                    remaining_length -= split

            # Now we will split the remaining length among the Nones
            nones = [None] * num_nones
            if remaining_length >= num_nones:
                for i, _ in enumerate(nones):
                    nones[i] = remaining_length // num_nones
                remaining_length = remaining_length % num_nones
                idx = 0
                while remaining_length > 0:
                    nones[idx] += 1
                    remaining_length -= 1
                    idx += 1
            elif remaining_length < num_nones and remaining_length > 0:
                idx = 0
                while remaining_length > 0:
                    nones[idx] = 1
                    remaining_length -= 1
                    idx += 1

            # Now, fill our finals
            lengths = [None] * len(splits)
            remaining_length = length_to_split
            for i, desired_length in enumerate(desired_lengths):
                if desired_length is None:
                    desired_length = nones.pop(0)
                # If it is still none, then just pass
                if desired_length is None:
                    continue
                if desired_length > remaining_length:
                    lengths[i] = remaining_length
                    break
                else:
                    lengths[i] = desired_length
                    remaining_length -= desired_length

        # Now, we will create the subframes
        subframes = []
        match orientation:
            case Orientation.HORIZONTAL:
                x = self.bounds[0].x
                for length in lengths:
                    if length is None:
                        subframes.append(None)
                    else:
                        subframes.append(
                            DrawFrame(
                                self.screen,
                                (
                                    ScreenCoord(x, self.bounds[0].y),
                                    ScreenCoord(x + (length - 1), self.bounds[1].y),
                                ),
                            )
                        )
                        x += length
            case Orientation.VERTICAL:
                y = self.bounds[0].y
                for length in lengths:
                    if length is None:
                        subframes.append(None)
                    else:
                        subframes.append(
                            DrawFrame(
                                self.screen,
                                (
                                    ScreenCoord(self.bounds[0].x, y),
                                    ScreenCoord(self.bounds[1].x, y + (length - 1)),
                                ),
                            )
                        )
                        y += length

        return subframes

    def contains(self, x: int, y: int) -> bool:
        return (
            self.bounds[0].x <= x <= self.bounds[1].x
            and self.bounds[0].y <= y <= self.bounds[1].y
        )

    @property
    def width(self) -> int:
        return (self.bounds[1].x - self.bounds[0].x) + 1

    @property
    def height(self) -> int:
        return (self.bounds[1].y - self.bounds[0].y) + 1

    def __repr__(self) -> str:
        return f"DrawFrame(screen={self.screen}, bounds={self.bounds})"


class TUIObject:
    draw_frame: DrawFrame

    async def frame(self, draw_frame: DrawFrame) -> None:
        """Sets the location for the object to be drawn in the view"""
        self.draw_frame = draw_frame

    async def update(
        self, event_code: int, mouse_x: int, mouse_y: int, mouse_button: int
    ) -> None:
        """Updates the object based on the user input"""
        pass

    async def draw(self) -> None:
        raise NotImplementedError("draw method must be implemented")

    async def execute(self) -> None:
        """Execute any actions that the object needs to perform"""
        pass


# TODO:
# - Better colors for the draw frame (convert to curses crap)


class Fill(TUIObject):
    def __init__(self, fill_char: str, style: int) -> None:
        self.fill_char = fill_char
        self.style = style
        super().__init__()

    async def draw(self) -> None:
        for y in range(self.draw_frame.height):
            self.draw_frame.draw(
                0, y, self.fill_char * self.draw_frame.width, self.style
            )

    def __repr__(self) -> str:
        return f"Fill(fill_char={self.fill_char}, style={self.style})"


# TODO: Stack will delete buttons if the padding is too large
class Stack(TUIObject):
    def __init__(
        self,
        elements: List[TUIObject],
        orientation: Orientation,
        splits: int | List[int | float | None] | None = None,
        element_padding: int = 3,
        element_padding_style: int = 0,
        divider: str | None = None,
        divider_style: int = 0,
    ) -> None:
        self.elements = elements
        self.orientation = orientation
        if splits is None:
            self.splits = [None] * len(elements)
        else:
            self.splits = splits
        self.element_padding = element_padding
        self.divider = divider

        if divider is not None:
            # Interleave dividers of size 1
            new_elements = []
            new_splits = []
            for i, (element, split) in enumerate(zip(self.elements, self.splits)):
                new_elements.append(element)
                new_splits.append(split)
                if i < len(self.elements) - 1:
                    new_elements.append(Fill(divider, divider_style))
                    new_splits.append(1)

            self.elements = new_elements
            self.splits = new_splits

        if element_padding > 0:
            # Interleave padding
            new_elements = []
            new_splits = []
            for i, (element, split) in enumerate(zip(self.elements, self.splits)):
                new_elements.append(element)
                new_splits.append(split)
                if i < len(self.elements) - 1:
                    new_elements.append(Fill(" ", element_padding_style))
                    new_splits.append(element_padding)

            self.elements = new_elements
            self.splits = new_splits

        self.drawable = [True for _ in self.elements]

        super().__init__()

    async def frame(self, draw_frame: DrawFrame) -> None:
        self.draw_frame = draw_frame
        subframes = self.draw_frame.split(self.splits, self.orientation)
        for i, element in enumerate(self.elements):
            await element.frame(subframes[i])
            if subframes[i] is not None:
                self.drawable[i] = True
            else:
                self.drawable[i] = False

    async def draw(self) -> None:
        for i, element in enumerate(self.elements):
            if self.drawable[i]:
                await element.draw()

    async def update(
        self, event_code: int, mouse_x: int, mouse_y: int, mouse_button: int
    ) -> None:
        for element in self.elements:
            await element.update(event_code, mouse_x, mouse_y, mouse_button)

    async def execute(self) -> None:
        for element in self.elements:
            await element.execute()


class Panel:
    active: bool

    def __init__(
        self,
        content: TUIObject,
        vertical_padding: int = 1,
        horizontal_padding: int = 1,
        header: Optional[TUIObject] = None,
        header_height: int = 1,
        footer: Optional[TUIObject] = None,
        footer_height: int = 1,
    ):
        self.content = content
        self.vertical_padding = vertical_padding
        self.horizontal_padding = horizontal_padding
        self.header = header
        self.header_height = header_height
        self.footer = footer
        self.footer_height = footer_height
        self.active = False

        self.header_is_drawable = False
        self.footer_is_drawable = False
        self.content_is_drawable = False

    async def frame(self, draw_frame: DrawFrame) -> None:
        self.draw_frame = draw_frame

        inner_frame = self.draw_frame.pad(1, 1)
        top_bound = 0
        bottom_bound = inner_frame.height - 1

        # Calculate the bounds for the header
        if self.header is not None:
            top_bound = self.header_height + 1 + 2 * self.vertical_padding
            header_frame = inner_frame.subframe(
                (
                    ScreenCoord(0, 0),
                    ScreenCoord(
                        inner_frame.width - 1,
                        top_bound,
                    ),
                )
            )
            if header_frame is not None:
                header_frame = header_frame.pad(
                    self.horizontal_padding, self.vertical_padding
                )
            if header_frame is not None:
                await self.header.frame(header_frame)
                self.header_is_drawable = True
            else:
                self.header_is_drawable = False

        # Calculate the bounds for the footer
        if self.footer is not None:
            footer_top = (bottom_bound - self.footer_height) + 1
            footer_frame = inner_frame.subframe(
                (
                    ScreenCoord(0, footer_top),
                    ScreenCoord(
                        inner_frame.width - 1,
                        inner_frame.height - 1,
                    ),
                )
            )
            if footer_frame is not None:
                footer_frame = footer_frame.pad(
                    self.horizontal_padding, self.vertical_padding
                )
            if footer_frame is not None:
                await self.footer.frame(footer_frame)
                self.footer_is_drawable = True
                bottom_bound = footer_top - (2 + 2 * self.vertical_padding)

        # Calculate the bounds for the content
        content_frame = inner_frame.subframe(
            (
                ScreenCoord(0, top_bound),
                ScreenCoord(inner_frame.width - 1, bottom_bound),
            )
        )
        if content_frame is not None:
            content_frame = content_frame.pad(
                self.horizontal_padding, self.vertical_padding
            )
        if content_frame is not None:
            await self.content.frame(content_frame)
            self.content_is_drawable = True

    async def draw(self) -> None:
        for y in [0, self.draw_frame.height - 1]:
            border = "─" * (self.draw_frame.width - 2)
            self.draw_frame.draw(1, y, border)

        for x in [0, self.draw_frame.width - 1]:
            for y in range(1, self.draw_frame.height - 1):
                self.draw_frame.draw(x, y, "│")

        self.draw_frame.draw(0, 0, "╭")
        self.draw_frame.draw(self.draw_frame.width - 1, 0, "╮")
        self.draw_frame.draw(self.draw_frame.width - 1, self.draw_frame.height - 1, "╯")
        self.draw_frame.draw(0, self.draw_frame.height - 1, "╰")

        if self.header is not None and self.header_is_drawable:
            await self.header.draw()

        if self.footer is not None and self.footer_is_drawable:
            separator = "─" * (self.draw_frame.width - 2)
            footer_separator_height = self.draw_frame.height - (2 + self.footer_height)
            self.draw_frame.draw(1, footer_separator_height, separator)
            self.draw_frame.draw(0, footer_separator_height, "├")
            self.draw_frame.draw(
                self.draw_frame.width - 1, footer_separator_height, "┤"
            )

            await self.footer.draw()

        if self.content_is_drawable:
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


# Only handles single-line text
class Button(TUIObject):
    hover: bool
    selected: bool
    clicked: bool

    def __init__(
        self,
        bound_function: Callable[[], Awaitable[None]],
        label: str,
    ):
        self.hover = False
        self.selected = False
        self.clicked = False
        self.label = label
        self.bound_function = bound_function
        super().__init__()

    async def draw(self) -> None:
        style = None
        if self.clicked:
            style = curses.color_pair(1) | curses.A_REVERSE | curses.A_BOLD
        elif self.selected or self.hover:
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
        if self.draw_frame is None:
            return
        if event_code == curses.KEY_MOUSE:
            # Check if the mouse is within the bounds of the button
            if self.draw_frame.contains(mouse_x, mouse_y):
                self.hover = True
                if mouse_button in [
                    curses.BUTTON1_PRESSED,
                    curses.BUTTON1_CLICKED,
                    curses.BUTTON1_RELEASED,
                ]:
                    self.clicked = True
            else:
                self.hover = False
        elif event_code == curses.KEY_ENTER and (self.hover or self.selected):
            self.clicked = True
        elif event_code == 27 and (self.selected or self.clicked):
            self.clicked = False
            self.selected = False

    async def step(self) -> None:
        if self.clicked:
            await self.bound_function()
            self.clicked = False

    async def select(self) -> None:
        self.selected = True

    def __repr__(self) -> str:
        return f"Button(label={self.label})"


# TODO: Add some sort of hover animation
# TODO: Add a copied to clipboard overlay message (how do we do this within the draw frame framework)
# TODO: Implement the copying to clipboard
class CopyableObject(TUIObject):
    COPY_ICON = "⧉"

    def __init__(
        self, object: TUIObject, text_to_copy: str, copy_button_style: int = 0
    ):
        self.object = object
        self.text_to_copy = text_to_copy
        self.copy_button_style = copy_button_style
        super().__init__()

    async def frame(self, draw_frame: DrawFrame) -> None:
        # We need to reserve the far right column for the copy button
        wrapped_object_frame = draw_frame.subframe(
            (
                ScreenCoord(0, 0),
                ScreenCoord(draw_frame.width - 1, draw_frame.height - 2),
            )
        )
        await self.object.frame(wrapped_object_frame)

    async def draw(self) -> None:
        self.draw_frame.draw(
            self.draw_frame.width - 1,
            0,
            CopyableObject.COPY_ICON,
            self.copy_button_style,
        )
        await self.object.draw()

    async def update(
        self, event_code: int, mouse_x: int, mouse_y: int, mouse_button: int
    ) -> None:
        pass

    async def execute(self) -> None:
        pass

    def __repr__(self) -> str:
        return f"CopyableText(object={self.object}, text_to_copy={self.text_to_copy}, copy_button_style={self.copy_button_style})"


from autograder.logging.tui.utils.text import (
    smart_wrap_text,
    right_pad_line,
    cut_line_with_ellipse,
)


class Text(TUIObject):
    def __init__(
        self, text: str, text_style: int = 0, new_line_character_style: int = 0
    ) -> None:
        self.text = text
        self.lines: List[str] = []
        self.new_line_characters: List[Tuple[int, int]] = []
        self.text_style = text_style
        self.new_line_character_style = new_line_character_style

    async def frame(self, draw_frame: DrawFrame) -> None:
        self.draw_frame = draw_frame

        # We are using a unicode character in the private use section so that
        # if there are line break characters already in the text we do not
        # format them like the characters we are adding
        real_lines = [line + "\uf026" for line in self.text.split("\n")]
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
            line = line.replace("\uf026", " ")
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


# Have three threads: one for rendering/drawing, one for watching events/input, and one for updating state
if __name__ == "__main__":
    import asyncio

    # button_one = Button(None, "Button One")
    # button_one.bound_function = button_one.select
    # button_two = Button(None, "Button Two")
    # button_two.bound_function = button_one.select
    # button_three = Button(None, "Button Three")
    # button_three.bound_function = button_three.select

    # button_stack = Stack(
    #     [button_one, button_two, button_three],
    #     Orientation.HORIZONTAL,
    #     element_padding=1,
    #     divider="│",
    # )

    # text_block = Text(
    #     "Here is some text¶ that we would like to have wrap very nicely and not exceed our cute little text box area.\nAnd the text, just does not stop. Just goes on and on and on, and there might even be some tremendously exceptionally long words occassionally",
    #     new_line_character_style=0,
    # )
    # button_panel = Panel(text_block, vertical_padding=0, footer=button_stack)
    # draw_frame = DrawFrame(None, (ScreenCoord(0, 3), ScreenCoord(70, 8)))

    # asyncio.run(button_panel.frame(draw_frame))
    # asdf

    # Here is how we will track the mouse realtime

    # Set environment variables
    from os import environ

    # TODO: be a nice citizen and save the old TERM value and restore it later
    # TODO: Also, check if we are in a terminal that supports the XTERM API
    # before doing this
    environ["TERM"] = "xterm-1003"

    import curses

    screen = curses.initscr()
    screen.keypad(1)
    screen.nodelay(1)

    # Now set up our colors

    # STYLING (FUCK ME)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(0, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

    curses.curs_set(0)
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
    curses.mouseinterval(5)
    print("\033[?1003h")  # enable mouse tracking with the XTERM API
    # https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Mouse-Tracking
    curses.flushinp()
    curses.noecho()
    screen.clear()

    button_one = Button(None, "Button One")
    button_one.bound_function = button_one.select
    button_two = Button(None, "Button Two")
    button_two.bound_function = button_one.select
    button_three = Button(None, "Button Three")
    button_three.bound_function = button_three.select

    button_stack = Stack(
        [button_one, button_two, button_three],
        Orientation.HORIZONTAL,
        element_padding=1,
        divider="│",
    )

    text_block = Text(
        "Here is some text¶ that we would like to have wrap very nicely and not exceed our cute little text box area.\nAnd the text, just does not stop. Just goes on and on and on, and there might even be some tremendously exceptionally long words occassionally",
        new_line_character_style=curses.color_pair(0) | curses.A_DIM,
    )
    button_panel = Panel(text_block, vertical_padding=0, footer=button_stack)
    draw_frame = DrawFrame(screen, (ScreenCoord(0, 3), ScreenCoord(70, 8)))

    async def await_getch(screen: "curses._CursesWindow"):
        while True:
            key = screen.getch()
            if key != curses.ERR:
                return key
            await asyncio.sleep(0.01)

    async def main():
        await button_panel.frame(draw_frame)
        while True:
            key = await await_getch(screen)
            screen.erase()  # Do not use clear(), as it will cause flickering artifacts
            screen.addstr(f"Key: {key}")
            mouse_x, mouse_y, mouse_button = None, None, None
            if key == curses.KEY_MOUSE:
                _, x, y, _, button = curses.getmouse()
                mouse_x, mouse_y, mouse_button = x, y, button
                screen.addstr(1, 0, f"Mouse info: {x}, {y} - {button}")
            elif key == ord("q"):
                break

            for i in range(80):
                if i % 3 == 0:
                    screen.addstr(2, i, f"{i}")

            await button_panel.update(key, mouse_x, mouse_y, mouse_button)
            await button_panel.draw()
            await button_panel.execute()

    asyncio.run(main())

    curses.endwin()
    curses.flushinp()
    print("\033[?1003l")  # disable mouse tracking with the XTERM API
