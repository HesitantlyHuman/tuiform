from enum import Enum

import curses


class Orientation(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class NavigationInput(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    NEXT = "next"
    PREV = "prev"
    FIRST = "first"
    LAST = "last"
    INTERACT = "interact"
    EXIT = "exit"
    QUIT = "quit"
    NONE = "none"

    @classmethod
    def from_key_code(cls, key_code: int) -> "NavigationInput":
        match key_code:
            case curses.KEY_MOUSE:
                return NavigationInput.NONE
            case curses.KEY_UP | 119:
                return NavigationInput.UP
            case curses.KEY_DOWN | 115:
                return NavigationInput.DOWN
            case curses.KEY_RIGHT | 100:
                return NavigationInput.RIGHT
            case curses.KEY_LEFT | 97:
                return NavigationInput.LEFT
            case 9:
                return NavigationInput.NEXT
            case 353:
                return NavigationInput.PREV
            case 337:
                return NavigationInput.FIRST
            case 336:
                return NavigationInput.LAST
            case 10:
                return NavigationInput.INTERACT
            case 27:
                return NavigationInput.EXIT
            case 17:
                return NavigationInput.QUIT
            case _:
                return NavigationInput.NONE
