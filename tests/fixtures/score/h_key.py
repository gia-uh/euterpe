"""H-KEY: a C sharp in C major, and a diatonic line."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:q c#4 d4 e4")


def clean() -> Score:
    return _score("c4:q d4 e4 f4")
