"""Views of what a unit does rather than what it sounds like: a filter's response, a shaper's curve."""

from __future__ import annotations

import copy

import numpy as np

from euterpe.sound.core import RATE, Unit, render
from euterpe.view.base import View
from euterpe.view.style import MADDER, SERIES, label_axis, note_name, octave_ruler


class _Probe(Unit):
    """A fixed signal fed to a copy of the unit in place of its source: an impulse or a ramp."""

    def __init__(self, signal: np.ndarray):
        self.signal = signal.astype(np.float32)
        self.reset()

    def reset(self) -> None:
        self.pos = 0

    def block(self, n: int) -> np.ndarray:
        out = np.zeros(n, np.float32)
        part = self.signal[self.pos:self.pos + n]
        out[: len(part)] = part
        self.pos += n
        return out


def _probe(unit: Unit, signal: np.ndarray, seconds: float) -> np.ndarray:
    """The unit's output when its source is replaced by signal; its parameters must be fixed."""
    if any(isinstance(v, Unit) for v in getattr(unit, "_values", {}).values()):
        raise ValueError(f"{type(unit).__name__} has a moving parameter; a response needs fixed parameters")
    u = copy.deepcopy(unit)
    u.src = _Probe(signal)
    u.channels = 1
    x = render(u, seconds)
    return x if x.ndim == 1 else x.mean(axis=1)


def _name_where_distinct(ax, lines, labels) -> None:
    """Each line named where it stands furthest from the others (with one line, at its peak)."""
    ys = [np.asarray(line.get_ydata(), float) for line in lines]
    for i, (line, label) in enumerate(zip(lines, labels or [])):
        x, y = line.get_xdata(), ys[i]
        others = [o for j, o in enumerate(ys) if j != i and len(o) == len(y)]
        k = int(np.argmax(np.abs(y - np.mean(others, axis=0)))) if others else int(np.argmax(y))
        ax.annotate(label, (x[k], y[k]), xytext=(6, 6), textcoords="offset points", fontsize=8.5,
                    fontstyle="italic", color=line.get_color())


class Response(View):
    """Gain in dB over frequency on a log axis, from each filter's impulse response."""

    def __init__(self, *filters: Unit, labels: list[str] | None = None, lo: float = 50.0, hi: float = 20000.0,
                 caption=None, id=None):
        super().__init__(caption=caption, id=id)
        self.filters, self.labels, self.lo, self.hi = filters, labels, lo, hi

    def draw(self):
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FuncFormatter

        fig, ax = plt.subplots(figsize=(7.0, 2.6))
        imp = np.zeros(1)
        imp[0] = 1.0
        lines = []
        for i, flt in enumerate(self.filters):
            h = _probe(flt, imp, 1.0)
            f = np.fft.rfftfreq(len(h), 1 / RATE)
            db = 20 * np.log10(np.maximum(np.abs(np.fft.rfft(h)), 1e-9))
            keep = (f >= self.lo) & (f <= self.hi)
            (line,) = ax.plot(f[keep], db[keep], color=SERIES[i % len(SERIES)])
            lines.append(line)
        _name_where_distinct(ax, lines, self.labels)
        ax.set_xscale("log")
        ax.set_xlim(self.lo, self.hi)
        ax.minorticks_off()
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " ")))
        ax.set_ylim(max(ax.get_ylim()[0], -60), ax.get_ylim()[1])
        octave_ruler(ax, self.lo, self.hi)
        cutoffs = {getattr(f, "_values", {}).get("cutoff") for f in self.filters}
        if len(cutoffs) == 1 and isinstance(c := cutoffs.pop(), float):
            ax.axvline(c, color=MADDER, lw=0.6)
            ax.annotate(f"cutoff {c:g} Hz, near {note_name(c)}", (c, 0), xycoords=("data", "axes fraction"),
                        xytext=(4, 4), textcoords="offset points", fontstyle="italic", fontsize=8.5, color=MADDER)
        label_axis(ax, "frequency (Hz)", "gain (dB)")
        return fig


class Curve(View):
    """A waveshaper's transfer curve: each input sample in -1..1 against the output it gives."""

    def __init__(self, *shapers: Unit, labels: list[str] | None = None, caption=None, id=None):
        super().__init__(caption=caption, id=id)
        self.shapers, self.labels = shapers, labels

    def draw(self):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(3.6, 3.2))
        ramp = np.linspace(-1, 1, RATE // 2)
        ax.plot([-1, 1], [-1, 1], color="#9aa0a8", lw=0.5, ls=(0, (1, 2)))
        lines = []
        for i, s in enumerate(self.shapers):
            y = _probe(s, ramp, len(ramp) / RATE)
            (line,) = ax.plot(ramp, y[: len(ramp)], color=SERIES[i % len(SERIES)])
            lines.append(line)
        _name_where_distinct(ax, lines, self.labels)
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.set_aspect("equal", adjustable="box")
        label_axis(ax, "input sample", "output sample")
        return fig


def response(*filters, **kw) -> Response:
    return Response(*filters, **kw)


def curve(*shapers, **kw) -> Curve:
    return Curve(*shapers, **kw)
