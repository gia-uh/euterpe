"""T-SYNCOPATION: a tied off-beat, and quarters on the beat."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:e d4:q~ d4:e e4:q f4:q")


def clean() -> Score:
    return _score("c4:q d e f")
