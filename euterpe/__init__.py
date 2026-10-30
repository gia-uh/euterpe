"""Euterpe: compose music by writing code."""

from euterpe.score import Score
from euterpe.theory import (
    Chord,
    EqualTemperament,
    Interval,
    JustIntonation,
    Key,
    Meter,
    Pitch,
    Pythagorean,
    Roman,
    Scale,
    analyze,
    cadence,
)

__all__ = ["Chord", "EqualTemperament", "Interval", "JustIntonation", "Key", "Meter", "Pitch", "Pythagorean", "Roman",
           "Scale", "Score", "analyze", "cadence", "display"]

__version__ = "0.1.0.dev0"


def display(*xs, normalize: bool = True, caption: str | None = None, id: str | None = None) -> None:
    """Show each object's widget through the host's display, at -16 LUFS unless normalize is false."""
    from euterpe.view import display as show

    show(*xs, normalize=normalize, caption=caption, id=id)
