"""The frame of the score rules: a Rule, where a finding sits on a score, the lines of a score, and the runs."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import combinations
from typing import Any

from euterpe.lint.audio import lint_audio
from euterpe.lint.finding import Finding, Report, Severity
from euterpe.lint.score.profiles import PROFILES, Profile
from euterpe.score.model import Note, Placed, Score
from euterpe.theory import Meter

_STYLE = {"error": "an error", "warn": "a warning"}


@dataclass(frozen=True)
class Rule:
    """One rule: its id, its group's letter, what it reads, its severity with no profile (None is off), and a function
    from a score, the profile's params and the severity in force to findings."""

    id: str
    group: str
    reads: str
    severity: Severity | None
    check: Callable[[Score, dict[str, Any], Severity], list[Finding]]


def lint_score(score: Score, profile: Profile | str | None = None) -> Report:
    """Every rule on the score, in the spec's order, with the severity and params the profile gives it. A finding the
    profile made a warning or an error says so in its message."""
    from euterpe.lint.score import RULES

    profile = _profile(profile)
    findings = []
    for rule in RULES:
        severity = profile.severities.get(rule.id, rule.severity)
        if severity is not None:
            for finding in rule.check(score, profile.params, severity):
                styled = finding.severity == severity != rule.severity and severity in _STYLE
                findings.append(replace(finding, message=f"{finding.message}, {_STYLE[severity]} under the "
                                                         f"{profile.name} profile") if styled else finding)
    return Report(findings)


def lint_piece(score: Score, profile: Profile | str | None = None, seed: int = 0, audio: bool = True) -> Report:
    """lint_score, then lint_audio of the score played from seed, unless audio is false or a score with no parts, or
    with a part with no instrument, cannot play."""
    profile = _profile(profile)
    report = lint_score(score, profile)
    if audio and score.parts and all(part.instrument is not None for part in score.parts.values()):
        for finding in lint_audio(score.play(seed).take().samples).findings:
            severity = profile.severities.get(finding.rule, finding.severity)
            if severity is not None:
                report.findings.append(replace(finding, severity=severity))
    return report


def _profile(profile: Profile | str | None) -> Profile:
    """A profile by name, or the one that changes nothing."""
    if profile is None:
        return Profile("")
    if isinstance(profile, Profile):
        return profile
    if profile not in PROFILES:
        raise ValueError(f"lint: no profile {profile!r}; the profiles are {', '.join(PROFILES)}")
    return PROFILES[profile]


def beat_at(meter: Meter, in_bar: Fraction) -> float:
    """A place from the downbeat as a beat counted from 1 in the meter's groups. A place past the end of an overfull
    bar goes on counting in its last group's size."""
    position = Fraction(0)
    for number, size in enumerate(meter.groups, 1):
        length = Fraction(size, meter.denominator)
        if in_bar < position + length or number == meter.beats:
            return float(number + (in_bar - position) / length)
        position += length


def found(rule: str, severity: Severity, message: str, score: Score, placed: Placed, value: float | None = None,
          in_bar: Fraction | None = None) -> Finding:
    """A finding at an event's part and bar, on its beat or the one at in_bar."""
    beat = beat_at(score.meter_at(placed.bar), placed.in_bar if in_bar is None else in_bar)
    return Finding(rule, severity, message, value, part=placed.part, bar=placed.bar, beat=beat)


def notes(score: Score, part: str | None = None) -> Iterator[Placed]:
    """The placed notes of the score, or of one part; a hit or a rest has no pitch."""
    return (placed for placed in score.events(part) if isinstance(placed.event, Note))


class VoiceLine(list):
    """One line of lines(score), a list of (offset, end, Pitch), which knows the part and voice it comes from."""

    def __init__(self, part: str, voice: int):
        super().__init__()
        self.part = part
        self.voice = voice


def lines(score: Score) -> list[VoiceLine]:
    """Each voice of each part as lines, a stack of n pitches counting as n, top to bottom by mean pitch. Each line is
    (offset, end, Pitch) in order, a tied note joined to the note it holds on. A stack smaller than its voice's largest
    leaves as a rest the lines it can reach least closely, so a line does not jump to fill the gap."""
    found_lines = []
    for name in score.parts:
        voices: dict[int, list[Placed]] = {}
        for placed in notes(score, name):
            voices.setdefault(placed.voice, []).append(placed)
        for voice, placed_notes in voices.items():
            found_lines += _voice_lines(name, voice, placed_notes)
    return sorted(found_lines, key=lambda line: sum(pitch.number for _, _, pitch in line) / len(line), reverse=True)


def _voice_lines(part: str, voice: int, placed_notes: list[Placed]) -> list[VoiceLine]:
    split = [VoiceLine(part, voice) for _ in range(max(len(placed.event.pitches) for placed in placed_notes))]
    tied = False
    for placed in placed_notes:
        stack = sorted(placed.event.pitches, reverse=True)
        end = placed.offset + placed.event.duration
        for slot, pitch in zip(_slots(split, stack), stack):
            line = split[slot]
            if tied and line and line[-1][1:] == (placed.offset, pitch):
                line[-1] = (line[-1][0], end, pitch)
            else:
                line.append((placed.offset, end, pitch))
        tied = placed.event.tie
    return split


def _slots(split: list[VoiceLine], stack: list) -> tuple[int, ...]:
    """The lines a stack goes on, in order, that move least from where they last were; a line not begun costs nothing.
    Among equals the higher lines come first."""
    return min(combinations(range(len(split)), len(stack)),
               key=lambda slots: sum(abs(split[slot][-1][2] - pitch) if split[slot] else 0
                                     for slot, pitch in zip(slots, stack)))
