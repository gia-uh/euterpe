"""H-CADENCE: ending on ii, and ending V to I with the tonic on top."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("choir").add(melody(text))
    return s


def trigger() -> Score:
    return _score("<c4 e4 g4>:h <d4 f4 a4>:h")


def clean() -> Score:
    return _score("<g3 b3 d4 g4>:h <c3 g3 e4 c5>:h")
