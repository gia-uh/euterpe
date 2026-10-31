"""A score's views: engraved notation, its piano roll, and the widget display(score) shows, one of them over the sound
widget with a cursor that walks it as it plays. Euterpe writes MusicXML and verovio (euterpe[notation]) engraves it to
SVG; the roll draws itself, so it stands in when verovio is missing. Spec 2026-10-30."""

from __future__ import annotations

import html
import json
import math
import re
from bisect import bisect_right
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from euterpe.score.model import Score
from euterpe.score.musicxml import musicxml_bytes
from euterpe.theory import Meter
from euterpe.view.base import View
from euterpe.view.special import W, _num, _number, drum_rows, hits as _hits, roll as _roll
from euterpe.view.style import INK, MADDER, PRUSSIAN, RULE, hz, keyboard_strip
from euterpe.view.widget import FONT, PLATE, Widget, caption_html

if TYPE_CHECKING:
    from euterpe.instruments.core import Note as Performed
    from euterpe.score.model import Line
    from euterpe.sound.clip import Clip

SCALE = 36  # percent, verovio's staff size
PAGE_WIDTH = 1530  # verovio's units: at SCALE this is about 550 wide, the width the book's column gives the plate
PAGE_HEIGHT = 60000  # verovio's largest page: more than 700 bars of one staff, fewer on several
MARGIN = 20
# Verovio writes a metronome's note in a music font it would embed. These are the same notes in plain Unicode.
_METRONOME = str.maketrans({"\ueca2": "\U0001d15d", "\ueca3": "\U0001d15e", "\ueca5": "♩", "\ueca7": "♪",
                            "\ueca9": "\U0001d161", "\uecb7": "."})


_MADDER_RULES = (f".euterpe-score .eu-on,.euterpe-score .eu-on *{{fill:{MADDER};stroke:{MADDER}}}"
                 ".eu-score g.note,.eu-score rect[id]{cursor:pointer}.eu-score text{pointer-events:none}"
                 f".eu-cursor{{stroke:{MADDER};stroke-width:1.5;vector-effect:non-scaling-stroke;pointer-events:none}}")
_PANEL_RULES = "@media (max-width:640px){.eu-score>svg{min-width:600px}}"


def _size(svg: bytes) -> tuple[float, float]:
    return tuple(map(float, re.search(r'<svg[^>]*?\bwidth="([\d.]+)"[^>]*?\bheight="([\d.]+)"', svg.decode()).groups()))


def _panel(svg: bytes) -> str:
    """The drawing as the plate holds it: it shrinks with the column and never grows past its natural width; on a phone
    it stays readable and the panel scrolls."""
    style = f"width:100%;max-width:{_size(svg)[0]:g}px;height:auto;display:block"
    return f'<div class="eu-score" style="max-height:60vh;overflow:auto">{svg.decode().replace("<svg", f"""<svg style="{style}\"""", 1)}</div>'


class _Still(View):
    """A drawing with no sound: on the site, the panel alone on the plate; in print, its SVG."""

    def _repr_mimebundle_(self, include=None, exclude=None):
        page = (f'<figure class="euterpe-figure" style="{PLATE}"><style>{_PANEL_RULES}</style>{_panel(self.svg())}'
                f"{caption_html(self.caption)}</figure>")
        data = {"text/html": page, "image/svg+xml": self.svg().decode(), "text/plain": repr(self)}
        meta = {k: v for k, v in (("caption", self.caption), ("id", self.id)) if v}
        meta["site"] = "html"
        return data, meta


class Drawn(_Still):
    """A view whose SVG is already made. written holds each engraved note as (id, start, end), in whole notes on the
    written timeline."""

    def __init__(self, svg: bytes, *, caption: str | None = None, written: list[tuple[str, Fraction, Fraction]] = ()):
        super().__init__(caption=caption)
        self._svg = svg
        self.written = written


class ScoreWidget(Widget):
    """What display(score) shows: the panel, an engraving or a roll, over the sound widget, with one player and one
    caption. events is the time map: [seconds, ids on, ids off] in time order, which the widget's script walks to move
    the cursor and light the notes. In print the panel stands where a widget's special view does."""

    classes = "euterpe-widget euterpe-score"
    points = 110  # the score above carries the detail, and the figure has a budget

    def __init__(self, audio: Clip, panel: View, events: list, *, caption: str | None = None, id: str | None = None,
                 normalize: bool = True):
        width, height = _size(panel.svg())
        super().__init__(audio, caption=caption, id=id, normalize=normalize,
                         special=(panel.svg().decode(), width, height, None, None))
        self.panel, self.events = panel, events

    def _top(self, sp: str | None) -> str:
        return (f"<style>{_PANEL_RULES}{_MADDER_RULES}</style>{_panel(self.panel.svg())}"
                f'<script type="application/json" class="eu-map">{json.dumps(self.events, separators=(",", ":"))}</script>')


def _events(spans: list[tuple[str, float, float]]) -> list:
    """The map from (id, seconds on, seconds off): each time once, in order, to the millisecond. A note keeps a
    millisecond at least, since the script takes an event's ids off before it puts its ids on."""
    found: dict[float, tuple[list, list]] = {}
    for name, start, end in spans:
        start, end = round(start, 3), round(end, 3)
        found.setdefault(start, ([], []))[0].append(name)
        found.setdefault(max(end, round(start + 0.001, 3)), ([], []))[1].append(name)
    return [[t, *found[t]] for t in sorted(found)]


def time_map(score: Score, written: list[tuple[str, Fraction, Fraction]]) -> list:
    """The engraved notes on the played timeline: each once per pass of its bar, at the seconds the score performs it,
    through its TempoMap and its swing. Humanize's jitter is left out. A pass's short closing bar drops what it does
    not play."""
    tempo = score.tempo_map()
    swing = score.performance.swing
    seconds = lambda offset: tempo.seconds(tempo._swung(swing, offset))
    numbers = sorted({played.bar for played in tempo.played})
    starts, at = [], Fraction(0)
    for number in range(1, numbers[-1] + 1):
        starts.append(at)
        at += score._bar_length(number)
    by_bar: dict[int, list] = {}
    for note in written:
        by_bar.setdefault(bisect_right(starts, note[1]), []).append(note)
    spans = []
    for played in tempo.played:
        first = starts[played.bar - 1]
        for name, on, off in by_bar.get(played.bar, ()):
            if on - first < played.length:
                start = played.start + on - first
                spans.append((name, seconds(start), seconds(start + off - on)))
    return _events(spans)


def _written(timemap: list[dict]) -> list[tuple[str, Fraction, Fraction]]:
    """Verovio's timemap as (id, start, end) in whole notes, from its quarters, a float that a tuplet leaves inexact."""
    started, notes = {}, []
    for entry in timemap:
        at = Fraction(entry["qstamp"]).limit_denominator(100_000) / 4
        for name in entry.get("off", ()):
            notes.append((name, started[name], at))
        for name in entry.get("on", ()):
            started[name] = at
    return sorted(notes, key=lambda note: note[1])


def _engrave(data: bytes) -> tuple[bytes, list[tuple[str, Fraction, Fraction]]]:
    """MusicXML as one SVG page, the same bytes each time, in the house ink, with no script and no font file, and its
    notes as (id, start, end). Verovio does not play out repeats: its ids for a second pass are not in the SVG, and it
    does not know a closing bar stops short, so time_map plays them out from the TempoMap."""
    try:
        import verovio
    except ImportError as e:  # the notation extra is missing
        raise ImportError("engraving needs verovio: pip install 'euterpe[notation]'") from e
    toolkit = verovio.toolkit()
    toolkit.setOptions({
        "xmlIdSeed": 1, "scale": SCALE, "pageWidth": PAGE_WIDTH, "pageHeight": PAGE_HEIGHT, "adjustPageHeight": True,
        "pageMarginLeft": MARGIN, "pageMarginRight": MARGIN, "pageMarginTop": MARGIN, "pageMarginBottom": MARGIN,
        "breaks": "auto", "header": "none", "footer": "none", "svgViewBox": True, "smuflTextFont": "none", "expandNever": True,
    })
    if not toolkit.loadData(data.decode()):
        raise ValueError("notation: verovio could not read the MusicXML")
    if toolkit.getPageCount() > 1:
        raise ValueError("notation: the score is too long for one figure; choose its measures with bars=(first, last)")
    svg = toolkit.renderToSVG(1)
    svg = re.sub(r'<svg viewBox="0 0 (\d+) (\d+)"', r'<svg width="\1" height="\2" viewBox="0 0 \1 \2"', svg, count=1)
    width, height = re.search(r'<svg width="(\d+)" height="(\d+)"', svg).groups()
    # The inner svg's size: a browser defaults it to the root's, but WeasyPrint draws it at nothing, so the PDF has no staff.
    svg = svg.replace('<svg class="definition-scale"', f'<svg class="definition-scale" x="0" y="0" width="{width}" height="{height}"', 1)
    svg = svg.replace('color="black"', f'color="{INK}" fill="{INK}"').replace('font-family="Times, serif"', FONT)
    return svg.replace(' font-family="Leipzig"', "").translate(_METRONOME).encode(), _written(toolkit.renderToTimemap({"includeRests": False}))


def notation(score: Score, bars: tuple[int, int] | None = None, caption: str | None = None,
             numerals: bool = False) -> View:
    svg, written = _engrave(musicxml_bytes(score, bars, numerals))
    return Drawn(svg, caption=caption, written=written)


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
        panel = notation(score)
    except ImportError as e:
        panel = roll(score, note=str(e))
    if not score.bars or any(part.instrument is None for part in score.parts.values()):
        return panel
    events = panel.events() if isinstance(panel, Roll) else time_map(score, panel.written)
    return ScoreWidget(score.play().take(), panel, events, normalize=normalize)


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


class Roll(_Still):
    """Piano rolls, one per lane under the part's name, drawn without matplotlib; a figure in matplotlib is for saving
    a PNG. Time runs in seconds, repeats played out, as the score sounds. Each note's mark has an id, and the lanes are
    one system to the widget's cursor, since time runs across them all."""

    def __init__(self, lanes: list[_Lane], seconds: float, bars: list[float], peak: bool, note: str | None):
        super().__init__()
        self.lanes, self.seconds, self.bars, self.peak, self.note = lanes, seconds, bars, peak, note
        notes = [n for lane in lanes for n in lane.notes]
        self.ids = {id(n): f"r{i}" for i, n in enumerate(notes, 1)}

    def events(self) -> list:
        """The time map: every note at its played start and end."""
        return _events([(self.ids[id(n)], n.time, n.time + n.duration) for lane in self.lanes for n in lane.notes])

    def _body(self, lane: _Lane) -> tuple[str, float]:
        if not lane.notes:
            return f'<text x="{W / 2}" y="16" text-anchor="middle" font-style="italic" fill="{RULE}">no notes</text>', 24
        if lane.names is not None:
            body, _, h, _, _ = _hits(lane.notes, None, self.seconds, self.bars, playhead=False, names=lane.names, ids=self.ids)
        else:
            body, _, h, _, _ = _roll(lane.notes, self.seconds, self.bars, lane.numerals, self.peak, playhead=False, ids=self.ids)
        return body, h

    def svg(self) -> bytes:
        if self._svg is None:
            y, top, inner = 0.0, "", []
            if self.note:
                top = f'<text x="0" y="10" font-style="italic" fill="{MADDER}">{html.escape(self.note)}</text>'
                y = 16.0
            for lane in self.lanes:
                body, h = self._body(lane)
                inner.append(f'<text x="0" y="{_num(y + 10)}" font-style="italic">{html.escape(lane.part)}</text>')
                inner.append(f'<svg x="0" y="{_num(y + 14)}" width="{W}" height="{_num(h)}" viewBox="0 0 {W} {_num(h)}">{body}</svg>')
                y += 14 + h
            self._svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {_num(y)}" width="{W}" height="{_num(y)}" '
                         f'{FONT} font-size="9" fill="{INK}">{top}<g class="system">{"".join(inner)}</g></svg>').encode()
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
