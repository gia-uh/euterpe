"""R-COMFORT: half the note time above the comfortable range, and none of it."""

from euterpe.score import Score, melody
from tests.helpers import Theremin


def _score(text: str) -> Score:
    s = Score()
    s.part("alto", Theremin()).add(melody(text))
    return s


def trigger() -> Score:
    return _score("a4:h d6:h")


def clean() -> Score:
    return _score("a4:h b4:h")
