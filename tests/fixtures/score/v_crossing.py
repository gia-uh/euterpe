"""V-CROSSING: the alto above the soprano, and below it."""

from euterpe.score import Score, melody


def _score(alto: str) -> Score:
    s = Score()
    s.part("soprano").add(melody("e5:w"))
    s.part("alto").add(melody(alto))
    return s


def trigger() -> Score:
    return _score("c5:h g5:h")


def clean() -> Score:
    return _score("c5:h d5:h")
