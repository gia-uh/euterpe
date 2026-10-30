"""Special views: the picture an object has of its own, drawn above its widget. A chord shape
as a chord diagram, a phrase on a fretted instrument as tablature, a phrase on a kit as a hit
grid, any other phrase with pitches as a piano roll. Spec 2026-10-28, section 06.

Each returns (svg body, width, height, x0, x1): x0 and x1 are where time 0 and the end of the
sound fall, so the widget's script moves a playhead over it; None when it has no time axis.
Marks with data-t light up while they sound."""

from __future__ import annotations

import html
import math

from euterpe.pitch import Pitch
from euterpe.view.style import INK, MADDER, NOTE_NAMES, PRUSSIAN, RULE, WASH

W = 640  # every special view is this wide in its own viewBox
X0, X1 = 64, W - 8  # where time runs, after the row names


def _num(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _number(pitch) -> int:
    """The nearest equal-tempered note number of a Pitch or a frequency in Hz."""
    return pitch.number if isinstance(pitch, Pitch) else round(69 + 12 * math.log2(float(pitch) / 440))


def _name(number: int, octave: bool = True) -> str:
    return NOTE_NAMES[number % 12] + (str(number // 12 - 1) if octave else "")


def _ticks(seconds: float, y: float) -> str:
    from euterpe.view.widget import _step

    step = _step(seconds)
    decimals = 0 if step >= 1 else 1 if step >= 0.1 else 2
    out, t = [], 0.0
    while t <= seconds + 1e-9:
        x = X0 + (X1 - X0) * t / seconds
        out.append(f'<line x1="{_num(x)}" x2="{_num(x)}" y1="{_num(y - 4)}" y2="{_num(y - 1)}" stroke="{RULE}" stroke-width="0.6"/>'
                   f'<text x="{_num(x)}" y="{_num(y + 8)}" text-anchor="middle" fill="#6b7078">{t:.{decimals}f}</text>')
        t += step
    return "".join(out)


def _playhead(height: float) -> str:
    return (f'<g class="eu-ph" transform="translate({X0},0)"><line y1="0" y2="{_num(height)}" stroke="{MADDER}" '
            f'stroke-width="1.4"/></g>')


def _rules(bars, seconds: float, top: float, bottom: float) -> str:
    """A hairline at each bar's start, in seconds."""
    xs = [_num(X0 + (X1 - X0) * t / seconds) for t in bars]
    return "".join(f'<line class="eu-bar" x1="{x}" x2="{x}" y1="{_num(top)}" y2="{_num(bottom)}" stroke="{RULE}" stroke-width="0.6"/>'
                   for x in xs)


def special_view(x, seconds: float) -> tuple | None:
    """The special view of what a widget plays, or None."""
    from euterpe.instruments.fretted import Fretted
    from euterpe.instruments.percussion import Kit
    from euterpe.instruments.phrase import Phrase

    if not isinstance(x, Phrase) or not x.notes or seconds <= 0:
        return None
    if isinstance(x.instrument, Fretted):
        return tablature(x.notes, x.instrument, seconds)
    if isinstance(x.instrument, Kit):
        return hits(x.notes, x.instrument, seconds)
    if len(x.notes) > 1 and all(isinstance(n.pitch, (Pitch, int, float)) for n in x.notes):
        return roll(x.notes, seconds)
    return None


def chord(shape, tuning) -> tuple:
    """A chord diagram: strings low to high from left to right, × over a string not played, ○
    over an open one, a dot with its fret number on each stopped string, each string's note
    under it, and the tab as the label."""
    frets = shape.frets
    n = len(frets)
    stopped = [f for f in frets if f]
    first = 1 if not stopped or max(stopped) <= 4 else min(stopped)
    rows = max(4, (max(stopped) - first + 1) if stopped else 4)
    dx, dy = 30, 26
    w = dx * (n - 1)
    left = (W - w) / 2
    top = 34
    p = []
    if first == 1:
        p.append(f'<rect x="{_num(left)}" y="{top - 4}" width="{w}" height="4" fill="{INK}"/>')
    else:
        p.append(f'<text x="{_num(left - 12)}" y="{_num(top + dy / 2 + 4)}" text-anchor="end" font-size="12">{first}fr</text>')
    for i in range(n):
        x = left + i * dx
        p.append(f'<line x1="{_num(x)}" x2="{_num(x)}" y1="{top}" y2="{top + rows * dy}" stroke="{INK}" stroke-width="0.9"/>')
    for j in range(1, rows + 1):
        p.append(f'<line x1="{_num(left)}" x2="{_num(left + w)}" y1="{top + j * dy}" y2="{top + j * dy}" stroke="{RULE}" stroke-width="0.8"/>')
    for i, f in enumerate(frets):
        x = left + i * dx
        if f is None:
            p.append(f'<text x="{_num(x)}" y="{top - 10}" text-anchor="middle" font-size="14" fill="{MADDER}">×</text>')
            continue
        if f == 0:
            p.append(f'<circle cx="{_num(x)}" cy="{top - 14}" r="5" fill="none" stroke="{INK}" stroke-width="1"/>')
        else:
            y = top + (f - first + 0.5) * dy
            p.append(f'<circle cx="{_num(x)}" cy="{_num(y)}" r="10" fill="{PRUSSIAN}"/>'
                     f'<text x="{_num(x)}" y="{_num(y + 4)}" text-anchor="middle" font-size="11" fill="#fff">{f}</text>')
        p.append(f'<text x="{_num(x)}" y="{top + rows * dy + 16}" text-anchor="middle" font-size="11" fill="#555">'
                 f'{_name(_number(tuning[i]) + f, octave=False)}</text>')
    sep = "-" if any(f is not None and f > 9 for f in frets) else ""
    tab = sep.join("x" if f is None else str(f) for f in frets)
    h = top + rows * dy + 44
    p.append(f'<text x="{W / 2}" y="{h - 8}" text-anchor="middle" font-size="14" font-family="ui-monospace,monospace">{tab}</text>')
    return "".join(p), W, h, None, None


def tablature(notes, instrument, seconds: float) -> tuple:
    """One line per string, the highest on top as players read it, each note's fret at its time."""
    n = len(instrument.tuning)
    dy, top = 14, 10
    h = top + dy * (n - 1) + 26
    p = []
    for s in range(1, n + 1):  # string 1 is the highest
        y = top + (s - 1) * dy
        p.append(f'<text x="{X0 - 10}" y="{y + 3.5}" text-anchor="end" fill="#555">{_name(instrument._open(s).number, octave=False)}</text>'
                 f'<line x1="{X0 - 4}" x2="{X1}" y1="{y}" y2="{y}" stroke="{RULE}" stroke-width="0.7"/>')
    for note in notes:
        s = note.resource
        if not isinstance(s, int) or not 1 <= s <= n or note.time >= seconds:
            continue
        fret = _number(note.pitch) - instrument._open(s).number
        x, y = X0 + (X1 - X0) * note.time / seconds, top + (s - 1) * dy
        p.append(f'<rect x="{_num(x - 5)}" y="{y - 6}" width="10" height="12" fill="#fff"/>'
                 f'<text x="{_num(x)}" y="{y + 4}" text-anchor="middle" font-size="11" font-family="ui-monospace,monospace" '
                 f'fill="{INK}" data-t="{note.time:.3f}">{fret}</text>')
    p.append(_ticks(seconds, top + dy * (n - 1) + 14))
    p.append(_playhead(top + dy * (n - 1) + 8))
    return "".join(p), W, h, X0, X1


def drum_rows(names) -> list[str]:
    """Drum names as a score writes them, each once, in the order drum notation stacks them, top to bottom."""
    places = {"crash": 0, "ride": 1, "hihat": 2, "snare": 4, "kick": 5}
    return sorted(set(names), key=lambda name: (3, int(name[3:])) if name.startswith("tom") else (places[name], 0))


def _drum_names(kit) -> list[tuple[object, str]]:
    """The kit's drums in the order drum notation stacks them, top to bottom."""
    named = [(kit.crash, "crash"), (kit.ride, "ride"), (kit.hihat, "hi-hat")]
    named += [(t, f"tom {i + 1}") for i, t in enumerate(kit.toms)]
    named += [(kit.snare, "snare"), (kit.kick, "kick")]
    return named


def hits(notes, kit, seconds: float, bars=(), playhead: bool = True, names: dict[int, str] | None = None) -> tuple:
    """One row per drum that plays, a mark per hit at its time, its velocity as ink density. bars are bar starts to
    rule, in seconds. names gives each note's drum as written, by the note's id, in place of the kit's."""
    if names is not None:
        played = [(name, name) for name in drum_rows(names[id(n)] for n in notes)]
        row = lambda n: names[id(n)]
    else:
        played = []
        for drum, name in _drum_names(kit):
            if any(n.resource is drum for n in notes):
                played.append((drum, name))
        for n in notes:  # drums not among the kit's own, by their class
            if all(n.resource is not d for d, _ in played):
                played.append((n.resource, type(n.resource).__name__.lower()))
        row = lambda n: n.resource
    rh, top = 16, 6
    h = top + rh * len(played) + 18
    p = []
    times = sorted({round(n.time, 4) for n in notes})
    gaps = [b - a for a, b in zip(times, times[1:]) if b - a > 1e-3]
    if gaps:  # hits on a step grid: a faint line every four steps
        step = min(gaps)
        if all(abs(t / step - round(t / step)) < 0.01 for t in times) and seconds / (4 * step) <= 64:
            k = 0
            while 4 * k * step <= seconds:
                x = X0 + (X1 - X0) * 4 * k * step / seconds
                p.append(f'<line x1="{_num(x)}" x2="{_num(x)}" y1="{top}" y2="{top + rh * len(played)}" stroke="{WASH}" stroke-width="1"/>')
                k += 1
    p.append(_rules(bars, seconds, top, top + rh * len(played)))
    for r, (drum, name) in enumerate(played):
        y = top + r * rh
        p.append(f'<text x="{X0 - 10}" y="{y + rh / 2 + 3}" text-anchor="end" fill="#555">{html.escape(name)}</text>')
        for n in notes:
            if row(n) == drum and n.time < seconds:
                x = X0 + (X1 - X0) * n.time / seconds
                p.append(f'<rect x="{_num(x - 3)}" y="{y + 2}" width="6" height="{rh - 4}" rx="1.5" fill="{PRUSSIAN}" '
                         f'fill-opacity="{0.35 + 0.65 * min(1.0, n.velocity):.2f}" data-t="{n.time:.3f}"/>')
    p.append(_ticks(seconds, top + rh * len(played) + 6))
    if playhead:
        p.append(_playhead(top + rh * len(played)))
    return "".join(p), W, h, X0, X1


def roll(notes, seconds: float, bars=(), numerals=(), peak: bool = False, playhead: bool = True) -> tuple:
    """A keyboard on the left over the notes' range and two semitones each side, each note a
    bar from its time for its duration, named as its Pitch is spelled. bars are bar starts to rule, in seconds; numerals
    are (seconds, text) written under the notes; peak marks the highest pitch in madder."""
    numbers = [_number(n.pitch) for n in notes]
    lo, hi = min(numbers) - 2, max(numbers) + 2
    rows = hi - lo + 1
    rh = max(3.0, min(12.0, 160 / rows))
    top = 4
    under = 12 if numerals else 0
    h = top + rows * rh + 18 + under
    p = []
    for m in range(lo, hi + 1):
        y = top + (hi - m) * rh
        black = m % 12 in (1, 3, 6, 8, 10)
        p.append(f'<rect x="{X0 - 30}" y="{_num(y)}" width="{18 if black else 26}" height="{_num(rh)}" '
                 f'fill="{INK if black else "#fff"}" stroke="{RULE}" stroke-width="0.3"/>')
        if black:
            p.append(f'<rect x="{X0}" y="{_num(y)}" width="{X1 - X0}" height="{_num(rh)}" fill="#f3f5f8"/>')
        if m % 12 == 0:
            p.append(f'<text x="{X0 - 32}" y="{_num(y + rh - 1)}" text-anchor="end" font-size="7" fill="#555">{_name(m)}</text>')
    p.append(_rules(bars, seconds, top, top + rows * rh))
    for t, text in numerals:
        p.append(f'<text x="{_num(X0 + (X1 - X0) * t / seconds)}" y="{_num(top + rows * rh + 10)}" font-size="9" '
                 f'font-style="italic">{html.escape(text)}</text>')
    for n, m in zip(notes, numbers):
        if n.time >= seconds:  # the clip ends before this note starts
            continue
        x = X0 + (X1 - X0) * n.time / seconds
        w = max(2.0, (X1 - X0) * n.duration / seconds)
        y = top + (hi - m) * rh
        p.append(f'<rect x="{_num(x)}" y="{_num(y + 0.5)}" width="{_num(min(w, X1 - x))}" height="{_num(rh - 1)}" rx="1.5" '
                 f'fill="{MADDER if peak and m == hi - 2 else PRUSSIAN}" data-t="{n.time:.3f}"/>')
        if rh >= 5:
            p.append(f'<text x="{_num(x + 2)}" y="{_num(y - 0.5)}" font-size="6.5">{n.pitch.pretty if isinstance(n.pitch, Pitch) else _name(m)}</text>')
    p.append(_ticks(seconds, top + rows * rh + 6 + under))
    if playhead:
        p.append(_playhead(top + rows * rh))
    return "".join(p), W, h, X0, X1
