from typing import Tuple

from tuiform.element import TUIElement, DrawFrame
from tuiform.enums import Orientation
from tuiform.stack import Stack
from tuiform.fill import Fill


class ScrollBar(TUIElement):
    IS_INTERACTABLE = True

    orientation: Orientation
    veiwable_range: Tuple[float, float]
    hovered: bool

    def __init__(self, orientation: Orientation) -> None:
        super().__init__()
        self.orientation = orientation


# TODO: how do we make sure that we scroll to the active element?
class ScrollPanel(TUIElement):
    orientation: Orientation
    current_scroll_position: int
    content: TUIElement
    scroll_bar: ScrollBar
    content_size: int

    def __init__(self, content: TUIElement, orientation: Orientation) -> None:
        super().__init__()
        match orientation:
            case Orientation.HORIZONTAL:
                stack_orientation = Orientation.VERTICAL
            case Orientation.VERTICAL:
                stack_orientation = Orientation.HORIZONTAL

        self.orientation = orientation
        scroll_bar = ScrollBar(orientation=orientation)
        stack = Stack(
            elements=[content, Fill(" "), scroll_bar],
            splits=[None, 1, 1],
            orientation=stack_orientation,
        )
        self.content = content
        self.scroll_bar = scroll_bar
        self.add_child(stack)

    def get_size(
        self, width_constraint: int | None = None, height_constraint: int | None = None
    ) -> Tuple[int]:
        pass  # TODO

    # TODO: moving the scroll bar should not need reframing
    async def frame(self, draw_frame: DrawFrame) -> None:
        match self.orientation:
            case Orientation.HORIZONTAL:
                self.content_size = self.content.get_size(
                    height_constraint=draw_frame.height
                )
            case Orientation.VERTICAL:
                self.content_size = self.content.get_size(
                    width_constraint=draw_frame.width
                )

        # TODO: create the virtual thingymabob
