"""V rules: how the lines of a score move against each other, in the common-practice style of four-part writing. Each
is off with no profile. The chorale profile makes V-PARALLEL an error and the rest warnings, and pop keeps V-PARALLEL as
a metric. Two lines are compared only where both sound, so a line in a rest or a missing voice has nothing to break."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable, Iterable, Iterator
from fractions import Fraction
from itertools import combinations, pairwise

from euterpe.lint.finding import Finding, Severity
from euterpe.lint.score.core import Rule, VoiceLine, beat_at, lines
from euterpe.lint.score.rhythm import counted, named
from euterpe.pitch import Interval, Pitch
from euterpe.score.model import Score
from euterpe.theory.chord import _name

_RANGES = (("C4", "G5"), ("G3", "D5"), ("C3", "G4"), ("E2", "C4"))  # soprano, alto, tenor and bass
_OCTAVE = 12
_KINDS = {5: "fifth", 8: "octave", 1: "unison"}


def _sounding(line: VoiceLine, at: Fraction) -> Pitch | None:
    """The pitch of a line at a moment, or None in a rest."""
    index = bisect_right(line, at, key=lambda note: note[0]) - 1
    return line[index][2] if index >= 0 and at < line[index][1] else None


def _moments(read: tuple[VoiceLine, ...],
             also: Iterable[Fraction] = ()) -> list[tuple[Fraction, tuple[Pitch | None, ...]]]:
    """Each moment any of the lines starts or ends a note, and the moments also asked for, with the pitch each line
    sounds from then on."""
    times = sorted({*also, *(time for line in read for offset, end, _ in line for time in (offset, end))})
    return [(at, tuple(_sounding(line, at) for line in read)) for at in times]


def _moves(upper: VoiceLine, lower: VoiceLine) -> Iterator[tuple[Fraction, Pitch, Pitch, Pitch, Pitch]]:
    """Each change between two moments in a row where both lines sound, as (when, upper from, lower from, upper to,
    lower to)."""
    for (_, before), (at, after) in pairwise(_moments((upper, lower))):
        if None not in before and None not in after:
            yield at, *before, *after


def _runs(moments: list, holds: Callable[[tuple], bool]) -> Iterator[tuple[Fraction, tuple]]:
    """The moment each stretch begins in which holds is true, so one fault held for many notes is one finding."""
    held = False
    for at, pitches in moments:
        now = holds(pitches)
        if now and not held:
            yield at, pitches
        held = now


def _found(rule: str, severity: Severity, score: Score, starts: list[Fraction], line: VoiceLine, at: Fraction,
           message: str, value: float) -> Finding:
    """A finding on a line at a moment, with the bar and beat it falls on among the bars' starts."""
    bar = bisect_right(starts, at)
    in_bar = at - starts[bar - 1] + score._lead(bar)
    return Finding(rule, severity, named(line.voice, message), value, part=line.part, bar=bar,
                   beat=beat_at(score.meter_at(bar), in_bar))


def _other(line: VoiceLine, other: VoiceLine) -> str:
    """How a line's message names another line: by its part, or as another line of the same part."""
    return "another line" if other.part == line.part else f"the {other.part}"


def _perfect(upper: Pitch, lower: Pitch) -> str | None:
    """The name of the fifth, octave or unison two pitches make at any distance, by their spelling, or None."""
    interval = Interval.between(*sorted((lower, upper)))
    return _KINDS.get(abs(interval.simple.number)) if interval.quality == "P" else None


def _same_way(upper_from: Pitch, lower_from: Pitch, upper_to: Pitch, lower_to: Pitch) -> bool:
    """Whether both lines move and in the same direction."""
    return (upper_to.number - upper_from.number) * (lower_to.number - lower_from.number) > 0


def _class(kind: str | None) -> str | None:
    """Octaves and unisons are one class: a line moving to its neighbour's octave stays parallel."""
    return "octave" if kind == "unison" else kind


def _parallel(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each pair of lines moving the same way from one perfect fifth, octave or unison to another of its kind, on the
    lower line at the moment they arrive, with the semitones between them as the value."""
    starts = score._starts(score.bars)
    findings = []
    for upper, lower in combinations(lines(score), 2):
        for at, upper_from, lower_from, upper_to, lower_to in _moves(upper, lower):
            kind = _perfect(upper_to, lower_to)
            if (kind and _same_way(upper_from, lower_from, upper_to, lower_to)
                    and _class(_perfect(upper_from, lower_from)) == _class(kind)):
                message = (f"parallel {kind}s with {_other(lower, upper)} "
                           f"({lower_from!r}–{upper_from!r} to {lower_to!r}–{upper_to!r})")
                findings.append(_found("V-PARALLEL", severity, score, starts, lower, at, message,
                                       float(upper_to - lower_to)))
    return findings


def _direct(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """The outer lines reaching a fifth, octave or unison the same way, the top one by a leap, on the top line, with the
    semitones of the leap as the value. Arriving from the same perfect interval is V-PARALLEL's."""
    read = lines(score)
    if len(read) < 2:
        return []
    top, bottom = read[0], read[-1]
    starts = score._starts(score.bars)
    findings = []
    for at, top_from, bottom_from, top_to, bottom_to in _moves(top, bottom):
        kind = _perfect(top_to, bottom_to)
        if (kind and _same_way(top_from, bottom_from, top_to, bottom_to)
                and abs(Interval.between(top_from, top_to).number) > 2
                and _class(_perfect(top_from, bottom_from)) != _class(kind)):
            message = (f"direct {kind} with {_other(top, bottom)} ({bottom_from!r}–{top_from!r} to "
                       f"{bottom_to!r}–{top_to!r}), the top line leaping")
            findings.append(_found("V-DIRECT", severity, score, starts, top, at, message, float(top_to - top_from)))
    return findings


def _crossing(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each stretch in which a lower line sounds above a higher one, where it begins, on the lower line, with the
    semitones it is above by as the value."""
    starts = score._starts(score.bars)
    findings = []
    for upper, lower in combinations(lines(score), 2):
        moments = _moments((upper, lower))
        for at, (high, low) in _runs(moments, lambda pair: None not in pair and pair[1].number > pair[0].number):
            message = f"{low!r} is above {high!r} in {_other(lower, upper)}"
            findings.append(_found("V-CROSSING", severity, score, starts, lower, at, message, float(low - high)))
    return findings


def _overlap(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A line moving past where its neighbour was just before, when the neighbour has moved too: with the neighbour
    still there, that is V-CROSSING. On the line that moves past, with the semitones past as the value."""
    starts = score._starts(score.bars)
    findings = []
    read = lines(score)
    for upper, lower in pairwise(read):
        for at, upper_from, lower_from, upper_to, lower_to in _moves(upper, lower):
            if upper_to == upper_from or lower_to == lower_from:
                continue
            if lower_from.number <= upper_from.number < lower_to.number:
                message = f"moves to {lower_to!r}, above {upper_from!r}, where {_other(lower, upper)} just was"
                findings.append(_found("V-OVERLAP", severity, score, starts, lower, at, message,
                                       float(lower_to - upper_from)))
            if upper_to.number < lower_from.number <= upper_from.number:
                message = f"moves to {upper_to!r}, below {lower_from!r}, where {_other(upper, lower)} just was"
                findings.append(_found("V-OVERLAP", severity, score, starts, upper, at, message,
                                       float(upper_to - lower_from)))
    return findings


def _not_four(rule: str, read: list[VoiceLine]) -> list[Finding]:
    """The metric that says a rule of four parts did not run on this many lines."""
    return [Finding(rule, "metric", f"reads exactly four lines, and this score has {counted(len(read), 'line')}",
                    float(len(read)))]


def _spacing(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each stretch with more than an octave from the first line to the second or the second to the third, where it
    begins, on the lower line, with the semitones as the value. Other than four lines, one metric saying so."""
    read = lines(score)
    if len(read) != len(_RANGES):
        return _not_four("V-SPACING", read)
    starts = score._starts(score.bars)
    findings = []
    for upper, lower in pairwise(read[:3]):
        moments = _moments((upper, lower))
        for at, (high, low) in _runs(moments, lambda pair: None not in pair and pair[0] - pair[1] > _OCTAVE):
            message = f"{low!r} is {high - low} semitones below {high!r} in {_other(lower, upper)}, more than an octave"
            findings.append(_found("V-SPACING", severity, score, starts, lower, at, message, float(high - low)))
    return findings


def _range(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each note outside its voice's range, the lines read top to bottom as soprano, alto, tenor and bass, with the
    semitones outside as the value, negative below. Other than four lines, one metric saying so."""
    read = lines(score)
    if len(read) != len(_RANGES):
        return _not_four("V-RANGE", read)
    starts = score._starts(score.bars)
    findings = []
    for line, (lowest, highest) in zip(read, _RANGES):
        low, high = Pitch(lowest), Pitch(highest)
        for at, _, pitch in line:
            outside = pitch - high if pitch.number > high.number else pitch - low if pitch.number < low.number else 0
            if outside:
                message = f"{pitch!r} is outside the voice's range, {lowest} to {highest}"
                findings.append(_found("V-RANGE", severity, score, starts, line, at, message, float(outside)))
    return findings


def _doubling(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each stretch with the leading tone of the key in force in two or more lines, where it begins, on the second line
    down, with how many lines hold it as the value. A key change that moves the leading tone begins a new stretch, even
    under notes tied across it, so each bar start is read too."""
    read = tuple(lines(score))
    findings = []
    last = None
    starts = score._starts(score.bars)
    for at, pitches in _moments(read, starts):
        leading = _name(score.key_at(bisect_right(starts, at)).leading_tone)
        holding = [index for index, pitch in enumerate(pitches) if pitch is not None and _name(pitch) == leading]
        doubled = leading if len(holding) > 1 else None
        if doubled and doubled != last:
            message = f"the leading tone {leading} is in {len(holding)} lines"
            findings.append(_found("V-DOUBLING", severity, score, starts, read[holding[1]], at, message,
                                   float(len(holding))))
        last = doubled
    return findings


RULES = (
    Rule("V-PARALLEL", "V", "each pair of lines moving together", None, _parallel),
    Rule("V-DIRECT", "V", "the outer lines reaching a perfect interval", None, _direct),
    Rule("V-CROSSING", "V", "each pair of lines at one moment", None, _crossing),
    Rule("V-OVERLAP", "V", "each line and the last note of its neighbour", None, _overlap),
    Rule("V-SPACING", "V", "the gaps between the three upper lines", None, _spacing),
    Rule("V-RANGE", "V", "each of four lines against its voice's range", None, _range),
    Rule("V-DOUBLING", "V", "the leading tone across the lines", None, _doubling),
)
