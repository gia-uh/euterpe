"""M-CONTOUR: known shares, and a one-note line."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:q d e g | e:w")


def clean() -> Score:
    return _score("c4:w")
