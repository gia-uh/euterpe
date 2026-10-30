"""N-ARTIC: staccato and palm mute on one note, of which an instrument reads one, and staccato and accent."""

from fractions import Fraction

from euterpe.instruments.core import Accent, Articulation, PalmMute, Staccato
from euterpe.pitch import C4, E4
from euterpe.score import Line, Note, Score


def _score(*articulations: Articulation) -> Score:
    half = Fraction(1, 2)
    s = Score()
    s.part("alto").add(Line([[Note(C4, half), Note(E4, half, articulations=articulations)]]))
    return s


def trigger() -> Score:
    return _score(Staccato(), PalmMute())


def clean() -> Score:
    return _score(Staccato(), Accent())
