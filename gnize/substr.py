"""
# Purpose

This module contains helpers
"""

from dataclasses import dataclass
from rich.console import Console
from ansi2html import Ansi2HTMLConverter


def strike(text):
    console = Console()
    with console.capture() as capture:
        console.print(f"[strike]{text}[/strike]", end="")
    return capture.get()

@dataclass
class Interval:
    "a subinterval of the given noise (might be a subcanvas, might be a gap)"

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
