"""T-PHRASE: 4 + 4 bars, and an unbroken line."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:q d e f | g a g f | e d c d | e d c:h | c:q d e f | g a g f | e d c d | e d c:h")


def clean() -> Score:
    return _score("c4:q d e f | g a g f | e d c d | e d c d | c d e f | g a g f | e d c d | e d c d")
