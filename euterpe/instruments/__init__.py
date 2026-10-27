"""Layer 2: instruments that turn notes into sound."""

from euterpe.instruments.core import (
    Accent,
    Articulation,
    Control,
    Instrument,
    Legato,
    Note,
    Staccato,
    play,
)
from euterpe.instruments.phrase import Phrase
from euterpe.instruments.plucked import PluckedString

__all__ = [
    "Accent",
    "Articulation",
    "Control",
    "Instrument",
    "Legato",
    "Note",
    "Phrase",
    "PluckedString",
    "Staccato",
    "play",
]
