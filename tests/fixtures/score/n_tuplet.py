"""N-TUPLET: two eighths in a triplet, and three."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:q 3[d4:e e4] f4:h")


def clean() -> Score:
    return _score("c4:q 3[d4:e e4 f4] g4:h")
