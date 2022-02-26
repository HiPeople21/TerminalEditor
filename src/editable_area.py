from typing import List
import aiofile
import asyncio

from rich.containers import Lines
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from textual.reactive import Reactive
from textual.widget import Widget
from textual.geometry import Size

from custom_scroll_view import CustomScrollView

OFFSET_X = 8
OFFSET_Y = 1
PADDING = 8

loop = asyncio.get_event_loop()


async def write(text):
    async with aiofile.async_open('log', 'a') as f:
        await f.write(text)


class EditableArea(Widget):
    """
    A class that contains the text which can be modified
    """
    """
    TODO: Cursor movement with line wrapping, Move view to cursor if cursor off screen
    """
    text = Reactive('')
    has_focus = Reactive(False)
    cursor_pos = Reactive([0, 0])
    cursor = Reactive('')
    cursor_window_pos_y = 0
    cursor_active = True

    def __init__(self, text: str, file_name: str) -> None:

        super().__init__()

        self.text = text
        self.view: CustomScrollView = self.app.body
        self.file_name = file_name
        self.syntax = Syntax(
            '',
            lexer=Syntax.guess_lexer(
                self.file_name, self.text
            ),
            theme="monokai",
        )
        self.sep = self.syntax.highlight('\n')
        self.space = self.syntax.highlight(' ')
        if self.text:
            if self.text[-1] == '\n':
                self.text += '\n'

    async def resize_view(self):
        await self.view.update(self.view.window.widget, home=False)

    async def on_mount(self) -> None:
        self.set_interval(1, self.handle_cursor)

    def handle_cursor(self) -> None:
        if self.has_focus:

            self.cursor = '' if self.cursor else '|'
            asyncio.gather(self.resize_view())
        self.refresh(layout=True)

    def render(self) -> Panel:

        rendered_grid = Table.grid(expand=False)
        rendered_grid.add_column()
        rendered_grid.add_column()
        text: Lines = self.syntax.highlight(self.text).split('\n')

        # prev_text = self.sep.join(text[:self.cursor_pos[1]])
        # post_text = self.sep.join(text[self.cursor_pos[1] + 1:])
        # loop = asyncio.get_event_loop()
        # loop.create_task(write(str(post_text)))
        # if prev_text:
        #     prev_text += self.sep
        # if post_text:
        #     post_text = self.sep + post_text

        # rendered_text: Text = (
        #     prev_text +
        #     text[self.cursor_pos[1]][:self.cursor_pos[0]] +
        #     Text(self.cursor) +
        #     text[self.cursor_pos[1]][self.cursor_pos[0]:] +
        #     post_text
        # )

        _, number_style, _ = self.syntax._get_number_styles(
            self.app.console)  # background_style, number_style, highlight_number_style
        numbers_column_width = len(str(1 + self.text.count("\n"))) + 2
        for index, line in enumerate(text, 1):
            if index == self.cursor_pos[1] + 1:
                line = line[:self.cursor_pos[0]] + \
                    self.cursor + line[self.cursor_pos[0]:]
            line_no = Text(str(index).rjust(
                numbers_column_width) + " ", style=number_style)

            rendered_grid.add_row(
                line_no, line)

        return Panel(
            rendered_grid
        )

        # text: List[str] = self.text.splitlines()
        # rendered_text: str = ''

        # for index, line in enumerate(text):
        #     if index != len(text) - 1:
        #         suffix = '\n'
        #     else:
        #         suffix = ''
        #     if index == self.cursor_pos[1]:
        #         if line == '\n':
        #             rendered_text += self.cursor + line
        #             continue
        #         rendered_text += (
        #             line[:self.cursor_pos[0]] +
        #             self.cursor + line[self.cursor_pos[0]:] + suffix
        #         )
        #         continue
        #     rendered_text += line + suffix
        # return Panel(Syntax(
        #     rendered_text,
        #     Syntax.guess_lexer(self.file_name, self.text),
        #     line_numbers=True,
        #     word_wrap=True,
        #     indent_guides=True,
        #     theme="monokai",

        # ))

    async def on_key(self, event) -> None:

        if not self.has_focus:
            return

        text: List[str] = self.text.splitlines()
        if text[-1] == '':
            trailing = True
        else:
            trailing = False
        self.cursor = '|'

        # Handles backspace
        if event.key == 'ctrl+h':
            if self.cursor_pos[0] > len(text[self.cursor_pos[1]]):
                self.cursor_pos[0] = len(text[self.cursor_pos[1]])

            if trailing and self.cursor_pos[1] != len(text) - 1:
                text.append('')
            if self.cursor_pos[0] > 0:
                prev_text = '\n'.join(text[:self.cursor_pos[1]])
                if prev_text:
                    prev_text += '\n'
                self.text = (
                    prev_text +
                    text[self.cursor_pos[1]][: self.cursor_pos[0] - 1] +
                    text[self.cursor_pos[1]][self.cursor_pos[0]:] +
                    '\n' +
                    '\n'.join(text[self.cursor_pos[1] + 1:])
                )

                self.cursor_pos[0] -= 1
            else:
                # Handles backspace at start of line
                self.text = (
                    '\n'.join(text[:self.cursor_pos[1]]) +
                    text[self.cursor_pos[1]][self.cursor_pos[0]:] +
                    '\n' +
                    '\n'.join(text[self.cursor_pos[1] + 1:])
                )
                if self.cursor_pos[1] > 0:
                    self.cursor_pos[1] -= 1
                    self.cursor_window_pos_y -= 1
                    self.cursor_pos[0] = len(text[self.cursor_pos[1]])
                if self.cursor_window_pos_y < 0:
                    await self.view.up()
                    self.cursor_window_pos_y += 1

            if self.cursor_window_pos_y >= self.view.vscroll.window_size - 2:
                await self.view.down(self.cursor_pos[1] - self.view.y)
            if self.cursor_window_pos_y < 0:
                await self.view.up(self.view.y - self.cursor_pos[1])

            await self.resize_view()

        # Handles tab
        elif event.key == 'ctrl+i':
            if self.cursor_pos[0] > len(text[self.cursor_pos[1]]):
                self.cursor_pos[0] = len(text[self.cursor_pos[1]])
            prev_text = '\n'.join(text[:self.cursor_pos[1]])
            if prev_text:
                prev_text += '\n'
            self.text = (
                prev_text +
                text[self.cursor_pos[1]][: self.cursor_pos[0]] +
                '\t' +
                text[self.cursor_pos[1]][self.cursor_pos[0]:] +
                '\n' +
                '\n'.join(text[self.cursor_pos[1] + 1:])
            )
            self.cursor_pos[0] += 1
            if trailing and self.cursor_pos[1] != len(text) - 1:
                self.text += '\n'
            if len(text[self.cursor_pos[1]]) > self.view.virtual_size.width:
                await self.resize_view()

        # Handles enter
        elif event.key == 'enter':
            if self.cursor_pos[0] > len(text[self.cursor_pos[1]]):
                self.cursor_pos[0] = len(text[self.cursor_pos[1]])
            prev_text = '\n'.join(text[:self.cursor_pos[1]])
            if prev_text:
                prev_text += '\n'
            self.text = (
                prev_text +
                text[self.cursor_pos[1]][: self.cursor_pos[0]] +
                '\n' +
                text[self.cursor_pos[1]][self.cursor_pos[0]:] +
                '\n' +
                '\n'.join(text[self.cursor_pos[1] + 1:])
            )
            if trailing and self.cursor_pos[1] != len(text) - 1:
                self.text += '\n'
            self.cursor_pos[0] = 0
            self.cursor_pos[1] += 1
            self.cursor_window_pos_y += 1
            if self.cursor_window_pos_y >= self.view.vscroll.window_size - 2:
                await self.view.down()
                self.cursor_window_pos_y -= 1

        # Handles left arrow
        elif event.key == 'left':

            if self.cursor_pos[0] > 0:
                self.cursor_pos[0] -= 1

            elif self.cursor_pos[1] > 0:
                self.cursor_pos[1] -= 1
                self.cursor_window_pos_y -= 1
                self.cursor_pos[0] = len(text[self.cursor_pos[1]])

        # Handles right arrow
        elif event.key == 'right':

            if self.cursor_pos[0] <= len(text[self.cursor_pos[1]]) - 1:
                self.cursor_pos[0] += 1

            elif self.cursor_pos[1] < len(text) - 1:
                self.cursor_pos[1] += 1
                self.cursor_window_pos_y += 1
                self.cursor_pos[0] = 0

        # Handles up arrow
        elif event.key == 'up':

            if self.cursor_pos[1] > 0:
                self.cursor_pos[1] -= 1
                self.cursor_window_pos_y -= 1
            else:
                self.cursor_pos[0] = 0
            if self.cursor_window_pos_y < 0:
                await self.view.up()
                self.cursor_window_pos_y += 1

        # Handles down arrow
        elif event.key == 'down':

            if self.cursor_pos[1] < len(text) - 1:
                self.cursor_pos[1] += 1
                self.cursor_window_pos_y += 1

            else:
                self.cursor_pos[0] = len(text[self.cursor_pos[1]])

            if self.cursor_window_pos_y >= self.view.vscroll.window_size - 2:
                await self.view.down()
                self.cursor_window_pos_y -= 1

        # Saves to file
        elif event.key == 'ctrl+s':
            async with aiofile.async_open(self.file_name, 'w') as f:
                await f.write(self.text)

        # Handles any other character
        elif not event.key.startswith('ctrl'):
            prev_text = '\n'.join(text[:self.cursor_pos[1]])
            if prev_text:
                prev_text += '\n'
            if self.cursor_pos[0] > len(text[self.cursor_pos[1]]):
                self.cursor_pos[0] = len(text[self.cursor_pos[1]])
            self.text = (
                prev_text +
                text[self.cursor_pos[1]][: self.cursor_pos[0]] +
                event.key +
                text[self.cursor_pos[1]][self.cursor_pos[0]:] +
                '\n' +
                '\n'.join(text[self.cursor_pos[1] + 1:])
            )
            self.cursor_pos[0] += 1
            if trailing and self.cursor_pos[1] != len(text) - 1:
                self.text += '\n'

            if len(text[self.cursor_pos[1]]) > self.view.virtual_size.width:
                await self.resize_view()

        self.refresh(layout=True)

    async def on_focus(self, event) -> None:
        self.has_focus = True
        self.cursor_active = True

    async def on_blur(self, event) -> None:
        self.has_focus = False
        self.cursor = ''
        self.cursor_active - False

    async def on_click(self, event) -> None:
        text: List[str] = self.text.splitlines()
        long_lines: List[str] = list(filter(lambda line: len(line) >
                                            self.view.hscroll.window_size - PADDING, text[int(self.view.y):event.y-1]))
        # Cursor Y position
        if event.y - OFFSET_Y >= len(text):
            self.cursor_pos[1] = len(text) - 1
            self.cursor_window_pos_y = self.view.vscroll.window_size - OFFSET_Y
        else:
            self.cursor_pos[1] = event.y - OFFSET_Y  # - len(long_lines)
            self.cursor_window_pos_y = (
                event.screen_y -
                OFFSET_Y -
                3  # -
                # len(long_lines)
            )

        # Cursor X position
        if event.x < OFFSET_X:
            self.cursor_pos[0] = 0
        elif event.x - OFFSET_X > len(text[self.cursor_pos[1]]):
            self.cursor_pos[0] = len(text[self.cursor_pos[1]])
        else:
            # if len(text[self.cursor_pos[1]]) > self.view.hscroll.window_size - PADDING:
            #     extra_offset = (
            #         len(long_lines) * (self.view.hscroll.window_size - 11)
            #     )
            # else:
            #     extra_offset = 0
            self.cursor_pos[0] = event.x - OFFSET_X  # + extra_offset

        # with open('log', 'a') as f:
        #     f.write(str(event) + '\n')
