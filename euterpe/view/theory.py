"""Views of theory objects: the circle of fifths, a keyboard with pressed keys, and a score's written pitch classes.
The first two are drawn by hand as SVG with text, so they need no matplotlib and the page's font sets their names."""

from __future__ import annotations

import html
import math
from bisect import bisect_right
from collections.abc import Iterable
from fractions import Fraction
from typing import TYPE_CHECKING

import numpy as np

from euterpe.pitch import Pitch
from euterpe.score.model import Note
from euterpe.theory.key import Key
from euterpe.view.base import View
from euterpe.view.signal import draw_chroma
from euterpe.view.special import _name, _num
from euterpe.view.style import INK, MADDER, RULE, WASH, signs
from euterpe.view.widget import FONT, PLATE, caption_html

if TYPE_CHECKING:
    from euterpe.score.model import Score

_MAJORS = ("C", "G", "D", "A", "E", "B", "F#", "Db", "Ab", "Eb", "Bb", "F")  # a fifth apart, each a wedge from the top


class _Drawing(View):
    """A hand-drawn SVG with no sound, sized by width as a matplotlib view is. On the site it sits inline on the plate,
    so its text takes the page's font and it shrinks with the column."""

    def body(self) -> tuple[str, float, float]:
        """The markup, and its width and height in its own units."""
        raise NotImplementedError

    def svg(self) -> bytes:
        if self._svg is None:
            body, w, h = self.body()
            points = self.width * 72
            self._svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_num(w)} {_num(h)}" width="{_num(points)}pt" '
                         f'height="{_num(points * h / w)}pt" {FONT} fill="{INK}">{body}</svg>').encode()
        return self._svg

    def _repr_mimebundle_(self, include=None, exclude=None):
        svg = self.svg().decode()
        style = f"width:100%;max-width:{_num(self.width * 72)}px;height:auto;display:block;margin:auto"
        inline = svg.replace("<svg", f'<svg style="{style}"', 1)
        page = f'<figure class="euterpe-figure" style="{PLATE}">{inline}{caption_html(self.caption)}</figure>'
        meta = {k: v for k, v in (("caption", self.caption), ("id", self.id)) if v}
        meta["site"] = "html"
        return {"text/html": page, "image/svg+xml": svg, "text/plain": repr(self)}, meta


def _point(radius: float, angle: float, centre: float) -> str:
    """The point at a radius and an angle in degrees clockwise from the top."""
    a = math.radians(angle)
    return f"{_num(centre + radius * math.sin(a))} {_num(centre - radius * math.cos(a))}"


class Circle(_Drawing):
    """The circle of fifths: majors outside, minors in italic inside, the key's wedge in madder and its neighbours in
    wash. A key past six sharps or flats takes the wedge of the key that sounds the same."""

    width = 4.0

    def __init__(self, key: Key, *, caption: str | None = None, id: str | None = None):
        super().__init__(caption=caption, id=id)
        self.key = key

    def body(self) -> tuple[str, float, float]:
        size, centre, outer, inner = 420, 210, 204, 72
        marked = self.key.signature % 12
        wedges, names = [], []
        for i, tonic in enumerate(_MAJORS):
            angle = i * 30
            fill = MADDER if i == marked else WASH if (i - marked) % 12 in (1, 11) else "#fff"
            ink = "#fff" if i == marked else INK
            start, end = angle - 15, angle + 15
            wedges.append(f'<path data-key="{signs(tonic)}" d="M{_point(inner, start, centre)} A{inner} {inner} 0 0 1 {_point(inner, end, centre)} '
                          f'L{_point(outer, end, centre)} A{outer} {outer} 0 0 0 {_point(outer, start, centre)} Z" '
                          f'fill="{fill}" stroke="{RULE}" stroke-width="1"/>')
            minor = Key(tonic, "major").relative.tonic
            for radius, text, style in ((162, signs(tonic), 'font-size="24"'),
                                        (104, minor[0].lower() + signs(minor[1:]), 'font-size="18" font-style="italic"')):
                x, y = _point(radius, angle, centre).split()
                names.append(f'<text x="{x}" y="{_num(float(y) + 7)}" text-anchor="middle" {style} fill="{ink}">{text}</text>')
        name = f"{signs(self.key.tonic)} {self.key.mode}"
        lines = [(name, 186), ("and its", 214), ("neighbours", 242)]
        middle = "".join(f'<text x="{centre}" y="{y}" text-anchor="middle" font-size="15" font-style="italic" fill="{MADDER}">{text}</text>'
                         for text, y in lines)
        return "".join(wedges) + "".join(names) + middle, size, size


def circle(key: Key, *, caption: str | None = None, id: str | None = None) -> Circle:
    return Circle(key, caption=caption, id=id)


_WHITE_W, _WHITE_H, _BLACK_W, _BLACK_H = 30, 110, 20, 68


class Keyboard(_Drawing):
    """A keyboard in whole octaves, at least two, from the C at or under the lowest note to the C over the highest. The
    pressed keys are in madder, named as each pitch is spelled, the other Cs in grey, and label stands to the right."""

    def __init__(self, pitches: Iterable[Pitch], *, label: str | None = None, caption: str | None = None, id: str | None = None):
        super().__init__(caption=caption, id=id)
        self.pressed = {p.number: p for p in pitches}
        self.label = label
        if not self.pressed:
            raise ValueError("keyboard: no pitches to press")

    def _key(self, number: int, x: float) -> tuple[str, str]:
        """A key's rect and its name."""
        black = _name(number, octave=False).endswith("♯")
        pitch = self.pressed.get(number)
        name = pitch.pretty if pitch else _name(number)
        w, h = (_BLACK_W, _BLACK_H) if black else (_WHITE_W, _WHITE_H)
        fill = MADDER if pitch else INK if black else "#fff"
        rect = (f'<rect data-key="{name}" x="{_num(x)}" y="2" width="{w}" height="{h}" rx="2.5" fill="{fill}" '
                f'stroke="{INK}" stroke-width="0.8"/>')
        if pitch or number % 12 == 0:
            ink = "#fff" if pitch else RULE
            size, y = (8.5, h - 5) if black else (10.5, h - 8)
            return rect, (f'<text x="{_num(x + w / 2)}" y="{_num(y)}" text-anchor="middle" font-size="{size}" font-style="italic" '
                          f'fill="{ink}">{name}</text>')
        return rect, ""

    def body(self) -> tuple[str, float, float]:
        lowest, highest = min(self.pressed), max(self.pressed)
        lo, hi = lowest - lowest % 12, highest - highest % 12 + 12
        if hi - lo < 24:
            lo -= 12
        whites, blacks, x = [], [], 1.0
        for number in range(lo, hi + 1):
            if _name(number, octave=False).endswith("♯"):
                blacks.append(self._key(number, x - _BLACK_W / 2))
            else:
                whites.append(self._key(number, x))
                x += _WHITE_W
        keys = "".join(rect for rect, _ in whites + blacks) + "".join(name for _, name in whites + blacks)
        w, h = x + 1, _WHITE_H + 4
        if self.label:
            keys += (f'<text x="{_num(x + 12)}" y="{_num(h / 2 + 5)}" font-size="14" font-style="italic" fill="{MADDER}">'
                     f"{html.escape(self.label)}</text>")
            w += 20 + 8 * len(self.label)
        return keys, w, h


def keyboard(pitches: Iterable[Pitch], *, label: str | None = None, caption: str | None = None, id: str | None = None) -> Keyboard:
    """These pitches pressed on a keyboard, as a view."""
    return Keyboard(pitches, label=label, caption=caption, id=id)


_NUMERAL_GAP = 3  # points between two numerals above the bars


class WrittenChroma(View):
    """A score's written pitch classes, one column per beat, each the share of the beat's written time on each pitch
    class, in the ink of Clip.chroma. matrix has shape (12, beats) and edges holds the beats' bounds in whole notes."""

    def __init__(self, score: Score, *, caption: str | None = None, id: str | None = None):
        super().__init__(caption=caption, id=id)
        beats = score._beats()
        self.edges = np.array([float(start) for _, _, start, _ in beats] + [float(beats[-1][3])])
        self.matrix = np.zeros((12, len(beats)))
        ends = [end for _, _, _, end in beats]
        for placed in score.events():
            if not isinstance(placed.event, Note):
                continue
            end = placed.offset + placed.event.duration
            index = bisect_right(ends, placed.offset)
            while index < len(beats) and beats[index][2] < end:
                held: Fraction = min(end, ends[index]) - max(placed.offset, beats[index][2])
                for pitch in placed.event.pitches:
                    self.matrix[pitch.number % 12, index] += float(held)
                index += 1
        totals = self.matrix.sum(axis=0)
        self.matrix[:, totals > 0] /= totals[totals > 0]
        self.bars = _first_beats(beats)
        self.numerals = _changes(beats, score.harmony())

    def draw(self):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(self.width, 2.8))
        draw_chroma(ax, self.matrix, self.edges)
        ax.set_xlim(self.edges[0], self.edges[-1])
        for _, x in self.bars[1:]:
            ax.axvline(x, color="#fff", lw=1.5)
        every = max(1, math.ceil(len(self.bars) / 16))
        shown = self.bars[::every]
        ax.set_xticks([x for _, x in shown], [str(bar) for bar, _ in shown])
        ax.set_xlabel("bar", fontstyle="italic")
        right = None
        for x, text in self.numerals:  # a numeral that would touch the one before it is left out
            label = ax.text(x, 1.02, text, transform=ax.get_xaxis_transform(), va="bottom", fontsize=9.5, fontstyle="italic")
            box = label.get_window_extent()
            if right is not None and box.x0 < right + _NUMERAL_GAP * fig.dpi / 72:
                label.remove()
            else:
                right = box.x1
        return fig


def _first_beats(beats: list) -> list[tuple[int, float]]:
    """Each bar with the start of its first beat."""
    first: dict[int, float] = {}
    for bar, _, start, _ in beats:
        first.setdefault(bar, float(start))
    return list(first.items())


def _changes(beats: list, harmony: list) -> list[tuple[float, str]]:
    """Each numeral that changes at the start of its beat, ? where harmony finds none."""
    numerals, last = [], None
    for (_, _, start, _), found in zip(beats, harmony):
        text = found.roman.text if found.roman else "?"
        if text != last:
            numerals.append((float(start), text))
            last = text
    return numerals


def written_chroma(score: Score, *, caption: str | None = None, id: str | None = None) -> WrittenChroma:
    if not score.parts:
        raise ValueError("chroma: the score has no parts")
    if not score.bars:
        raise ValueError("chroma: the score has nothing written")
    return WrittenChroma(score, caption=caption, id=id)
