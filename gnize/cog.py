"""
# Purpose

This module implements `cog`.  It's short for cognize, which is what happens in
your mind the first time that you see a new thing.  If you see that thing a
second time, you might recognize it--which is a separate sort of thing. That's
what the `recog` command line utility is for.

Presumably, the thing you want to cognize isn't alone.  Maybe it is bundled
with ads or other malware.  Maybe it it split by a pagniation boundary.
Whatevever the extra data is, we'll call the whole thing "noise" and whatever
subset you want to cognize now (and recognize later) we'll call "signal".

`cog` will create artifacts that you (or someone else) can use to identify the
signal later on--even if it is surrounded by (or lightly corruptedby ) by
different noise.

There are two components to this:

- fingerprints (stored in ~/.gnize/fingerprints.db)
- canvasses (stored in ~/.gnize/canvasses)

The fingerprints are generated by features.py, they're a list of hashes ordered
by their appearence in the noise.  Each time you cog(nize) you create a single
canvas, which is a list of strings which together make up the signal.
Canvasses aren't a single string because the signal as found in the noise might
have noise in ths middle.  For instance, here's some noise:

    asdfsdaf45646546This is the song that never ends yes it goes on
    and on my friends some people started signing it __^%%$^%k not
    knowning what it was and they'll continue singing it forever
    just because assxccjjasoadflkasdflkjsdlj.

The cognizer has some freedom in how they extract this signal, but a reasonable
choice would be:

    ["This is the song that never ends yes it goes on and on my friends some people started signing it ",
     "not knowning what it was and they'll continue singing it forever just because"]

A recognizer of the "same" signal, couched in different noise might break it up
differently, and that might corrupt some of the fingerprints that they
calculate, but unless their corruption is severe, they're likely to reidentify
enough of the same fingerprints that they can find the original canvas (and
whatever annotations go with it).

The possibility of having several canvasses for what ammounts to the "same"
signal, and building consensus on one to treat as cannonical, is a separate
problem.  For now we just want create canvasses and query for them by fingerprints.
"""

from re import sub
import sys
import pty
from dataclasses import dataclass
from textwrap import dedent
from pprint import pformat
from copy import deepcopy
from typing import List, Tuple

from prompt_toolkit import Application
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.widgets import Frame, HorizontalLine, VerticalLine

from gnize import dotdir, features

import IPython

from minineedle import NeedlemanWunsch, ScoreMatrix
from minineedle.core import Gap
from rich.console import Console

@dataclass
class Interval:
    "a subintval of the given noise (might be a subcanvas, might be a gap)"

    start: int
    end: int
    content: str

    def inside(self, it):
        return self.start < it < self.end

    def outside(self, it):
        return it < self.start or it > self.end

    def summary(self, index, cursor_start=0, cursor_stop=None):

        if cursor_stop is None:
            if self.inside(cursor_start):
                prefix = "(*)"
            else:
                prefix = None
        else:
            if self.inside(cursor_start) and self.outside(cursor_stop):
                prefix = "(*>"
            elif self.outside(cursor_start) and self.inside(cursor_stop):
                prefix = "<*)"
            elif self.inside(cursor_start) and self.inside(cursor_stop):
                prefix = "(*)"
            else:
                prefix = None

        # if the cursor isn't inside the subcanvas, display the subcanvas index
        if not prefix:
            prefix = f"{index}"

        flat = " ".join(self.content.split())
        width = len(flat)
        if width > 16:
            start = flat[:8]
            end = flat[-8:]
            connector = ".."
        elif width > 8:
            midpoint = int(width / 2)
            start = flat[:midpoint]
            end = flat[midpoint:]
            connector = ".."
        else:
            start = flat
            end = ""
            connector = ""

        return prefix + f"{start}{connector}{end}"


def align_and_fix(_signal, _noise) -> Tuple[List[Interval], List[Interval], str]:

    signal = deepcopy(_signal)
    noise = deepcopy(_noise)

    def align() -> List[Tuple]:

        pair = NeedlemanWunsch(noise, signal)
        pair.smatrix = ScoreMatrix(match=1, miss=0, gap=-1)
        pair.align()
        c, s = pair.get_aligned_sequences()
        return list(zip(c, s))

    # overwrite transcription errors with values from canvas
    c_idx = -1
    s_idx = -1
    for c, s in align():
        if type(c) is Gap:
            # no data inssertion allowed at this step
            # overwrite signal from canvas at this location
            # this means that editor actions that would create new data
            # can only widen the signal
            signal[s_idx] = c
        else:
            c_idx += 1

        if type(s) is Gap:
            # signal is allowed to be less than canvas, do nothing
            # this lets editor actions that would delete data work as expected
            pass
        else:
            s_idx += 1

    signals = []
    gaps = []
    outer_buffer = ""
    buffer = ""
    buffer_is_signal = False

    def struck(text):
        console = Console()
        with console.capture() as capture:
            console.print(f"[strike]{text}[/strike]", end='')
        return capture.get()

    # categorize characters on signal/gap transition
    for i, (c, s) in enumerate(align()):

        # first past should have eliminated any additions
        if type(c) is Gap:
            raise ValueError("signal char {s}(#{s_idx}) cannot be aligned to canvas")

        # interpret deletions as gaps
        if type(s) is Gap:
            if buffer_is_signal:
                signals.append(Interval(i - len(buffer), i, buffer))
                outer_buffer += buffer
                buffer = c
                buffer_is_signal = False
            else:
                buffer += c
        else:
            if not buffer_is_signal:
                gaps.append(Interval(i - len(buffer), i, buffer))
                outer_buffer += struck(buffer)
                buffer = s
                buffer_is_signal = True
            else:
                buffer += s

    # capture remaining characters
    if buffer_is_signal:
        signals.append(Interval(i - len(buffer), i, buffer))
        outer_buffer += buffer
    else:
        gaps.append(Interval(i - len(buffer), i, buffer))
        outer_buffer += struck(buffer)


    return signals, gaps, outer_buffer


subcanvasses = []
gaps = []


def update(event):
    global subcanvasses
    global subcanvasses_display
    global gaps
    global gaps_display
    global debug_display

    subcanvasses, gaps, fixed_buffer = align_and_fix(noise, buffer.text)
    buffer.text = fixed_buffer

    if event.selection_state:
        selected_from = min(
            event._Buffer__cursor_position,
            event.selection_state.original_cursor_position,
        )
        selected_to = max(
            event._Buffer__cursor_position,
            event.selection_state.original_cursor_position,
        )
        debug_display.text = f"{len(subcanvasses)} subcanvasses, {len(gaps)} gaps, selected: {selected_from}, {selected_to}"
        render(
            subcanvasses, subcanvasses_display, selected_from, cursor_stop=selected_to
        )
        render(gaps, gaps_display, selected_from, selected_to)
    else:
        cursor_position = event._Buffer__cursor_position
        debug_display.text = f"{len(subcanvasses)} subcanvasses, {len(gaps)} gaps, cursor:{cursor_position}"
        render(subcanvasses, subcanvasses_display, cursor_position)
        render(gaps, gaps_display, cursor_position)


def render(interval_list, interval_display, cursor_start, cursor_stop=None):
    interval_display.text = "\n".join(
        [
            x.summary(i, cursor_start, cursor_stop=cursor_stop)
            for i, x in enumerate(interval_list)
        ]
    )


legend_left = dedent(
    """
    Done----Ctrl+D
    Cancel--Ctrl+C
    """
).strip("\n")

legend_center = dedent(
    """
    Editor--Ctrl+E
    """
).strip("\n")

legend_right = dedent(
    """
    Signals--Ctrl+[Shift]+S
    Gaps-----Ctrl+[Shift]+G
    """
).strip("\n")


noise = ""
signal = ""
buffer = Buffer(on_text_changed=update, on_cursor_position_changed=update)

buffer_header = FormattedTextControl(text="Delete noise until only signal remains")
subcanvasses_header = FormattedTextControl(text="Signal")
gaps_header = FormattedTextControl(text="Noise")

subcanvasses_display = FormattedTextControl(text="")
gaps_display = FormattedTextControl(text="")
debug_display = FormattedTextControl(text="")

selected_idx = 0

root_container = HSplit(
    [
        VSplit(
            [
                Frame(
                    title="Delete noise until only signal remains",
                    body=Window(content=BufferControl(buffer=buffer)),
                ),
                Frame(
                    title="Signals",
                    body=Window(width=15, content=subcanvasses_display),
                ),
                Frame(title="Gaps", body=Window(width=10, content=gaps_display)),
            ]
        ),
        HorizontalLine(),
        VSplit(
            [
                Window(content=FormattedTextControl(text=legend_left)),
                Window(content=FormattedTextControl(text=legend_center)),
                Window(
                    content=FormattedTextControl(text=legend_right),
                    align=WindowAlign.RIGHT,
                ),
            ]
        ),
        HorizontalLine(),
        Window(content=debug_display),
        HorizontalLine(),
    ]
)


def make_canvas(_noise):

    global noise
    noise = _noise
    config = dotdir.make_or_get()

    subcanvasses.append(Interval(start=0, end=len(noise) - 1, content=noise))

    # start with the input noise as the signal
    buffer.text = noise

    kb = KeyBindings()

    @kb.add("c-c")
    def done(event):
        event.app.exit()

    # https://github.com/prompt-toolkit/python-prompt-toolkit/issues/502#issuecomment-466591259
    sys.stdin = sys.stderr
    Application(
        key_bindings=kb, layout=Layout(root_container), editing_mode=EditingMode.VI
    ).run()
