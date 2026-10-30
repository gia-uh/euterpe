"""M-RANGE: two octaves and a third, and a tenth."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:w | e6:w")


def clean() -> Score:
    return _score("c4:w | e5:w")
