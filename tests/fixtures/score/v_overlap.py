"""V-OVERLAP: the tenor jumps above the alto's last note, and stays below it."""

from euterpe.score import Score, melody


def _score(tenor: str) -> Score:
    s = Score()
    s.part("alto").add(melody("e4:h g4:h"))
    s.part("tenor").add(melody(tenor))
    return s


def trigger() -> Score:
    return _score("c4:h f4:h")


def clean() -> Score:
    return _score("c4:h d4:h")
