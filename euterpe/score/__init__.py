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
from euterpe.score.perform import Dynamics, Humanize, Lengths, Performance, Swing, TempoMap, part_seeds

__all__ = ["BarRest", "Change", "Dynamic", "Dynamics", "Hairpin", "Harmony", "Hit", "Humanize", "Lengths", "Line", "Measure",
           "Note", "Numeral", "Part", "Performance", "Placed", "Ramp", "Rest", "Score", "Section", "Swing", "TempoMap", "Tuplet",
           "arpeggiate", "chords", "drums", "melody", "part_seeds"]
