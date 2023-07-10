#!/usr/bin/env python3

"""poc2_textual.py - Demonstrate use of Textual and our base widget
"""

import asyncio

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer

from demo_helpers import OrderNumber, new_order, pretty_order
from demo_helpers import DemoWidget


class OurWidget(DemoWidget):

    async def background_task(self):
        while True:
            await self.make_order()

    async def make_order(self):
        order = await new_order()

        order['count'] = count = await OrderNumber.get_next_order_number()

        self.add_line(f'Order {count}: {pretty_order(order)}')

    async def on_mount(self):
        asyncio.create_task(self.background_task())


class MyGridApp(App):

    BINDINGS = [
        ("q", "quit()", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield OurWidget('Widget 1')
                yield OurWidget('Widget 2')
            with Vertical():
                yield OurWidget('Widget 3')
                # And just the bare DemoWidget, to show it does *something*
                yield DemoWidget('DemoWidget')
            yield Footer()


def main():
    """A demonstration of our Textual widget
    """

    app = MyGridApp()
    app.run()


if __name__ == '__main__':
    main()
