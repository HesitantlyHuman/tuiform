from os import environ

import curses

class tui_session:
    _screen: "curses._CursesWindow"
    _prev_env_term: str

    def __init__(self) -> None:
        pass

    def __enter__(self) -> "curses._CursesWindow":
        self._prev_env_term = environ["TERM"]
        # TODO: Check if we are in a terminal that supports the XTERM API
        # before doing this
        environ["TERM"] = "xterm-1003"
        self._screen = curses.initscr()

        # STYLING (FUCK ME)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(0, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)

        # Mouse and interactivity settings
        self._screen.keypad(1)
        self._screen.nodelay(1)
        curses.curs_set(0)
        curses.raw()
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        curses.mouseinterval(5)
        print("\033[?1003h")  # enable mouse tracking with the XTERM API
        # https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Mouse-Tracking
        curses.flushinp()
        curses.noecho()
        self._screen.clear()
        return self._screen

    def __exit__(self, exc_type, exc_val, exc_tb):
        environ["TERM"] = self._prev_env_term
        print("\033[?1003l", end="")  # disable mouse tracking with the XTERM API
        curses.endwin()
        curses.flushinp()