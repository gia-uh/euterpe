"""Views of signals: waveform, the default view, spectrum, spectrogram and level."""

from __future__ import annotations

import numpy as np

from euterpe.sound.clip import Clip
from euterpe.sound.core import Unit
from euterpe.view.base import View, sources
from euterpe.view.style import (
    INK, MADDER, PRUSSIAN, RULE, SERIES, default_mark, inkmap, keyboard_strip, label_axis, octave_ruler,
)

_FLOOR = 1e-9  # a level that keeps log10 finite on silence


def _mono(c: Clip) -> np.ndarray:
    return c.samples if c.channels == 1 else c.samples.mean(axis=1)


def _db(x: np.ndarray) -> np.ndarray:
    return 20 * np.log10(np.maximum(np.abs(x), _FLOOR))


def _smooth(f: np.ndarray, p: np.ndarray, fraction: int = 6) -> tuple[np.ndarray, np.ndarray]:
    """Mean power in bands 1/fraction of an octave wide, so a noise spectrum reads as a line."""
    edges = 20.0 * 2 ** (np.arange(0, 11 * fraction + 1) / fraction)
    idx = np.digitize(f, edges)
    fc, pc = [], []
    for i in np.unique(idx):
        sel = idx == i
        if sel.any() and 0 < i < len(edges):
            fc.append(float(np.sqrt(edges[i - 1] * edges[i])))
            pc.append(float(p[sel].mean()))
    return np.array(fc), np.array(pc)


def _plain_log_ticks(ax) -> None:
    from matplotlib.ticker import FuncFormatter

    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " ")))


def _mark_default(clips, ax) -> None:
    for c in clips:
        if c.defaulted:
            default_mark(ax, c.seconds)
            return


def _channels(c: Clip) -> list[np.ndarray]:
    return [c.samples] if c.channels == 1 else [c.samples[:, k] for k in range(c.channels)]


def _power(c: Clip) -> np.ndarray:
    """Power per sample, summed over the channels, so a panned sound keeps its level."""
    return sum(ch.astype(np.float64) ** 2 for ch in _channels(c))


_SHORT = 16  # fewer samples than this cannot be measured in frequency


def _too_short(ax, clips) -> bool:
    if all(len(c) >= _SHORT for c in clips):
        return False
    ax.text(0.5, 0.5, "too short to measure", transform=ax.transAxes, ha="center", va="center",
            fontstyle="italic", fontsize=9, color=RULE)
    return True


def _draw_marks(ax, marks, scale=1.0, labels=True) -> None:
    """(time, label) pairs as dotted rules, with their label at the top when labels is true."""
    for t, label in marks:
        ax.axvline(t * scale, color=RULE, lw=0.6, ls=(0, (1, 2)))
        if labels:
            ax.annotate(label, (t * scale, 1), xycoords=("data", "axes fraction"), xytext=(3, -2),
                        textcoords="offset points", va="top", fontsize=8.5, fontstyle="italic", color=MADDER)


def _name_lines(ax, lines, labels) -> None:
    """Each series named in its own ink at the right end of its line, instead of a legend; labels
    that would touch are pushed apart vertically."""
    ax.autoscale_view()
    gap = 13 * ax.figure.dpi / 72  # 13 pt between label centres: an 8.5 pt label with its line gap
    ends = []
    for line, label in zip(lines, labels or []):
        x, y = line.get_xdata(), line.get_ydata()
        if len(x):
            ends.append((ax.transData.transform((x[-1], y[-1]))[1], x[-1], y[-1], label, line.get_color()))
    ends.sort()
    placed = []
    for disp_y, x, y, label, color in ends:
        target = disp_y if not placed else max(disp_y, placed[-1] + gap)
        placed.append(target)
        ax.annotate(label, (x, y), xytext=(4, (target - disp_y) * 72 / ax.figure.dpi), textcoords="offset points",
                    va="center", fontsize=8.5, fontstyle="italic", color=color)


class _Many(View):
    def __init__(self, *xs: Unit | Clip, labels: list[str] | None = None, caption=None, id=None):
        super().__init__(caption=caption, id=id)
        self.clips = sources(*xs)
        self.labels = labels


class Waveform(_Many):
    """Pressure over time in a window. Several sources overlay, or with separate=True get a panel
    each; reference is drawn in grey under every source; samples=True marks each sample; marks
    are (time, label) pairs drawn as dotted rules."""

    def __init__(self, *xs, span: tuple[float, float] | None = None, samples: bool = False,
                 separate: bool = False, reference: Unit | Clip | None = None,
                 marks: list[tuple[float, str]] | None = None, **kw):
        super().__init__(*xs, **kw)
        self.span, self.samples, self.separate, self.marks = span, samples, separate, marks or []
        self.reference = sources(reference)[0] if reference is not None else None

    def _plot(self, ax, c, color, lo, hi, scale, alpha=1.0, lw=1.0, dots=False):
        a, b = round(lo * c.rate), round(hi * c.rate)
        seg = c.samples[a:b]
        t = (np.arange(a, a + len(seg)) / c.rate) * scale
        chans = [seg] if c.channels == 1 else [seg[:, 0], seg[:, 1]]
        first = None
        for k, ch in enumerate(chans):
            if dots:
                ax.plot(t, ch, color=RULE, lw=0.6)
                (line,) = ax.plot(t, ch, "o", color=color, ms=3)
            else:
                (line,) = ax.plot(t, ch, color=color, lw=lw, alpha=alpha if k == 0 else alpha * 0.5)
            first = first or line
        return first

    def draw(self):
        import matplotlib.pyplot as plt

        lo, hi = self.span or (0.0, max(c.seconds for c in self.clips))
        hi = max(hi, lo + 1 / self.clips[0].rate)
        ms = hi - lo <= 0.1
        scale = 1000 if ms else 1
        k = len(self.clips) if self.separate else 1
        fig, axes = plt.subplots(k, 1, figsize=(self.width, 2.4 if k == 1 else 0.6 + 1.1 * k), sharex=True,
                                 sharey=True, squeeze=False)
        axes = axes[:, 0]
        lines = []
        for i, c in enumerate(self.clips):
            ax = axes[i if self.separate else 0]
            if self.reference is not None and (self.separate or i == 0):
                self._plot(ax, self.reference, RULE, lo, hi, scale, lw=0.8)
            lines.append((ax, self._plot(ax, c, SERIES[i % len(SERIES)], lo, hi, scale, dots=self.samples)))
        for k, ax in enumerate(axes):
            ax.axhline(0, color=RULE, lw=0.4, zorder=0)
            _draw_marks(ax, self.marks, scale, labels=k == 0)
            ax.spines["left"].set_position(("outward", 4))
        ax0 = axes[0]
        ax0.set_xlim(lo * scale, hi * scale)
        if self.separate:
            for (ax, line), label in zip(lines, self.labels or []):
                ax.text(1.0, 0.85, label, transform=ax.transAxes, ha="right", va="top", fontstyle="italic",
                        fontsize=9.5, color=line.get_color())
        else:
            _name_lines(ax0, [line for _, line in lines], self.labels)
        label_axis(axes[-1], "time (ms)" if ms else "time (s)")
        axes[len(axes) // 2].set_ylabel("pressure", fontstyle="italic")
        _mark_default(self.clips, ax0)
        return fig


class Spectrum(_Many):
    """Level over frequency. With f0, one numbered stem per harmonic, each source its own panel;
    without, a smoothed line on a log axis, sources overlaid."""

    def __init__(self, *xs, upto: float = 6000.0, f0: float | None = None, harmonics: int | None = None, **kw):
        super().__init__(*xs, **kw)
        self.upto, self.f0, self.harmonics = upto, f0, harmonics

    def _stems(self, ax, c, color):
        ax.set_ylim(-60, 8)
        ax.set_yticks([-60, -30, 0])
        if _too_short(ax, [c]):
            return
        win = np.hanning(len(c))
        mag = np.sqrt(sum(np.abs(np.fft.rfft(ch * win)) ** 2 for ch in _channels(c))) / max(win.sum() / 2, 1e-12)
        f = np.fft.rfftfreq(len(c), 1 / c.rate)
        n = self.harmonics or int(self.upto // self.f0)
        for h in range(1, n + 1):
            fh = self.f0 * h
            if fh > self.upto:
                break
            k = int(np.argmin(np.abs(f - fh)))
            db = float(_db(mag[max(0, k - 3):k + 4].max())[()])
            if db < -60:
                continue
            ax.plot([fh, fh], [-60, db], color=color, lw=1.3)
            ax.plot(fh, db, "o", ms=3.2, color=color)
            if h <= 5:
                ax.annotate(str(h), (fh, db), xytext=(0, 3), textcoords="offset points", ha="center",
                            fontsize=7, color=color)

    def draw(self):
        import matplotlib.pyplot as plt
        from scipy.signal import welch

        if self.f0:
            k = len(self.clips)
            fig, axes = plt.subplots(k, 1, figsize=(self.width, 1.0 + 1.15 * k), sharex=True, squeeze=False,
                                     gridspec_kw={"hspace": 0.35})
            axes = axes[:, 0]
            for i, (c, ax) in enumerate(zip(self.clips, axes)):
                color = SERIES[i % len(SERIES)]
                self._stems(ax, c, color)
                if self.labels:
                    ax.text(1.0, 0.55, self.labels[i], transform=ax.transAxes, ha="right", fontstyle="italic",
                            color=color, fontsize=10)
                octave_ruler(ax, max(self.f0 * 1.5, 20), self.upto, names=i == 0)
                ax.spines["left"].set_position(("outward", 4))
            axes[-1].set_xlim(0, self.upto)
            label_axis(axes[-1], "frequency (Hz)")
            axes[len(axes) // 2].set_ylabel("level (dB)", fontstyle="italic")
            _mark_default(self.clips, axes[0])
            return fig
        fig, ax = plt.subplots(figsize=(self.width, 2.6))
        lines = []
        for i, c in enumerate(self.clips):
            if len(c) < _SHORT:
                continue
            nper = min(8192, len(c))
            f, p = welch(np.stack(_channels(c)), fs=c.rate, nperseg=nper, axis=-1)
            p = p.sum(axis=0)
            keep = (f >= 20) & (f <= self.upto)
            fc, pc = _smooth(f[keep], p[keep])
            db = 10 * np.log10(np.maximum(pc, _FLOOR ** 2))
            (line,) = ax.plot(fc, db, color=SERIES[i % len(SERIES)], lw=1.2)
            lines.append(line)
        _too_short(ax, self.clips)
        ax.set_xscale("log")
        ax.set_xlim(20, self.upto)
        ax.minorticks_off()
        _plain_log_ticks(ax)
        octave_ruler(ax, 20, self.upto)
        _name_lines(ax, lines, self.labels)
        label_axis(ax, "frequency (Hz)", "level (dB)")
        _mark_default(self.clips, ax)
        return fig


class Spectrogram(_Many):
    """Frequency over time on a log axis with a keyboard; level is ink density."""

    def __init__(self, *xs, lo: float = 55.0, hi: float = 4000.0, **kw):
        super().__init__(*xs, **kw)
        self.lo, self.hi = lo, hi

    def draw(self):
        import matplotlib.pyplot as plt
        from scipy.signal import spectrogram as stft

        k = len(self.clips)
        fig, axes = plt.subplots(1, k, figsize=(self.width, 2.8), sharey=True, squeeze=False,
                                 gridspec_kw={"wspace": 0.12})
        for i, (c, ax) in enumerate(zip(self.clips, axes[0])):
            if _too_short(ax, [c]):
                continue
            nper = min(4096, max(8, len(c) // 4))
            f, t, s = stft(np.stack(_channels(c)), fs=c.rate, nperseg=nper, noverlap=nper * 7 // 8, axis=-1)
            db = 10 * np.log10(np.maximum(s.sum(axis=0), _FLOOR ** 2))
            db -= max(float(db.max()), 10 * np.log10(_FLOOR ** 2) + 70)
            keep = (f >= self.lo * 0.9) & (f <= self.hi * 1.1)
            ax.pcolormesh(t, f[keep], np.clip(db[keep], -70, 0), cmap=inkmap(), shading="gouraud",
                          vmin=-70, vmax=0, rasterized=True)
            ax.set_yscale("log")
            ax.set_ylim(self.lo, self.hi)
            ax.set_yticks([])

            ax.minorticks_off()
            ax.spines["left"].set_visible(False)
            ax.spines["bottom"].set_position(("outward", 4))
            ax.set_xlabel("time (s)", fontstyle="italic")
            if i == 0:
                keyboard_strip(ax, self.lo, self.hi)
            if self.labels:
                ax.set_title(self.labels[i], fontstyle="italic", fontsize=9.5, color=INK, loc="left")
        _mark_default(self.clips, axes[0][-1])
        return fig


class Level(_Many):
    """Level in dBFS over time, one step every `every` seconds; marks as in Waveform."""

    def __init__(self, *xs, every: float = 0.01, marks: list[tuple[float, str]] | None = None, **kw):
        super().__init__(*xs, **kw)
        self.every, self.marks = every, marks or []

    def draw(self):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(self.width, 2.4))
        lines = []
        for i, c in enumerate(self.clips):
            pw = _power(c)
            size = min(max(1, round(self.every * c.rate)), max(1, len(pw)))
            frames = pw[: len(pw) // size * size].reshape(-1, size)
            db = 10 * np.log10(np.maximum(frames.mean(axis=1), _FLOOR ** 2))
            t = np.arange(len(db)) * self.every
            (line,) = ax.step(t, db, where="post", color=SERIES[i % len(SERIES)], lw=1.1)
            lines.append(line)
        ax.set_xlim(0, max(max(c.seconds for c in self.clips), 1 / self.clips[0].rate))
        top = max((float(np.nanmax(line.get_ydata())) for line in lines if len(line.get_ydata())), default=0.0)
        ax.set_ylim(max(ax.get_ylim()[0], top - 80), top + 3)
        _draw_marks(ax, self.marks)
        _name_lines(ax, lines, self.labels)
        label_axis(ax, "time (s)", "level (dBFS)")
        _mark_default(self.clips, ax)
        return fig


def waveform(*xs, **kw) -> Waveform:
    return Waveform(*xs, **kw)


def default(x, **kw):
    """What display(x) shows: the widget."""
    from euterpe.view.widget import Widget

    return Widget(x, **kw)


def spectrum(*xs, **kw) -> Spectrum:
    return Spectrum(*xs, **kw)


def spectrogram(*xs, **kw) -> Spectrogram:
    return Spectrogram(*xs, **kw)


def level(*xs, **kw) -> Level:
    return Level(*xs, **kw)
