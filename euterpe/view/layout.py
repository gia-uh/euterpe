"""Putting views together: row() side by side under one caption, figure() for a hand-made drawing."""

from __future__ import annotations

import re
from collections.abc import Callable

from euterpe.view.base import View

_SIZE = re.compile(r'<svg[^>]*?width="([\d.]+)pt"[^>]*?height="([\d.]+)pt"', re.S)


class Row(View):
    """Several views as panels of one SVG, left to right; the audio is the first view's that has one."""

    def __init__(self, *views: View, caption=None, id=None):
        super().__init__(caption=caption, id=id)
        self.views = views
        self.audio = next((v.audio for v in views if v.audio is not None), None)

    def svg(self) -> bytes | None:
        if self._svg is None:
            parts, x, h, gap = [], 0.0, 0.0, 12.0
            for v in self.views:
                s = v.svg()
                if s is None:
                    continue
                text = s.decode()
                w_pt, h_pt = map(float, _SIZE.search(text).groups())
                body = text[text.index("<svg"):]
                # sizes in the panel's own pt units, so they match the row's viewBox
                body = re.sub(r'(width|height)="([\d.]+)pt"', r'\1="\2"', body, count=2)
                body = body.replace("<svg", f'<svg x="{x:.2f}" y="0"', 1)
                parts.append(body)
                x += w_pt + gap
                h = max(h, h_pt)
            w = max(x - gap, 0.0)
            self._svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                         f'width="{w:.2f}pt" height="{h:.2f}pt" viewBox="0 0 {w:.2f} {h:.2f}">'
                         + "".join(parts) + "</svg>").encode()
        return self._svg


class Figure(View):
    """A hand-made matplotlib drawing under the same contract. Pass a function that returns the
    Figure, so it is drawn in the house style, or a Figure already drawn."""

    def __init__(self, fig, *, caption=None, id=None):
        super().__init__(caption=caption, id=id)
        self.fig = fig

    def draw(self):
        return self.fig() if isinstance(self.fig, Callable) else self.fig


def row(*views: View, **kw) -> Row:
    return Row(*views, **kw)


def figure(fig, **kw) -> Figure:
    return Figure(fig, **kw)
