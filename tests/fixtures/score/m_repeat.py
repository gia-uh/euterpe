"""M-REPEAT: six Cs, and four."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:q c c c | c c d e")


def clean() -> Score:
    return _score("c4:q c c c | d e f g")
