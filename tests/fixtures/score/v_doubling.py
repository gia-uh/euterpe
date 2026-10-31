"""V-DOUBLING: B in the soprano and the tenor over G, and B once."""

from euterpe.score import Score, melody


def _score(tenor: str) -> Score:
    s = Score()
    s.part("soprano").add(melody("b4:w"))
    s.part("alto").add(melody("g4:w"))
    s.part("tenor").add(melody(tenor))
    s.part("bass").add(melody("g2:w"))
    return s


def trigger() -> Score:
    return _score("g3:h b3:h")


def clean() -> Score:
    return _score("g3:h d4:h")
