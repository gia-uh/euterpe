"""R-ARTIC: a palm mute on a violin, whose articulations do not list it, and on an electric guitar, whose do."""

from fractions import Fraction

from euterpe.instruments import ElectricGuitar, Violin
from euterpe.instruments.core import PalmMute
from euterpe.pitch import A4
from euterpe.score import Line, Note, Rest, Score


def _score(instrument) -> Score:
    s = Score()
    s.part("alto", instrument).add(Line([[Rest(1)], [Rest(Fraction(1, 4)), Note(A4, Fraction(3, 4), articulations=(PalmMute(),))]]))
    return s


def trigger() -> Score:
    return _score(Violin())


def clean() -> Score:
    return _score(ElectricGuitar())
