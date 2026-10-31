"""V-RANGE: the soprano on B5, and on E5."""

from euterpe.score import Score, melody


def _score(top: str) -> Score:
    s = Score()
    s.part("soprano").add(melody(top))
    s.part("alto").add(melody("g4:w"))
    s.part("tenor").add(melody("c4:w"))
    s.part("bass").add(melody("c3:w"))
    return s


def trigger() -> Score:
    return _score("e4:h b5:h")


def clean() -> Score:
    return _score("e4:h e5:h")
