"""V-DIRECT: the soprano leaps to an octave over the bass, and steps to it."""

from euterpe.score import Score, melody


def _score(top: str) -> Score:
    s = Score()
    s.part("soprano").add(melody(top))
    s.part("bass").add(melody("a3:h c4:h"))
    return s


def trigger() -> Score:
    return _score("g4:h c5:h")


def clean() -> Score:
    return _score("b4:h c5:h")
