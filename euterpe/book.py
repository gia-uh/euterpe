"""Helpers for the book's executed code blocks. Players and figures come from euterpe.view."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from euterpe.sound.core import Unit, render
from euterpe.sound.osc import Sine


def gain_db(filter: Callable[[Unit], Unit], freq: float) -> float:
    """The gain, in dB rounded to 0.1, that filter (a function from a source to the filtered
    source) gives a sine at freq Hz: peak out over peak in, after the first 0.1 s."""
    dry = render(Sine(freq), 0.5)[4800:]
    wet = render(filter(Sine(freq)), 0.5)[4800:]
    return round(float(20 * np.log10(np.abs(wet).max() / np.abs(dry).max())), 1) + 0.0
