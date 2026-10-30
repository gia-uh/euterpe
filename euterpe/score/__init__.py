"""Layer 3: the score. Written time in Fractions of a whole note, in the keys and meters of euterpe.theory."""

from euterpe.score.model import (
    BarRest,
    Change,
    Dynamic,
    Hairpin,
    Harmony,
    Hit,
    Line,
    Measure,
    Note,
    Numeral,
    Part,
    Placed,
    Ramp,
    Rest,
    Score,
    Section,
    Tuplet,
)
from euterpe.score.notation import arpeggiate, chords, drums, melody

__all__ = ["BarRest", "Change", "Dynamic", "Hairpin", "Harmony", "Hit", "Line", "Measure", "Note", "Numeral", "Part",
           "Placed", "Ramp", "Rest", "Score", "Section", "Tuplet", "arpeggiate", "chords", "drums", "melody"]
