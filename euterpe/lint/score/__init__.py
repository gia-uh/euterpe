"""Rules that read a score: one module per group, each usable under a profile."""

from euterpe.lint.score import instrument, notation
from euterpe.lint.score.core import Rule, VoiceLine, lines, lint_piece, lint_score
from euterpe.lint.score.profiles import PROFILES, Profile

RULES = (  # in the order of the spec's table, which is the order they run in
    *notation.RULES,
    *instrument.RULES,
)

__all__ = ["PROFILES", "Profile", "RULES", "Rule", "VoiceLine", "lines", "lint_piece", "lint_score"]
