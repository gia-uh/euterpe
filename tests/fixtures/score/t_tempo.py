"""T-TEMPO: 90 bpm, and 130."""

from euterpe.score import Score, melody


def _score(tempo: float) -> Score:
    s = Score(tempo=tempo)
    s.part("alto").add(melody("c4:w"))
    return s


def trigger() -> Score:
    return _score(90)


def clean() -> Score:
    return _score(130)
