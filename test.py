import asyncio

import curses

from tuiform.element import TUIWindow
from tuiform.manager import tui_session
from tuiform.clipboard import CopyableObject
from tuiform.text import DataValue, Text
from tuiform.button import Button
from tuiform.stack import Stack
from tuiform.panel import Panel
from tuiform.enums import Orientation

# How I would like it to work
# with TUIForm() as form:
#     log_id_entry = TextEntry("Log ID")
#     log_id_button = Button(None, "Search")
#     log_entry_panel = Panel(
#         Stack([log_id_entry, log_id_button], orientation=Orientation.VERTICAL)
#     )
#     form.render(log_entry_panel)

with tui_session() as screen:
    button_one = Button(None, "One")
    button_one.bound_function = button_one.select

    bottom_button_stack = Stack(
        [
            button_one,
            Button(None, "Two"),
            Button(None, "Three"),
            Button(None, "Four"),
            Button(None, "Five"),
            Button(None, "Six"),
            Button(None, "Seven"),
            Button(None, "Eight"),
            Button(None, "Nine"),
            Button(None, "Ten"),
        ],
        Orientation.HORIZONTAL,
        element_padding=1,
        divider="│",
    )

    button_four = Button(None, "Button Four")

    text_block = Text(
        "Here is some text¶\nthat we would like to have wrap very nicely and not exceed our cute little text box area.\nAnd the text, just does not stop. Just goes on and on and on, and there might even be some tremendously exceptionally long words occassionally",
        new_line_character_style=curses.color_pair(0) | curses.A_DIM,
    )
    value_example = DataValue("Active Log", "generate_sums")
    copyable_text_block = CopyableObject(
        content=text_block, text_to_copy=text_block.text
    )
    content_stack = Stack(
        [copyable_text_block, value_example],
        orientation=Orientation.VERTICAL,
    )
    button_panel = Panel(
        content_stack,
        footer=bottom_button_stack,
        header=button_four,
    )
    other_text_block = Text(
        "This is some other text that will reside on the right side of the screen. sodfimeslietnsleijtlsidflsiefjseflseijflsiejf sljsielfjsliefjlsiejflsijelfijsliejflsijeflisjelf sleifjlsiejflisjelfijslfdlskvnlsd"
    )
    other_text_block_panel = Panel(other_text_block, footer=Button(None, "A button"))

    side_by_side = Stack(
        [button_panel, other_text_block_panel],
        splits=[None, 35],
        orientation=Orientation.HORIZONTAL,
    )
    window = TUIWindow(screen, side_by_side)

    asyncio.run(window.start())
