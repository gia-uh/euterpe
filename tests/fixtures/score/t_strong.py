"""T-STRONG: a known share on two bars, and a part of rests."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:q d e f | g:h a:e b c5 d5")


def clean() -> Score:
    return _score("R | R")
