"""T-FOURFLOOR: a kick on 1 and 3, and on all four."""

from euterpe.score import Score, drums


def _score(row: str) -> Score:
    s = Score()
    s.part("drums").add(drums({"kick": row}, step="q"))
    return s


def trigger() -> Score:
    return _score("x.x.")


def clean() -> Score:
    return _score("xxxx")
