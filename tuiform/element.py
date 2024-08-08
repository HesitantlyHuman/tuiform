from typing import Tuple, Optional, List, Sequence, Any

import asyncio
from os import environ

import curses

from tuiform.screen import ScreenCoord
from tuiform.enums import NavigationInput, Orientation


async def await_getch(screen: "curses._CursesWindow") -> int:
    while True:
        key = screen.getch()
        if key != curses.ERR:
            return key
        await asyncio.sleep(0.025)


class TUIWindow:
    screen: "curses._CursesWindow"
    top_level_element: "TUIElement"
    bounds: Tuple[ScreenCoord, ScreenCoord]
    resize: bool

    _needs_redraw: bool
    _pending_draws: List[List[Tuple[ScreenCoord, str, int]]]
    _focused_elements: List["TUIElement"]
    _active_element: "TUIElement"
    _screen_size: Tuple[int, int]
    _screen_padding: Tuple[int, int, int, int]

    def __init__(
        self,
        screen: "curses._CursesWindow",
        top_level_element: "TUIElement",
        bounds: Tuple[ScreenCoord, ScreenCoord] = None,
        resize: bool = True,
    ) -> None:
        self.top_level_element = top_level_element
        self.screen = screen

        self._pending_draws = []
        self._screen_size = None
        self._resize = True
        self._focused_elements = []
        self._active_element = None  # TODO: focus an element here
        self._needs_redraw = False

        if bounds is None:
            bounds = (
                ScreenCoord(0, 0),
                ScreenCoord(self.screen_width, self.screen_height),
            )
        self.bounds = bounds
        self._screen_padding = (
            self.bounds[0].y,
            self.screen_width - self.bounds[1].x,
            self.screen_height - self.bounds[1].y,
            self.bounds[0].x,
        )  # Top, Right, Bottom, Left
        self.resize = resize

    def schedule_draw(
        self, position: ScreenCoord, text: str, style: int = None, z: int = 0
    ) -> None:
        if z + 1 > len(self._pending_draws):
            self._pending_draws.extend(
                [[] for _ in range(z + 1 - len(self._pending_draws))]
            )
        self._pending_draws[z].append((position, text, style))

    def run_draw_calls(self) -> None:
        for draw_layer in self._pending_draws:
            for draw_call in draw_layer:
                pos, text, style = draw_call
                self.run_draw_call(pos.x, pos.y, text, style)
        self._pending_draws = []

    def run_draw_call(self, x: int, y: int, text: str, style: int = None) -> None:
        # Curses will fail if we try to draw to the bottom right corner of the
        # screen, so we need to check if we are trying to do so, and just draw
        # that character seperate
        if x + len(text) >= self.screen_width and y >= self.screen_height - 1:
            if style is None:
                try:
                    self.screen.addstr(y, x, text[-1])
                except curses.error:
                    pass
            else:
                try:
                    self.screen.addstr(y, x, text[-1], style)
                except curses.error:
                    pass
            if len(text) == 1:
                return
            text = text[:-1]

        if style is None:
            self.screen.addstr(y, x, text)
        else:
            self.screen.addstr(y, x, text, style)

    async def draw(self) -> None:
        if self._needs_redraw:
            self.screen.erase()  # Do not use clear(), as it will cause flickering artifacts
            await self.top_level_element.draw()
            self.run_draw_calls()
            self._needs_redraw = False

    async def frame(self) -> None:
        self._screen_size = None
        new_bounds = (
            ScreenCoord(
                self._screen_padding[3],
                self._screen_padding[0] + 2,
            ),
            ScreenCoord(
                self.screen_width - self._screen_padding[1] - 1,
                self.screen_height - self._screen_padding[2] - 1,
            ),
        )
        self.bounds = new_bounds
        top_level_draw_frame = DrawFrame(self, bounds=self.bounds)
        await self.top_level_element.frame(top_level_draw_frame)
        self._needs_redraw = True

    async def start(self) -> None:
        await self.frame()
        self.top_level_element.focus()
        while True:
            key = await await_getch(self.screen)
            self.screen.addstr(0, 0, f"Key: {key}")

            mouse_x, mouse_y, mouse_button = None, None, None
            if key == curses.KEY_RESIZE:
                await self.frame()
            elif key == curses.KEY_MOUSE:
                _, x, y, _, button = curses.getmouse()
                mouse_x, mouse_y, mouse_button = x, y, button
                self.screen.addstr(1, 0, f"Mouse info: {x}, {y} - {button}")
            elif key == ord("q"):  # TODO: change this to check for the ctrc
                break

            if self._active_element is None:
                self.top_level_element.focus()

            await self.top_level_element.update(key, mouse_x, mouse_y, mouse_button)
            if not self._active_element is None:
                # TODO: this is also very janky
                prev_active_element = self._active_element
                await self._active_element.navigation_update(
                    NavigationInput.from_key_code(key)
                )
                if not self._active_element is prev_active_element:
                    self._needs_redraw = True
            await self.top_level_element.execute()
            await self.draw()

    # TODO: Find the active element and focus next or prev
    async def update_navigation(navigation_input: NavigationInput) -> None:
        pass

    def _get_screen_size(self) -> None:
        height, width = self.screen.getmaxyx()
        self._screen_size = (width, height)

    @property
    def screen_width(self) -> int:
        if self._screen_size is None:
            self._get_screen_size()
        return self._screen_size[0]

    @property
    def screen_height(self) -> int:
        if self._screen_size is None:
            self._get_screen_size()
        return self._screen_size[1]

    @property
    def width(self) -> int:
        return (self.bounds[1].x - self.bounds[0].x) + 1

    @property
    def height(self) -> int:
        return (self.bounds[1].y - self.bounds[0].y) + 1


# # TODO: How do we make the distinction clear here? Because this does not handle any of the drawing or focusing that the real one does. Maybe we call it a pane or something different?
# # Maybe these are the real draw frames, and the others are just screen regions?
# class VirtualTUIWindow:
#     window: TUIWindow | "VirtualTUIWindow"
#     bounds: Tuple


# TODO: replace the split with the new util function
# TODO: see, we can do the scrolling draw frame like this, and for the most part that is fine
# The issue is that the height is never going to be the scroll content height, which is an issue for framing
class DrawFrame:
    window: TUIWindow
    bounds: Optional[Tuple[ScreenCoord, ScreenCoord]]
    offset: Optional[Tuple[int, int]]

    _has_drawn: bool = False

    def __init__(
        self,
        window: TUIWindow,
        bounds: Optional[Tuple[ScreenCoord, ScreenCoord]] = None,
        offset: Optional[Tuple[int, int]] = None,
    ):
        self.window = window
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
        self.offset = offset

    def draw(
        self,
        x: int,
        y: int,
        text: str,
        style: int = None,
        overlay: bool = False,
        z: int = 0,
    ):
        if not isinstance(x, int):
            raise ValueError(
                f"`DrawFrame.draw` expected `x` to be type `int`, received type {type(x)}."
            )
        if not isinstance(y, int):
            raise ValueError(
                f"`DrawFrame.draw` expected `y` to be type `int`, received type {type(y)}."
            )
        if not isinstance(text, str):
            raise ValueError(
                f"`DrawFrame.draw` expected `text` to be type `str`, received type {type(text)}."
            )
        if style is not None and not isinstance(style, int):
            raise ValueError(
                f"`DrawFrame.draw` expected `style` to be type `int` or value `None`, received type {type(style)}."
            )
        if not isinstance(overlay, bool):
            raise ValueError(
                f"`DrawFrame.draw` expected `overlay` to be type `bool`, received type {type(text)}."
            )

        if not self.is_drawable:
            return

        adjusted_x = x + self.bounds[0].x
        adjusted_y = y + self.bounds[0].y

        if self.offset is not None:
            adjusted_x += self.offset[0]
            adjusted_y += self.offset[1]

        if not overlay and (
            adjusted_x > self.bounds[1].x or adjusted_y > self.bounds[1].y
        ):
            return

        if adjusted_y > self.window.height + self.window.bounds[0].y:
            return

        # Now, lets trim the text to fit within the bounds
        if (not overlay and (len(text) + adjusted_x > self.bounds[1].x)) or (
            len(text) + adjusted_x > self.window.width
        ):
            text = text[
                : min(
                    (self.bounds[1].x - adjusted_x) + 1,
                    (self.window.width - adjusted_x) + 1,
                )
            ]

        self.window.schedule_draw(
            ScreenCoord(adjusted_x, adjusted_y), text, style, z
        )  # TODO: figure out if we want to make everything use screen cords.

    def pad(self, horizontal: int, vertical: int) -> "DrawFrame":
        if (
            not self.is_drawable
            or self.width <= 2 * horizontal
            or self.height <= 2 * vertical
        ):
            return DrawFrame(self.window, None)
        return DrawFrame(
            self.window,
            (
                ScreenCoord(self.bounds[0].x + horizontal, self.bounds[0].y + vertical),
                ScreenCoord(self.bounds[1].x - horizontal, self.bounds[1].y - vertical),
            ),
        )

    def subframe(self, bounds: Tuple[ScreenCoord, ScreenCoord]) -> "DrawFrame":
        if not self.is_drawable:
            return DrawFrame(self.window, None)
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
            return DrawFrame(self.window, None)

        relative_bounds = (
            ScreenCoord(bounds[0].x + self.bounds[0].x, bounds[0].y + self.bounds[0].y),
            ScreenCoord(bounds[1].x + self.bounds[0].x, bounds[1].y + self.bounds[0].y),
        )
        return DrawFrame(self.window, relative_bounds)

    def split(
        self, splits: int | List[int | float | None], orientation: Orientation
    ) -> List["DrawFrame"]:
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
        if self.bounds is None:
            if isinstance(splits, int):
                return [DrawFrame(self.window) for _ in range(splits)]
            elif isinstance(splits, Sequence):
                return [DrawFrame(self.window) for _ in splits]
            else:
                raise ValueError(
                    f"`DrawFrame.split` expected `splits` type of int or sequence, received type of {type(splits)} instead."
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
        elif isinstance(splits, Sequence):
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
                f"`DrawFrame.split` expected `splits` type of int or sequence, received type of {type(splits)} instead."
            )

        # Now, we will create the subframes
        subframes = []
        match orientation:
            case Orientation.HORIZONTAL:
                x = self.bounds[0].x
                for length in lengths:
                    if length is None:
                        subframes.append(DrawFrame(self.window, None))
                    else:
                        subframes.append(
                            DrawFrame(
                                self.window,
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
                        subframes.append(DrawFrame(self.window, None))
                    else:
                        subframes.append(
                            DrawFrame(
                                self.window,
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

    @classmethod
    def from_screen(cls, screen: "curses._CursesWindow") -> "DrawFrame":
        height, width = screen.getmaxyx()
        bounds = (ScreenCoord(0, 0), ScreenCoord(width - 1, height - 1))
        return DrawFrame(screen, bounds)

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
        return self.bounds is not None and self.window is not None

    def __repr__(self) -> str:
        return f"DrawFrame(screen={self.screen}, bounds={self.bounds})"


class TUIElement:
    IS_INTERACTABLE: bool = (
        False  # TODO: maybe interactability can be done by checking the update and navigation update functions
    )

    draw_frame: DrawFrame
    window: TUIWindow
    children: Optional[List["TUIElement"]] = None
    parent: Optional["TUIElement"] = None

    _is_focusable = None
    _focusable_children = None

    def __init__(self) -> None:
        self.draw_frame = DrawFrame(None)
        self.window = None

    # What things invalidate the drawn state?
    # - Focusing an element
    # - Internal logic in update
    # - Reframing

    # TODO: frame and draw probably don't need to be async

    def get_size(
        self, width_constraint: int | None = None, height_constraint: int | None = None
    ) -> Tuple[int, int]:
        raise NotImplementedError("")  # TODO: write this error

    async def frame(self, draw_frame: DrawFrame) -> None:
        """Sets the location for the object to be drawn in the view"""
        self.draw_frame = draw_frame
        self.window = draw_frame.window  # TODO: is this necessary?

    async def navigation_update(self, navigation_input: NavigationInput) -> None:
        """Is called on the active element when navigation input is received."""
        if navigation_input is NavigationInput.NONE:
            return

        if self.parent is not None:
            await self.parent.navigation_update(navigation_input)

    async def update(
        self, event_code: int, mouse_x: int, mouse_y: int, mouse_button: int
    ) -> None:
        """Updates the object based on the user input. Prefer to use navigation_update."""
        pass

    async def execute(self) -> None:
        """Execute any actions that the object needs to perform"""
        pass

    async def draw(self) -> None:
        """Draw the object to the screen"""
        raise NotImplementedError("`TUIElement`s must implement a draw method")

    # TODO: change this to be automatic, so that implementers of TUIElement do
    # not need to remember to do it. (Use the attribute assignment to check if we are adding
    # a TUIElement as an attribute.)
    # Wait... maybe not, the TUIElement in question could be a parent...
    def add_child(self, child: "TUIElement") -> None:
        if self.children is None:
            self.children = []

        if child in self.children:
            raise ValueError(
                f"`TUIElement` received a child which is already a child of this object."
            )

        self.children.append(child)
        child.parent = self

        if child.is_focusable:
            self._is_focusable = True

    def remove_child(self, child: "TUIElement") -> None:
        try:
            self.children.remove(child)
            self._is_focusable = None
        except ValueError:
            pass

        child.parent = None

        if len(self.children) == 0:
            self.children = None

    @property
    def is_focusable(self) -> bool:
        if self._is_focusable is None:
            if self.IS_INTERACTABLE and self.draw_frame.is_drawable:
                self._is_focusable = True
                return True
            if self.children is not None:
                for child in self.children:
                    if child.is_focusable:
                        self._is_focusable = True
                        return True
            self._is_focusable = False
        return self._is_focusable

    @property
    def focusable_children(self) -> List["TUIElement"]:
        if self.children is None:
            return None
        if self._focusable_children is None:
            self._focusable_children = []
            for child in self.children:
                if child.is_focusable:
                    self._focusable_children.append(child)
        return self._focusable_children

    # TODO: why is this not a property if other things are?
    def is_focused(self) -> bool:
        if self.window is None:
            return False
        return (
            self in self.window._focused_elements
        )  # TODO: avoid accessing the private members of TUIWindow

    def is_active(self) -> bool:
        if self.window is None:
            return False
        return self is self.window._active_element

    def focus_next(self) -> None:
        if self.is_focusable and self.children is not None:
            # Find the currently focused child
            currently_focused_child_index = -1
            for index, child in enumerate(self.children):
                if child.is_focused():
                    currently_focused_child_index = index
                    break

            # Find the next focusable child
            next_focusable_child = None
            for child_index in range(
                currently_focused_child_index + 1, len(self.children)
            ):
                child = self.children[child_index]
                if child.is_focusable:
                    next_focusable_child = child
                    break

            if next_focusable_child is None:
                if not self.parent is None:
                    self.parent.focus_next()
            else:
                child.focus()
        elif self.parent is not None:
            self.parent.focus_next()

    def focus_prev(self) -> None:
        if self.is_focusable and self.children is not None:
            # Find the currently focused child
            currently_focused_child_index = len(self.children)
            for index, child in enumerate(self.children):
                if child.is_focused():
                    currently_focused_child_index = index
                    break

            # Find the next focusable child
            next_focusable_child = None
            for child_index in range(currently_focused_child_index - 1, -1, -1):
                child = self.children[child_index]
                if child.is_focusable:
                    next_focusable_child = child
                    break

            if next_focusable_child is None:
                if not self.parent is None:
                    self.parent.focus_prev()
            else:
                child.focus()
        elif self.parent is not None:
            self.parent.focus_prev()

    def focus(self) -> None:
        if self.window is None:
            return

        # TODO: fix this so that Window is in charge of its private members
        if not self.is_focusable:
            if self.parent is not None:
                self.parent.focus_next()

        if self.children is not None and len(self.children) > 0:
            for child in self.children:
                if child.is_focusable:
                    return child.focus()

        self.window._focused_elements.clear()
        parent = self.parent
        while parent is not None:
            if parent in self.window._focused_elements:
                break
            self.window._focused_elements.append(parent)
            parent = parent.parent

        self.window._active_element = self
        self.window._focused_elements.append(self)

    def __setattr__(self, name: str, value: Any) -> None:
        # TODO: this is kind of janky. Seems like there should be a nicer way...
        if (
            not name == "draw_frame"
            and self.draw_frame.window is not None
            and not getattr(self, name) == value
        ):
            self.draw_frame.window._needs_redraw = True
        super().__setattr__(name, value)
        if name == "draw_frame":
            if not self.draw_frame.is_drawable:
                self._is_focusable = False
                self._focusable_children = []
            else:
                self._is_focusable = None
                self._focusable_children = None

            parent = self.parent
            while parent is not None:
                parent._is_focusable = None
                parent._focusable_children = None
                parent = parent.parent
