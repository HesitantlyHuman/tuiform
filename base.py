from typing import Tuple, Callable, Awaitable, Optional, List, Self

import curses
import pyperclip
from enum import Enum

import time


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


class FocusTree:
    focusable: bool
    focused: bool
    on_focus: Callable[[], Awaitable[None]]
    children: List["FocusTree"]
    parent: Optional["FocusTree"]

    async def focus_self(self) -> None:
        if not self.focusable:
            raise ValueError("This FocusTree is not focusable")

    async def focus_next() -> None:
        pass

    async def focus_previous() -> None:
        pass

    async def clear_focus(self) -> None:
        for child in self.children:
            await child.clear_focus()

    @property
    def child_is_focused(self) -> bool:
        for child in self.children:
            if child.focused or child.child_is_focused:
                return True
        return False


class DrawFrame:
    screen: "curses._CursesWindow"
    bounds: Optional[Tuple[ScreenCoord, ScreenCoord]]

    def __init__(
        self,
        screen: "curses._CursesWindow",
        bounds: Optional[Tuple[ScreenCoord, ScreenCoord]] = None,
    ):
        self.screen = screen
        if bounds is not None:
            bounds = (
                ScreenCoord(max(0, bounds[0].x), max(0, bounds[0].y)),
                ScreenCoord(bounds[1].x, bounds[1].y),
            )
            if (
                bounds[0].x > bounds[1].x  # Inverted horizontal bounds
                or bounds[0].y > bounds[1].y  # Inverted vertical bounds
            ):
                bounds = None
        self.bounds = bounds

    # TODO: fix this so that overlays are always on top of non-overlays
    def draw(self, x: int, y: int, text: str, style: int = None, overlay: bool = False):
        if not self.is_drawable:
            return

        adjusted_x = x + self.bounds[0].x
        adjusted_y = y + self.bounds[0].y

        if not overlay and (
            adjusted_x > self.bounds[1].x or adjusted_y > self.bounds[1].y
        ):
            return

        screen_height, screen_width = screen.getmaxyx()
        if adjusted_y > screen_height:
            return

        # Now, lets trim the text to fit within the bounds
        if (not overlay and (len(text) + adjusted_x > self.bounds[1].x)) or (
            len(text) + adjusted_x > screen_width
        ):
            text = text[
                : min(
                    (self.bounds[1].x - adjusted_x) + 1, (screen_width - adjusted_x) + 1
                )
            ]

        # Curses will fail if we try to draw to the bottom right corner of the
        # screen, so we need to check if we are trying to do so, and just draw
        # that character seperate
        if adjusted_x + len(text) >= screen_width and adjusted_y >= screen_height - 1:
            if style is not None:
                try:
                    self.screen.addstr(adjusted_y, adjusted_x, text[-1], style)
                except curses.error:
                    pass
            else:
                try:
                    self.screen.addstr(adjusted_y, adjusted_x, text[-1])
                except curses.error:
                    pass
            if len(text) == 1:
                return
            text = text[:-1]

        if style is not None:
            self.screen.addstr(adjusted_y, adjusted_x, text, style)
        else:
            self.screen.addstr(adjusted_y, adjusted_x, text)

    def pad(self, horizontal: int, vertical: int) -> "DrawFrame":
        if (
            not self.is_drawable
            or self.width <= 2 * horizontal
            or self.height <= 2 * vertical
        ):
            return DrawFrame(self.screen, None)
        return DrawFrame(
            self.screen,
            (
                ScreenCoord(self.bounds[0].x + horizontal, self.bounds[0].y + vertical),
                ScreenCoord(self.bounds[1].x - horizontal, self.bounds[1].y - vertical),
            ),
        )

    def subframe(self, bounds: Tuple[ScreenCoord, ScreenCoord]) -> "DrawFrame":
        if not self.is_drawable:
            return DrawFrame(self.screen, None)
        bounds = (
            ScreenCoord(max(0, bounds[0].x), max(0, bounds[0].y)),
            ScreenCoord(min(self.width, bounds[1].x), min(self.height, bounds[1].y)),
        )
        if (
            bounds[0].x >= self.width  # Left border past current right
            or bounds[0].y >= self.height  # Bottom border past current bottom
            or bounds[0].x > bounds[1].x  # Inverted horizontal bounds
            or bounds[0].y > bounds[1].y  # Inverted vertical bounds
        ):
            return DrawFrame(self.screen, None)

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
        if not self.is_drawable:
            if isinstance(splits, int):
                return [DrawFrame(self.screen, None) for _ in range(splits)]
            elif isinstance(splits, list):
                return [DrawFrame(self.screen, None) for _ in splits]
            else:
                raise ValueError(
                    f"Expected splits to be an int or a list, instead got {splits}"
                )

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
        else:
            raise ValueError(
                f"Expected splits to be an int or a list, instead got {splits}"
            )

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
                        subframes.append(DrawFrame(self.screen, None))
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

    def local(self, global_x: int, global_y: int) -> Optional[Tuple[int, int]]:
        if not self.is_drawable:
            return None
        local_x = global_x - self.bounds[0].x
        local_y = global_y - self.bounds[0].y
        return (local_x, local_y)

    def contains(self, x: int, y: int) -> bool:
        if not self.is_drawable:
            return False
        return (
            self.bounds[0].x <= x <= self.bounds[1].x
            and self.bounds[0].y <= y <= self.bounds[1].y
        )

    @property
    def width(self) -> Optional[int]:
        if self.bounds is None:
            return 0
        return (self.bounds[1].x - self.bounds[0].x) + 1

    @property
    def height(self) -> Optional[int]:
        if self.bounds is None:
            return 0
        return (self.bounds[1].y - self.bounds[0].y) + 1

    @property
    def is_drawable(self) -> bool:
        return self.bounds is not None

    def __repr__(self) -> str:
        return f"DrawFrame(screen={self.screen}, bounds={self.bounds})"


class TUIObject:
    FOCUSABLE: bool
    focused: bool
    draw_frame: DrawFrame
    children: Optional[List["TUIObject"]]
    parent: Optional["TUIObject"]

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

    async def add_children(self) -> None:
        pass

    def focus_next(self) -> None:
        if self.parent:
            self.parent.clear_focus()
        pass

    def focus_prev(self) -> None:
        # First, before we reset the focus, lets
        # find what needs to be focused

        if self.parent:
            self.parent.clear_focus()
        pass

    def focus_self(self) -> None:
        self.clear_focus()
        if self.FOCUSABLE:
            self.focused = True
        elif len(self.children) > 0:
            self.children[0].focus_self()

    def clear_focus(self) -> None:
        self.focused = False
        for child in self.children:
            child.clear_focus()


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
            footer_top = (content_bottom - self.footer_height) + 1
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

    async def draw(self) -> None:
        if not self.draw_frame.is_drawable:
            return

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

        if self.header is not None:
            if self.header.draw_frame.is_drawable:
                separator = "─" * (self.draw_frame.width - 2)
                header_separator_height = 1 + self.header_height
                self.draw_frame.draw(1, header_separator_height, separator)
                self.draw_frame.draw(0, header_separator_height, "├")
                self.draw_frame.draw(
                    self.draw_frame.width - 1, header_separator_height, "┤"
                )

            await self.header.draw()

        if self.footer is not None:
            if self.footer.draw_frame.is_drawable:
                separator = "─" * (self.draw_frame.width - 2)
                footer_separator_height = self.draw_frame.height - (
                    2 + self.footer_height
                )
                self.draw_frame.draw(1, footer_separator_height, separator)
                self.draw_frame.draw(0, footer_separator_height, "├")
                self.draw_frame.draw(
                    self.draw_frame.width - 1, footer_separator_height, "┤"
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
        if not self.draw_frame.is_drawable:
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

    async def execute(self) -> None:
        if self.clicked:
            await self.bound_function()
            self.clicked = False

    async def select(self) -> None:
        self.selected = True

    def __repr__(self) -> str:
        return f"Button(label={self.label})"


# TODO: Add in a check for the linux xsel or xclip libs and change message to alert user
# TODO: Add some sort of hover animation
# TODO: Add a copied to clipboard overlay message (how do we do this within the draw frame framework)
# TODO: Implement the copying to clipboard
class CopyableObject(TUIObject):
    COPY_ICON = "⧉"
    MESSAGE_DISPLAY_TIME = 1

    copied: bool
    selected: bool
    hovered: bool
    copied_timestamp: float

    def __init__(
        self,
        object: TUIObject,
        text_to_copy: str,
        copy_button_style: int = 0,
        copy_button_highlight_style: int = None,
    ):
        self.object = object
        self.text_to_copy = text_to_copy
        self.copy_button_style = copy_button_style
        if copy_button_highlight_style is None:
            copy_button_highlight_style = self.copy_button_style | curses.A_BOLD
        self.copy_button_highlight_style = copy_button_highlight_style
        self.hovered = False
        self.selected = False
        self.copied = False
        self.copied_timestamp = 0
        super().__init__()

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
        await self.object.frame(wrapped_object_frame)

    async def draw(self) -> None:
        if not self.draw_frame.is_drawable:
            return
        self.draw_frame.draw(
            self.draw_frame.width - 1,
            0,
            CopyableObject.COPY_ICON,
            (
                self.copy_button_highlight_style
                if self.hovered
                else self.copy_button_style
            ),
        )

        if time.time() < self.copied_timestamp + CopyableObject.MESSAGE_DISPLAY_TIME:
            self.draw_frame.draw(
                self.draw_frame.width - 10, -1, "(Copied to clipboard)", overlay=True
            )

        await self.object.draw()

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

        else:
            pass  # TODO: figure out how to check for Ctrl + Shift + C
        await self.object.update(
            event_code=event_code,
            mouse_x=mouse_x,
            mouse_y=mouse_y,
            mouse_button=mouse_button,
        )

    async def execute(self) -> None:
        if self.copied:
            self.copied = False
            self.copied_timestamp = time.time()
        await self.object.execute()

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


# TODO: fix the value coloring
class DataValue(TUIObject):
    label: str
    value: str

    def __init__(self, label: str, value: str) -> None:
        self.label = label + ":"
        self.value = value
        self.label_text_box = Text(
            text=self.label, text_style=curses.color_pair(0) | curses.A_BOLD
        )
        self.value_text_box = Text(
            text=self.value, text_style=curses.color_pair(2) | curses.A_BOLD
        )

    async def frame(self, draw_frame: DrawFrame) -> None:
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


# TODO: figure out how to have something scrollable...
# The issue is that the scrollable item needs to know how big it is, based on its internals...
# the problem for us is that we have designed everything with a top down control scheme

# TODO: How do we do changing selection with the arrow keys
# Make sure everything is navigable without mouse

# FOCUS HANDLING
# Clicks should completely override the focus
# Tabs and Shift + Tabs should change the focus
# Arrow keys should change focus if the user has reached the end of internal selections / behavior
# Maybe they should just have some bindable .focus_next() and .focus_prev()
# Or maybe they should be given an object which they can call those functions on? Focus Chain
# And the focus chain would be nestable, so if we need to break out it can do that

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
    curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)

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
    button_three = Button(None, "Button Three lol")
    button_three.bound_function = button_three.select

    bottom_button_stack = Stack(
        [button_one, button_two, button_three],
        Orientation.HORIZONTAL,
        element_padding=1,
        divider="│",
    )

    button_four = Button(None, "Button Four")
    button_four.bound_function = button_three.select

    text_block = Text(
        "Here is some text¶ that we would like to have wrap very nicely and not exceed our cute little text box area.\nAnd the text, just does not stop. Just goes on and on and on, and there might even be some tremendously exceptionally long words occassionally",
        new_line_character_style=curses.color_pair(0) | curses.A_DIM,
    )
    value_example = DataValue("Active Log", "generate_sums")
    copyable_text_block = CopyableObject(object=text_block, text_to_copy="HELLO THERE")
    content_stack = Stack(
        [copyable_text_block, value_example],
        orientation=Orientation.VERTICAL,
        element_padding=0,
    )
    button_panel = Panel(
        content_stack,
        vertical_padding=0,
        footer=bottom_button_stack,
        header=button_four,
    )

    async def await_getch(screen: "curses._CursesWindow"):
        while True:
            key = screen.getch()
            if key != curses.ERR:
                return key
            await asyncio.sleep(0.025)

    async def main():
        height, width = screen.getmaxyx()
        draw_frame = DrawFrame(
            screen, (ScreenCoord(0, 3), ScreenCoord(width - 1, height - 1))
        )
        await button_panel.frame(draw_frame)
        while True:
            key = await await_getch(screen)
            screen.erase()  # Do not use clear(), as it will cause flickering artifacts
            screen.addstr(f"Key: {key}")

            mouse_x, mouse_y, mouse_button = None, None, None
            if key == curses.KEY_RESIZE:
                height, width = screen.getmaxyx()
                draw_frame = DrawFrame(
                    screen, (ScreenCoord(0, 3), ScreenCoord(width - 1, height - 1))
                )
                await button_panel.frame(draw_frame)
            elif key == curses.KEY_MOUSE:
                _, x, y, _, button = curses.getmouse()
                mouse_x, mouse_y, mouse_button = x, y, button
                screen.addstr(1, 0, f"Mouse info: {x}, {y} - {button}")
            elif key == ord("q"):
                break

            await button_panel.update(key, mouse_x, mouse_y, mouse_button)
            await button_panel.draw()
            await button_panel.execute()

    asyncio.run(main())

    curses.endwin()
    curses.flushinp()
    print("\033[?1003l")  # disable mouse tracking with the XTERM API
