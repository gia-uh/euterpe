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
    if any(c.defaulted for c in clips):
        default_mark(ax)


def _name_lines(ax, lines, labels) -> None:
    """Each series named in its own ink at the right end of its line, instead of a legend."""
    for line, label in zip(lines, labels or []):
        x, y = line.get_xdata(), line.get_ydata()
        if len(x):
            ax.annotate(label, (x[-1], y[-1]), xytext=(4, 0), textcoords="offset points", va="center",
                        fontsize=8.5, fontstyle="italic", color=line.get_color())


def _period(x: np.ndarray, rate: int) -> float | None:
    """The period in seconds, from the strongest autocorrelation peak between 30 and 2000 Hz."""
    seg = x[: min(len(x), 8192)]
    if len(seg) < 1024 or not np.any(seg):
        return None
    seg = seg - seg.mean()
    ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
    lo, hi = rate // 2000, min(rate // 30, len(ac) - 1)
    if hi <= lo or ac[0] <= 0:
        return None
    k = lo + int(np.argmax(ac[lo:hi]))
    return k / rate if ac[k] > 0.3 * ac[0] else None


class _Many(View):
    def __init__(self, *xs: Unit | Clip, labels: list[str] | None = None, caption=None, id=None):
        super().__init__(caption=caption, id=id)
        self.clips = sources(*xs)
        self.labels = labels


class Waveform(_Many):
    """Pressure over time in a window; samples=True marks each sample."""

    def __init__(self, *xs, span: tuple[float, float] | None = None, samples: bool = False, **kw):
        super().__init__(*xs, **kw)
        self.span, self.samples = span, samples

    def draw(self):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7.0, 2.4))
        lo, hi = self.span or (0.0, max(c.seconds for c in self.clips))
        ms = hi - lo <= 0.1
        scale = 1000 if ms else 1
        lines = []
        for i, c in enumerate(self.clips):
            a, b = round(lo * c.rate), round(hi * c.rate)
            seg = c.samples[a:b]
            t = (np.arange(a, a + len(seg)) / c.rate) * scale
            color = SERIES[i % len(SERIES)]
            chans = [seg] if c.channels == 1 else [seg[:, 0], seg[:, 1]]
            for k, ch in enumerate(chans):
                (line,) = ax.plot(t, ch, color=color, lw=1.0, alpha=1.0 if k == 0 else 0.5,
                                  marker="o" if self.samples else None, ms=3)
                if k == 0:
                    lines.append(line)
        ax.axhline(0, color=RULE, lw=0.4, zorder=0)
        ax.set_xlim(lo * scale, hi * scale)
        _name_lines(ax, lines, self.labels)
        label_axis(ax, "time (ms)" if ms else "time (s)", "pressure")
        _mark_default(self.clips, ax)
        return fig


class Default(View):
    """What display(x) shows: the waveform, or for a clip over 50 ms the whole clip as an envelope
    with three cycles magnified; and the player."""

    def __init__(self, x: Unit | Clip, *, caption=None, id=None):
        super().__init__(caption=caption, id=id)
        self.audio = sources(x)[0]

    def draw(self):
        import matplotlib.pyplot as plt
        from matplotlib.patches import ConnectionPatch, Rectangle

        c = self.audio
        x = _mono(c)
        if c.seconds <= 0.05:
            fig = Waveform(c).draw()
            return fig
        fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 2.3), gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.28})
        hop = max(1, len(x) // 600)
        env = np.abs(x[: len(x) // hop * hop]).reshape(-1, hop).max(axis=1)
        te = np.arange(len(env)) * hop / c.rate
        top = max(float(env.max()) * 1.1, 1e-3)
        a.fill_between(te, -env, env, color=PRUSSIAN, alpha=0.18, lw=0)
        a.plot(te, env, color=PRUSSIAN, lw=0.8)
        a.plot(te, -env, color=PRUSSIAN, lw=0.8)
        a.set_xlim(0, c.seconds)
        a.set_ylim(-top, top)
        label_axis(a, "time (s)", "pressure")
        z0 = max(0.05, 0.2 * c.seconds)
        z0 = min(z0, c.seconds - 0.01)
        i0 = round(z0 * c.rate)
        period = _period(x[i0:], c.rate)
        width = 3 * period if period else 0.01
        n = max(2, round(width * c.rate))
        seg = x[i0:i0 + n]
        t = (np.arange(i0, i0 + len(seg)) / c.rate) * 1000
        b.plot(t, seg, color=INK, lw=1.0)
        lim = max(float(np.abs(seg).max()) * 1.15, 1e-3)
        b.set_xlim(t[0], t[-1])
        b.set_ylim(-lim, lim)
        b.spines["left"].set_color(MADDER)
        b.spines["bottom"].set_color(MADDER)
        label_axis(b, "time (ms)")
        a.add_patch(Rectangle((z0, -top), width, 2 * top, facecolor=MADDER, alpha=0.25, edgecolor=MADDER, lw=0.8))
        for y in (top, -top):
            fig.add_artist(ConnectionPatch((z0 + width, y), (0, (y / top + 1) / 2), "data", "axes fraction",
                                           axesA=a, axesB=b, color=MADDER, lw=0.5, ls=(0, (2, 2))))
        what = "three cycles" if period else "10 ms"
        b.text(1.0, 1.04, f"{what} at {z0:.2g} s, magnified", transform=b.transAxes, ha="right", va="bottom",
               fontstyle="italic", fontsize=8.5, color=MADDER)
        if c.defaulted:
            default_mark(a)
        return fig


class Spectrum(_Many):
    """Level over frequency. With f0, one numbered stem per harmonic, each source its own panel;
    without, a smoothed line on a log axis, sources overlaid."""

    def __init__(self, *xs, upto: float = 6000.0, f0: float | None = None, harmonics: int | None = None, **kw):
        super().__init__(*xs, **kw)
        self.upto, self.f0, self.harmonics = upto, f0, harmonics

    def _stems(self, ax, c, color):
        x = _mono(c)
        win = np.hanning(len(x))
        mag = np.abs(np.fft.rfft(x * win)) / max(win.sum() / 2, 1e-12)
        f = np.fft.rfftfreq(len(x), 1 / c.rate)
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
        ax.set_ylim(-60, 8)
        ax.set_yticks([-60, -30, 0])

    def draw(self):
        import matplotlib.pyplot as plt
        from scipy.signal import welch

        if self.f0:
            k = len(self.clips)
            fig, axes = plt.subplots(k, 1, figsize=(7.0, 1.0 + 1.15 * k), sharex=True, squeeze=False,
                                     gridspec_kw={"hspace": 0.35})
            axes = axes[:, 0]
            for i, (c, ax) in enumerate(zip(self.clips, axes)):
                color = SERIES[i % len(SERIES)]
                self._stems(ax, c, color)
                if self.labels:
                    ax.text(1.0, 0.55, self.labels[i], transform=ax.transAxes, ha="right", fontstyle="italic",
                            color=color, fontsize=10)
                octave_ruler(ax, max(self.f0 * 0.9, 20), self.upto, names=i == 0)
                ax.spines["left"].set_position(("outward", 4))
            axes[-1].set_xlim(0, self.upto)
            label_axis(axes[-1], "frequency (Hz)")
            axes[len(axes) // 2].set_ylabel("level (dB)", fontstyle="italic")
            _mark_default(self.clips, axes[0])
            return fig
        fig, ax = plt.subplots(figsize=(7.0, 2.6))
        lines = []
        for i, c in enumerate(self.clips):
            x = _mono(c)
            nper = min(8192, max(256, len(x)))
            f, p = welch(x, fs=c.rate, nperseg=nper)
            keep = (f >= 20) & (f <= self.upto)
            fc, pc = _smooth(f[keep], p[keep])
            db = 10 * np.log10(np.maximum(pc, _FLOOR ** 2))
            (line,) = ax.plot(fc, db, color=SERIES[i % len(SERIES)], lw=1.2)
            lines.append(line)
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
        fig, axes = plt.subplots(1, k, figsize=(7.0, 2.8), sharey=True, squeeze=False,
                                 gridspec_kw={"wspace": 0.12})
        for i, (c, ax) in enumerate(zip(self.clips, axes[0])):
            x = _mono(c)
            nper = min(4096, max(256, len(x) // 4))
            f, t, s = stft(x, fs=c.rate, nperseg=nper, noverlap=nper * 7 // 8)
            db = 10 * np.log10(np.maximum(s, _FLOOR ** 2))
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
    """Level in dBFS over time, one step every `every` seconds."""

    def __init__(self, *xs, every: float = 0.01, **kw):
        super().__init__(*xs, **kw)
        self.every = every

    def draw(self):
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7.0, 2.4))
        lines = []
        for i, c in enumerate(self.clips):
            x = _mono(c)
            size = max(1, round(self.every * c.rate))
            frames = x[: len(x) // size * size].reshape(-1, size)
            db = 10 * np.log10(np.maximum((frames ** 2).mean(axis=1), _FLOOR ** 2))
            t = np.arange(len(db)) * self.every
            (line,) = ax.step(t, db, where="post", color=SERIES[i % len(SERIES)], lw=1.1)
            lines.append(line)
        ax.set_xlim(0, max(c.seconds for c in self.clips))
        _name_lines(ax, lines, self.labels)
        label_axis(ax, "time (s)", "level (dBFS)")
        _mark_default(self.clips, ax)
        return fig


def waveform(*xs, **kw) -> Waveform:
    return Waveform(*xs, **kw)


def default(x, **kw) -> Default:
    return Default(x, **kw)


def spectrum(*xs, **kw) -> Spectrum:
    return Spectrum(*xs, **kw)


def spectrogram(*xs, **kw) -> Spectrogram:
    return Spectrogram(*xs, **kw)


def level(*xs, **kw) -> Level:
    return Level(*xs, **kw)
