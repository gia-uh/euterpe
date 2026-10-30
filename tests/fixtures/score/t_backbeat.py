"""T-BACKBEAT: a snare on 1 and 3, and on 2 and 4."""

from euterpe.score import Score, drums


def _score(row: str) -> Score:
    s = Score()
    s.part("drums").add(drums({"snare": row}, step="q"))
    return s


def trigger() -> Score:
    return _score("x.x. | x.x.")


def clean() -> Score:
    return _score(".x.x | .x.x")
