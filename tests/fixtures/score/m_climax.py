"""M-CLIMAX: the top note three times in a phrase, and once."""

from euterpe.score import Score, melody


def _score(text: str) -> Score:
    s = Score()
    s.part("alto").add(melody(text))
    return s


def trigger() -> Score:
    return _score("c4:q g4 e4 g4 | e4 g4 d4 c4")


def clean() -> Score:
    return _score("c4:q d4 e4 g4 | f4 e4 d4 c4")
