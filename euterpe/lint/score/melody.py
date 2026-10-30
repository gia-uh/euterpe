"""M rules: what each voice of a part does as a line, a stack contributing its top pitch and a tie joining its notes. A
rest does not break a line. Each measures with no profile, and the chorale profile makes them warnings."""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter
from collections.abc import Iterator

from euterpe.lint.finding import Finding, Severity
from euterpe.lint.score.core import Rule, found
from euterpe.lint.score.profiles import THRESHOLDS
from euterpe.lint.score.rhythm import Sound, named, phrase_ends, sounds
from euterpe.pitch import Interval, Pitch
from euterpe.score.model import Score

_STEP = 2  # the most semitones a step moves
_SIXTH = 8  # the fewest semitones a sixth moves
_OCTAVE = 12


def _top(sound: Sound) -> Pitch:
    return max(sound.first.event.pitches)


def _lines(score: Score) -> Iterator[tuple[str, int, list[Sound]]]:
    """Each voice that holds notes, as (part, voice, its sounds)."""
    for name in score.parts:
        for voice, line in sounds(score, name).items():
            yield name, voice, line


def _moves(line: list[Sound]) -> list[int]:
    """The semitones between each note and the next, negative going down."""
    return [_top(after) - _top(before) for before, after in zip(line, line[1:])]


def _range(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per line: its span in semitones. When that is above max_range, a finding at the note that goes over too."""
    findings = []
    limit = params.get("max_range", THRESHOLDS["max_range"])
    for name, voice, line in _lines(score):
        numbers = [_top(sound).number for sound in line]
        span = max(numbers) - min(numbers)
        findings.append(Finding("M-RANGE", "metric", named(voice, f"a span of {span} semitones"), float(span), part=name))
        if span > limit and severity != "metric":
            over = next(sound for count, sound in enumerate(line, 1)
                        if max(numbers[:count]) - min(numbers[:count]) > limit)
            findings.append(found("M-RANGE", severity, named(voice, f"a span of {span} semitones, above {limit}"), score,
                                  over.first, float(span)))
    return findings


def _leap(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each leap above an octave, and each of a sixth or more that the next note does not turn back from, at the note
    it lands on, with its semitones as the value. A line's last note has nothing to turn back with."""
    findings = []
    for name, voice, line in _lines(score):
        moves = _moves(line)
        for index, move in enumerate(moves):
            following = moves[index + 1] if index + 1 < len(moves) else None
            unturned = abs(move) >= _SIXTH and following is not None and following * move >= 0
            if abs(move) > _OCTAVE or unturned:
                landed = line[index + 1]
                way = "above an octave" if abs(move) > _OCTAVE else "with no motion back"
                message = named(voice, f"a leap of {abs(move)} semitones to {_top(landed)!r}, {way}")
                findings.append(found("M-LEAP", severity, message, score, landed.first, float(move)))
    return findings


def _climax(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per line: how often its highest note occurs. When it occurs more than once in a phrase, a finding at
    its second time in that phrase too."""
    findings = []
    for name, voice, line in _lines(score):
        highest = max(_top(sound).number for sound in line)
        peaks = [sound for sound in line if _top(sound).number == highest]
        count = float(len(peaks))
        often = "once" if len(peaks) == 1 else f"{len(peaks)} times"
        findings.append(Finding("M-CLIMAX", "metric", named(voice, f"the highest note occurs {often}"), count, part=name))
        if severity != "metric":
            ends = phrase_ends(score.parts[name], voice)
            seen = Counter()
            for sound in peaks:
                phrase = bisect_left(ends, sound.last.bar)
                seen[phrase] += 1
                if seen[phrase] == 2:
                    message = named(voice, f"{_top(sound)!r}, the highest note, again in one phrase")
                    findings.append(found("M-CLIMAX", severity, message, score, sound.first, count))
    return findings


def _repeat(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each run of more than max_repeat equal notes, at the note that goes over, with the run's length as the value."""
    findings = []
    limit = params.get("max_repeat", THRESHOLDS["max_repeat"])
    for name, voice, line in _lines(score):
        start = 0
        for index in range(1, len(line) + 1):
            if index == len(line) or _top(line[index]).number != _top(line[start]).number:
                length = index - start
                if length > limit:
                    message = named(voice, f"{length} equal notes, {_top(line[start])!r}, above {limit}")
                    findings.append(found("M-REPEAT", severity, message, score, line[start + limit].first, float(length)))
                start = index
    return findings


def _augmented(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each melodic augmented second or fourth as it is spelled, at the note it lands on, with its semitones as the value."""
    findings = []
    for name, voice, line in _lines(score):
        for before, after in zip(line, line[1:]):
            interval = Interval.between(_top(before), _top(after))
            if interval.quality[0] == "A" and abs(interval.number) in (2, 4):
                size = "second" if abs(interval.number) == 2 else "fourth"
                message = named(voice, f"{_top(before)!r} to {_top(after)!r} is an augmented {size}")
                findings.append(found("M-AUGMENTED", severity, message, score, after.first, float(abs(interval.semitones))))
    return findings


def _contour(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Three metrics per line of two notes or more: the shares of its moves that are steps, that are leaps and that go
    up. A repeated note is neither a step nor a leap."""
    findings = []
    for name, voice, line in _lines(score):
        moves = _moves(line)
        if moves:
            shares = {"steps": sum(0 < abs(move) <= _STEP for move in moves),
                      "leaps": sum(abs(move) > _STEP for move in moves),
                      "upward motion": sum(move > 0 for move in moves)}
            for what, count in shares.items():
                share = count / len(moves)
                findings.append(Finding("M-CONTOUR", "metric", named(voice, f"{share:.0%} {what}"), share, part=name))
    return findings


RULES = (
    Rule("M-RANGE", "M", "each line's lowest and highest note", "metric", _range),
    Rule("M-LEAP", "M", "each line's leaps and the note after them", "metric", _leap),
    Rule("M-CLIMAX", "M", "each line's highest note in its phrases", "metric", _climax),
    Rule("M-REPEAT", "M", "each line's runs of equal notes", "metric", _repeat),
    Rule("M-AUGMENTED", "M", "each line's intervals as spelled", "metric", _augmented),
    Rule("M-CONTOUR", "M", "each line's moves", "metric", _contour),
)
