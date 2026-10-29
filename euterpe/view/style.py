"""The house style of every view: printing inks on white paper, the book's serif, and a
keyboard on every frequency axis. Spec section 06."""

from __future__ import annotations

from pathlib import Path

import numpy as np

INK = "#1e2430"  # iron-gall blue-black: lines, text
PRUSSIAN = "#1f5f8b"  # first series
MADDER = "#b0361f"  # what the text points at, at most one thing per figure
VERDIGRIS = "#2f7d6d"  # third series
OCHRE = "#b8862b"  # fourth series
RULE = "#9aa0a8"  # hairlines, octave rules, a reference series
WASH = "#e8edf2"  # the faintest ink, for fills
SERIES = (PRUSSIAN, MADDER, VERDIGRIS, OCHRE)
NOTE_NAMES = ("C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B")

_FONTS = Path(__file__).parent / "fonts"
_registered = False


def fonts() -> None:
    """Register the bundled Source Serif 4 with matplotlib, once."""
    global _registered
    if not _registered:
        from matplotlib import font_manager

        for f in sorted(_FONTS.glob("*.ttf")):
            font_manager.fontManager.addfont(str(f))
        _registered = True


def inkmap():
    """Spectrogram ink: level is ink density, silence is paper."""
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list("ink", [(0, "#ffffff"), (0.35, "#c9d6e3"), (0.7, PRUSSIAN), (1, INK)])


def rc() -> dict:
    """matplotlib settings for every view; svg.fonttype and hashsalt make the SVG deterministic."""
    from cycler import cycler

    return {
        "font.family": ["Source Serif 4", "DejaVu Serif", "DejaVu Sans"],
        "font.size": 9.5,
        "axes.labelsize": 9.5,
        "axes.labelcolor": INK,
        "axes.edgecolor": INK,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.facecolor": "none",
        "axes.prop_cycle": cycler(color=list(SERIES)),
        "figure.facecolor": "#ffffff",  # a white plate in both of the book's themes, as the widget
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "lines.linewidth": 1.1,
        "lines.solid_capstyle": "round",
        "svg.fonttype": "path",
        "svg.hashsalt": "euterpe",
    }


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def note_name(freq: float) -> str:
    """The nearest equal-tempered note, as C♯4."""
    m = int(round(69 + 12 * np.log2(freq / 440.0)))
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"


def label_axis(ax, x: str | None = None, y: str | None = None) -> None:
    """Italic axis labels, and the left and bottom axes moved 4 pt off the data."""
    if x:
        ax.set_xlabel(x, fontstyle="italic")
    if y:
        ax.set_ylabel(y, fontstyle="italic")
    for side in ("left", "bottom"):
        ax.spines[side].set_position(("outward", 4))


def octave_ruler(ax, lo: float, hi: float, names: bool = True) -> None:
    """A dotted hairline at every A between lo and hi Hz, named above the axes."""
    for m in range(21, 120, 12):
        f = hz(m)
        if lo <= f <= hi:
            ax.axvline(f, color=RULE, lw=0.4, ls=(0, (1, 2)), zorder=0)
            if names:
                ax.annotate(note_name(f), (f, 1), xycoords=("data", "axes fraction"), xytext=(0, 3),
                            textcoords="offset points", ha="center", va="bottom", fontsize=7.5,
                            fontstyle="italic", color=RULE)


def keyboard_strip(ax, lo: float, hi: float, width: float = 0.022) -> None:
    """A piano along a log-frequency y axis, just outside the left edge, each A named."""
    from matplotlib.patches import Rectangle

    for m in range(12, 128):
        f0, f1 = hz(m - 0.5), hz(m + 0.5)
        if f1 < lo or f0 > hi:
            continue
        black = NOTE_NAMES[m % 12].endswith("♯")
        ax.add_patch(Rectangle((-width - 0.006, max(f0, lo)), width * (0.6 if black else 1), min(f1, hi) - max(f0, lo),
                               transform=ax.get_yaxis_transform(), clip_on=False,
                               facecolor=INK if black else "white", edgecolor=RULE, lw=0.25))
        if NOTE_NAMES[m % 12] == "A" and lo <= hz(m) <= hi:
            ax.annotate(note_name(hz(m)), (-width - 0.012, hz(m)), xycoords=("axes fraction", "data"),
                        ha="right", va="center", fontsize=7.5, fontstyle="italic", color=INK)


def default_mark(ax, seconds: float = 1.0) -> None:
    """Say on the drawing that its length is a default, not a choice."""
    ax.text(1.0, 1.02, f"{seconds:g} s (default)", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7.5, fontstyle="italic", color=RULE)
