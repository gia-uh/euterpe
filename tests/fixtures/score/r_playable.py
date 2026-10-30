"""R-PLAYABLE: a note above the instrument's top, and one inside its range."""

from euterpe.score import Score, melody
from tests.helpers import Theremin


def _score(text: str) -> Score:
    s = Score()
    s.part("alto", Theremin()).add(melody(text))
    return s


def trigger() -> Score:
    return _score("a4:w | a4:h b7:h")


def clean() -> Score:
    return _score("a4:w | a4:h b4:h")
