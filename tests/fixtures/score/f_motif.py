"""F-MOTIF: a sequence reports its motif, and a scale run reports only steps."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:q d4 e4 c4 | d4 e4 f4 d4 | e4 f4 g4 e4")


def clean() -> Score:
    return _score("c4:q d4 e4 f4 | g4 a4 b4 c5")
