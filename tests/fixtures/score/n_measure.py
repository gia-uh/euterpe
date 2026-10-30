"""N-MEASURE: five quarters in 4/4, and four."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:w | c4:q d e f g")


def clean() -> Score:
    return _score("c4:w | c4:q d e f")
