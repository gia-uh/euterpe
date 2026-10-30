"""N-TIE: a tie to another pitch, and to the same one."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("g4:h c4:q~ d4:q")


def clean() -> Score:
    return _score("g4:h c4:q~ c4:q")
