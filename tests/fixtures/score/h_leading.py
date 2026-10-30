"""H-LEADING: B to G in the soprano over V to I, and B to C."""

from euterpe.score import Score, melody


def _score(top: str) -> Score:
    s = Score()
    s.part("soprano").add(melody(top))
    s.part("lower").add(melody("<g3 d4>:h <c4 e4>:h"))
    return s


def trigger() -> Score:
    return _score("b4:h g4:h")


def clean() -> Score:
    return _score("b4:h c5:h")
