"""F-REPEAT: a section and its variation hold much in common, and two different sections little."""

from euterpe.score import Score, melody

_A = "c4:q d4 e4 c4 | g4 f4 e4 d4"


def _score(second: str) -> Score:
    s = Score()
    s.part("alto").add(melody(f"{_A} | {second}"))
    s.section("A", 1, 2)
    s.section("B", 3, 4)
    return s


def trigger() -> Score:
    return _score("c4:q d4 e4 c4 | g4 f4 e4 c4")


def clean() -> Score:
    return _score("c5:q g4 c4 g4 | e5:q b4 f5 a4")
