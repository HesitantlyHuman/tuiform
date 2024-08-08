from typing import List, Tuple, Optional

from tuiform.utils.split import split_int
from tuiform.fill import Fill
from tuiform.enums import NavigationInput, Orientation
from tuiform.element import TUIElement, DrawFrame


class Stack(TUIElement):
    orientation: Orientation
    element_padding: int
    divider: str

    def __init__(
        self,
        elements: List[TUIElement],
        orientation: Orientation,
        splits: int | List[int | float | None] | None = None,
        element_padding: int = 0,
        element_padding_style: int = 0,
        divider: str | None = None,
        divider_style: int = 0,
    ) -> None:
        super().__init__()
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
            for i, (element, split) in enumerate(zip(elements, self.splits)):
                new_elements.append(element)
                new_splits.append(split)
                if i < len(elements) - 1:
                    new_elements.append(Fill(divider, divider_style))
                    new_splits.append(1)

            elements = new_elements
            self.splits = new_splits

        if element_padding > 0:
            # Interleave padding
            new_elements = []
            new_splits = []
            for i, (element, split) in enumerate(zip(elements, self.splits)):
                new_elements.append(element)
                new_splits.append(split)
                if i < len(elements) - 1:
                    new_elements.append(Fill(" ", element_padding_style))
                    new_splits.append(element_padding)

            elements = new_elements
            self.splits = new_splits

        for element in elements:
            self.add_child(element)

    def get_size(
        self, width_constraint: int | None = None, height_constraint: int | None = None
    ) -> Tuple[int, int]:
        if height_constraint is not None and self.orientation is Orientation.VERTICAL:
            child_height_constraints = split_int(height_constraint, self.splits)
        elif height_constraint is not None:
            child_height_constraints = [height_constraint for _ in self.splits]
        else:
            child_height_constraints = [None for _ in self.splits]

        if width_constraint is not None and self.orientation is Orientation.HORIZONTAL:
            child_width_constraints = split_int(width_constraint, self.splits)
        elif width_constraint is not None:
            child_width_constraints = [width_constraint for _ in self.splits]
        else:
            child_width_constraints = [None for _ in self.splits]

        width, height = 0, 0
        for i, child in enumerate(self.children):
            child_width, child_height = child.get_size(
                width_constraint=child_width_constraints[i],
                height_constraint=child_height_constraints[i],
            )
            if self.orientation == Orientation.VERTICAL:
                width = max(width, child_width)
                height += child_height
            else:
                width += child_width
                height = max(height, child_height)
        return width, height

    async def frame(self, draw_frame: DrawFrame) -> None:
        self.draw_frame = draw_frame
        subframes = self.draw_frame.split(self.splits, self.orientation)
        for i, child in enumerate(self.children):
            await child.frame(subframes[i])

    async def navigation_update(self, navigation_input: NavigationInput) -> None:
        if navigation_input is NavigationInput.NONE:
            return

        if len(self.children) == 0:
            if self.parent is not None:
                await self.parent.navigation_update(navigation_input)
            return

        with open("logging.txt", "a") as f:
            print(
                f"Stack with orientation {self.orientation} received navigation input {navigation_input}",
                file=f,
            )

        match (self.orientation, navigation_input):
            case (Orientation.HORIZONTAL, NavigationInput.RIGHT) | (
                Orientation.VERTICAL,
                NavigationInput.DOWN,
            ):
                with open("logging.txt", "a") as f:
                    print(
                        f"Checking if focus next",
                        file=f,
                    )
                if not self.focusable_children[-1].is_focused():
                    with open("logging.txt", "a") as f:
                        print(
                            f"Focusing next",
                            file=f,
                        )
                    self.focus_next()
                    return
            case (Orientation.HORIZONTAL, NavigationInput.LEFT) | (
                Orientation.VERTICAL,
                NavigationInput.UP,
            ):
                if not self.focusable_children[0].is_focused():
                    self.focus_prev()
                    return
            case (_, NavigationInput.FIRST):
                if not self.focusable_children[0].is_focused():
                    self.focus()
                    return
            case (_, NavigationInput.LAST):  # TODO: fix this
                if not self.focusable_children[-1].is_focused():
                    self.focus()
                    return
            case (_, NavigationInput.NEXT):
                if self.parent is not None:
                    self.parent.focus_next()
                    return
            case (_, NavigationInput.PREV):
                if self.parent is not None:
                    self.parent.focus_prev()
                    return

        if self.parent is not None:
            await self.parent.navigation_update(navigation_input)

    async def update(
        self, event_code: int, mouse_x: int, mouse_y: int, mouse_button: int
    ) -> None:
        for child in self.children:
            await child.update(event_code, mouse_x, mouse_y, mouse_button)

    async def execute(self) -> None:
        for child in self.children:
            await child.execute()

    async def draw(self) -> None:
        for child in self.children:
            if child.draw_frame.is_drawable:
                await child.draw()

    def __repr__(self) -> str:
        return f"Stack(elements={self.children}, orientation={self.orientation}, splits={self.splits}, element_padding={self.element_padding}, divider={self.divider})"
