"""T-DENSITY: known counts, and an empty bar that counts 0."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:q d e f | g:e a b c5 d e f g")


def clean() -> Score:
    return _score("c4:w | R | c4:q d e f")
