"""V-PARALLEL: a four-bar chorale with parallel fifths from the alto to the soprano in bar 3, and its corrected version."""

from euterpe.score import Score, melody


def _score(alto: str) -> Score:
    s = Score()
    s.part("soprano").add(melody("e5:q d5 c5 b4 | c5 c5 b4 c5 | a4 b4 c5 b4 | c5:w"))
    s.part("alto").add(melody(f"g4:q g4 g4 g4 | g4 a4 g4 e4 | {alto} e4 d4 | e4:w"))
    s.part("tenor").add(melody("c4:q d4 e4 d4 | e4 f4 d4 c4 | f3 g3 g3 g3 | g3:w"))
    s.part("bass").add(melody("c3:q b2 c3 g3 | c3 f3 g3 c3 | d3 c3 c3 g2 | c3:w"))
    return s


def trigger() -> Score:
    return _score("d4:q e4")


def clean() -> Score:
    return _score("f4:q e4")
