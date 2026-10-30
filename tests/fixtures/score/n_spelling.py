"""N-SPELLING: G flat in D major, and F sharp."""

from euterpe.score import Score, melody
from euterpe.theory import Key


def _score(text: str) -> Score:
    s = Score(key=Key("D major"))
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("d4:q gb4 a4 d5")


def clean() -> Score:
    return _score("d4:q f#4 a4 d5")
