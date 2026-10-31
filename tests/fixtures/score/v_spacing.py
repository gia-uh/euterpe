"""V-SPACING: the soprano and the alto a tenth apart, and a sixth."""

from euterpe.score import Score, melody


def _score(alto: str) -> Score:
    s = Score()
    s.part("soprano").add(melody("c5:h e5:h"))
    s.part("alto").add(melody(alto))
    s.part("tenor").add(melody("g3:w"))
    s.part("bass").add(melody("c3:w"))
    return s


def trigger() -> Score:
    return _score("c4:w")


def clean() -> Score:
    return _score("g4:w")
