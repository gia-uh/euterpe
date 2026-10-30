"""H-ROMAN: I, IV, V, I read as such, and a single line with no chords."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("choir").add(melody(text))
    return s


def trigger() -> Score:
    return _score("<c4 e4 g4>:q <f3 a3 c4> <g3 b3 d4> <c4 e4 g4>")


def clean() -> Score:
    return _score("c4:q d4 e4 f4")
