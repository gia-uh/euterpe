"""H-SEVENTH: the F of G7 rising to G, and falling to E."""

from euterpe.score import Score, melody


def _score(top: str) -> Score:
    s = Score()
    s.part("alto").add(melody(top))
    s.part("lower").add(melody("<g3 b3 d4>:h <c3 g3 c4>:h"))
    return s


def trigger() -> Score:
    return _score("f4:h g4:h")


def clean() -> Score:
    return _score("f4:h e4:h")
