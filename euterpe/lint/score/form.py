"""F rules: the material a score repeats, as n-grams of signed interval numbers over each line. An interval number is
letter distance, so a motif moved by step inside a key stays one motif when a third changes from major to minor. Each
is a metric under every profile."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

from euterpe.lint.finding import Finding, Severity
from euterpe.lint.score.core import Rule
from euterpe.lint.score.melody import _lines, _top
from euterpe.lint.score.rhythm import Sound, named
from euterpe.pitch import Interval
from euterpe.score.model import Score

_SIZES = (3, 4)


def _numbers(line: list[Sound]) -> list[int]:
    return [Interval.between(_top(before), _top(after)).number for before, after in zip(line, line[1:])]


def _grams(line: list[Sound], size: int) -> list[tuple[int, ...]]:
    numbers = _numbers(line)
    return [tuple(numbers[index:index + size]) for index in range(len(numbers) - size + 1)]


def _motif(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per line and size: its most frequent n-gram, the earliest among equals, with its count as the value. An
    n-gram that occurs once is no motif and reports nothing."""
    findings = []
    for name, voice, line in _lines(score):
        for size in _SIZES:
            common = Counter(_grams(line, size)).most_common(1)
            if common and common[0][1] > 1:
                gram, count = common[0]
                shown = " ".join(f"{number:+d}" for number in gram)
                message = named(voice, f"the motif {shown} occurs {count} times")
                findings.append(Finding("F-MOTIF", "metric", message, float(count), part=name))
    return findings


def _repeat(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per pair of labelled sections with any n-gram: the share of all their n-grams that both hold, read over
    every line, so a tune passed to another part still counts."""
    held = {}
    for section in score.sections:
        held[section] = set()
        for _, _, line in _lines(score):
            inside = [sound for sound in line if section.first <= sound.first.bar <= section.last]
            for size in _SIZES:
                held[section].update(_grams(inside, size))
    findings = []
    for first, second in combinations(score.sections, 2):
        both, either = held[first] & held[second], held[first] | held[second]
        if either:
            share = len(both) / len(either)
            message = f"sections {first.name} and {second.name} hold {share:.0%} of their n-grams in common"
            findings.append(Finding("F-REPEAT", "metric", message, share))
    return findings


RULES = (
    Rule("F-MOTIF", "F", "each line's interval n-grams", "metric", _motif),
    Rule("F-REPEAT", "F", "the interval n-grams of each pair of sections", "metric", _repeat),
)
