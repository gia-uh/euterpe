"""A score's views: engraved notation, and its piano roll. Euterpe writes MusicXML and verovio (euterpe[notation])
engraves it to SVG; the roll draws itself, so it stands in when verovio is missing."""

from __future__ import annotations

import html
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from euterpe.score.model import Score
from euterpe.score.musicxml import musicxml_bytes
from euterpe.theory import Meter
from euterpe.view.base import View
from euterpe.view.special import W, _num, _number, drum_rows, hits as _hits, roll as _roll
from euterpe.view.style import INK, MADDER, PRUSSIAN, RULE, hz, keyboard_strip
from euterpe.view.widget import FONT

if TYPE_CHECKING:
    from euterpe.instruments.core import Note as Performed
    from euterpe.score.model import Line

SCALE = 40  # percent, verovio's staff size
PAGE_WIDTH = 960  # verovio's units: at SCALE this is 384 wide, so a figure fits a phone
PAGE_HEIGHT = 60000  # verovio's largest page: more than 700 bars of one staff, fewer on several
MARGIN = 20
# Verovio writes a metronome's note in a music font it would embed. These are the same notes in plain Unicode.
_METRONOME = str.maketrans({"\ueca2": "\U0001d15d", "\ueca3": "\U0001d15e", "\ueca5": "♩", "\ueca7": "♪",
                            "\ueca9": "\U0001d161", "\uecb7": "."})


class Drawn(View):
    """A view whose SVG is already made, with the sound under it if it has one."""

    def __init__(self, svg: bytes, *, caption: str | None = None):
        super().__init__(caption=caption)
        self._svg = svg


def _engrave(data: bytes) -> bytes:
    """MusicXML as one SVG page, the same bytes each time, in the house ink, with no script and no font file."""
    try:
        import verovio
    except ImportError as e:  # the notation extra is missing
        raise ImportError("engraving needs verovio: pip install 'euterpe[notation]'") from e
    toolkit = verovio.toolkit()
    toolkit.setOptions({
        "xmlIdSeed": 1, "scale": SCALE, "pageWidth": PAGE_WIDTH, "pageHeight": PAGE_HEIGHT, "adjustPageHeight": True,
        "pageMarginLeft": MARGIN, "pageMarginRight": MARGIN, "pageMarginTop": MARGIN, "pageMarginBottom": MARGIN,
        "breaks": "auto", "header": "none", "footer": "none", "svgViewBox": True, "smuflTextFont": "none",
    })
    if not toolkit.loadData(data.decode()):
        raise ValueError("notation: verovio could not read the MusicXML")
    if toolkit.getPageCount() > 1:
        raise ValueError("notation: the score is too long for one figure; choose its measures with bars=(first, last)")
    svg = toolkit.renderToSVG(1)
    svg = re.sub(r'<svg viewBox="0 0 (\d+) (\d+)"', r'<svg width="\1" height="\2" viewBox="0 0 \1 \2"', svg, count=1)
    svg = svg.replace('color="black"', f'color="{INK}" fill="{INK}"').replace('font-family="Times, serif"', FONT)
    return svg.replace(' font-family="Leipzig"', "").translate(_METRONOME).encode()


def notation(score: Score, bars: tuple[int, int] | None = None, caption: str | None = None,
             numerals: bool = False) -> View:
    return Drawn(_engrave(musicxml_bytes(score, bars, numerals)), caption=caption)


def _meter(line: Line) -> Meter:
    """The meter a bar of the line's longest length fills, in quarters or shorter. A length no meter can write, as
    tuplets leave, rounds up to the quarters that hold it."""
    longest = max((sum(item.duration for item in bar if hasattr(item, "duration")) for bar in line.bars), default=0)
    longest = Fraction(longest) or Fraction(1)
    if longest.denominator & (longest.denominator - 1):
        longest = Fraction(math.ceil(longest * 4), 4)
    return Meter(f"{longest.numerator * 4 // min(longest.denominator, 4)}/{max(longest.denominator, 4)}")


def line_notation(line: Line, meter: Meter | None = None) -> View:
    score = Score(meter=meter or line.meter or _meter(line))
    score.part("", clef="treble").add(line)
    return notation(score)


def score_view(score: Score, normalize: bool = True) -> View:
    try:
        view = notation(score)
    except ImportError as e:
        view = roll(score, note=str(e))
    if all(part.instrument is not None for part in score.parts.values()) and score.bars:
        view.audio = score.play().take()
        view.normalize = normalize
    return view


@dataclass
class _Lane:
    """One row of the roll: a part's pitched notes, or with names its hits, each drum named as written."""

    part: str
    notes: list[Performed]
    numerals: list[tuple[float, str]]
    names: dict[int, str] | None = None


def _numerals(score: Score) -> list[tuple[float, str]]:
    """Each numeral of harmony() that changes, at its time on every pass, ? where it finds none."""
    tempo = score.tempo_map()
    harmony: dict[int, list] = {}
    for found in score.harmony():
        harmony.setdefault(found.bar, []).append(found)
    numerals, last = [], None
    for played in tempo.played:
        meter = played.meter
        for found in harmony.get(played.bar, ()):
            in_bar = max(Fraction(sum(meter.groups[:found.beat - 1]), meter.denominator), played.lead)
            if in_bar - played.lead >= played.length:  # a repeat's closing bar stops short of this beat
                continue
            text = found.roman.text if found.roman else "?"
            if text != last:
                numerals.append((tempo.seconds(played.start + in_bar - played.lead), text))
                last = text
    return numerals


class Roll(View):
    """Piano rolls, one per lane under the part's name, drawn without matplotlib; a figure in matplotlib is for saving
    a PNG. Time runs in seconds, repeats played out, as the score sounds."""

    def __init__(self, lanes: list[_Lane], seconds: float, bars: list[float], peak: bool, note: str | None):
        super().__init__()
        self.lanes, self.seconds, self.bars, self.peak, self.note = lanes, seconds, bars, peak, note

    def _body(self, lane: _Lane) -> tuple[str, float]:
        if not lane.notes:
            return f'<text x="{W / 2}" y="16" text-anchor="middle" font-style="italic" fill="{RULE}">no notes</text>', 24
        if lane.names is not None:
            body, _, h, _, _ = _hits(lane.notes, None, self.seconds, self.bars, playhead=False, names=lane.names)
        else:
            body, _, h, _, _ = _roll(lane.notes, self.seconds, self.bars, lane.numerals, self.peak, playhead=False)
        return body, h

    def svg(self) -> bytes:
        if self._svg is None:
            y, inner = 0.0, []
            if self.note:
                inner.append(f'<text x="0" y="10" font-style="italic" fill="{MADDER}">{html.escape(self.note)}</text>')
                y = 16.0
            for lane in self.lanes:
                body, h = self._body(lane)
                inner.append(f'<text x="0" y="{_num(y + 10)}" font-style="italic">{html.escape(lane.part)}</text>')
                inner.append(f'<svg x="0" y="{_num(y + 14)}" width="{W}" height="{_num(h)}" viewBox="0 0 {W} {_num(h)}">{body}</svg>')
                y += 14 + h
            self._svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {_num(y)}" width="{W}" height="{_num(y)}" '
                         f'{FONT} font-size="9" fill="{INK}">{"".join(inner)}</svg>').encode()
        return self._svg

    def draw(self):
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(len(self.lanes), 1, figsize=(self.width, 2.4 * len(self.lanes)), sharex=True, squeeze=False)
        for ax, lane in zip(axes[:, 0], self.lanes):
            ax.set_title(lane.part, loc="left", fontstyle="italic", fontsize=9)
            ax.set_xlim(0, self.seconds)
            for t in self.bars:
                ax.axvline(t, color=RULE, lw=0.5, zorder=0)
            if lane.names is not None:
                rows = drum_rows(lane.names[id(n)] for n in lane.notes)[::-1]  # the first row on top
                ax.plot([n.time for n in lane.notes], [rows.index(lane.names[id(n)]) for n in lane.notes], "|", color=PRUSSIAN,
                        markersize=11, markeredgewidth=1.6, clip_on=False)
                ax.set_yticks(range(len(rows)), rows)
                ax.set_ylim(-0.5, len(rows) - 0.5)
            elif lane.notes:
                numbers = [_number(n.pitch) for n in lane.notes]
                lo, hi = hz(min(numbers) - 2), hz(max(numbers) + 2)
                ax.set_yscale("log")
                ax.set_ylim(lo, hi)
                ax.set_yticks([])
                ax.minorticks_off()
                keyboard_strip(ax, lo, hi)
                ax.hlines([hz(m) for m in numbers], [n.time for n in lane.notes], [n.time + n.duration for n in lane.notes], lw=3,
                          colors=[MADDER if self.peak and m == max(numbers) else PRUSSIAN for m in numbers])
                for t, text in lane.numerals:
                    ax.text(t, 0.02, text, transform=ax.get_xaxis_transform(), va="bottom", fontsize=8, fontstyle="italic")
        axes[-1, 0].set_xlabel("seconds", fontstyle="italic")
        return fig


def roll(score: Score, part: str | None = None, peak: bool = False, note: str | None = None) -> View:
    """The score's parts as they sound with its own performance, seed 0. note is a line over the drawing."""
    if not score.parts:
        raise ValueError("roll: the score has no parts")
    score.events(part)  # raises for a part it does not have
    performed = score.performance._performed(score, 0)
    numerals = _numerals(score)
    lanes = []
    for name in score.parts if part is None else (part,):
        notes, names = performed[name]
        pitched = [n for n in notes if id(n) not in names]
        struck = [n for n in notes if id(n) in names]
        if pitched or not struck:
            lanes.append(_Lane(name, pitched, numerals))
        if struck:
            lanes.append(_Lane(name, struck, [], names))
    tempo = score.tempo_map()
    last = tempo.played[-1]
    seconds = max([tempo.seconds(last.start + last.length)] + [n.time + n.duration for lane in lanes for n in lane.notes])
    return Roll(lanes, seconds, [tempo.seconds(bar.start) for bar in tempo.played], peak, note)
