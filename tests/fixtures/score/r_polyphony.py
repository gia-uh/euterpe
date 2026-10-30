"""R-POLYPHONY: three notes at once on a one-voice instrument, and one at a time."""

from euterpe.score import Score, melody
from tests.helpers import Theremin


def _score(text: str) -> Score:
    s = Score()
    s.part("alto", Theremin()).add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:h <c4 e4 g4>:h")


def clean() -> Score:
    return _score("c4:h e4:h")
