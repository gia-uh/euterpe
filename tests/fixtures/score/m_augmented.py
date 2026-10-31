"""M-AUGMENTED: F to B, and F to C with G sharp to A."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("f4:q b4 c5 d5")


def clean() -> Score:
    return _score("f4:q c5 g#4 a4")
