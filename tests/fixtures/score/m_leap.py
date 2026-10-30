"""M-LEAP: a sixth up then a third up, and a sixth up then a step down."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:q a4 c5 b4")


def clean() -> Score:
    return _score("c4:q a4 g4 f4")
