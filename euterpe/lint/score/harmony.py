"""H rules: what the score's chords do in the key in force, as Score.harmony reads them. A beat with no numeral is
skipped. Each measures with no profile, and the chorale profile makes the cadence and the two resolutions warnings."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Iterator
from fractions import Fraction

from euterpe.lint.finding import Finding, Severity
from euterpe.lint.score.core import Rule, VoiceLine, beat_at, lines, notes
from euterpe.lint.score.rhythm import named
from euterpe.pitch import Interval, Pitch
from euterpe.score.model import Harmony, Score
from euterpe.theory import Chord, cadence
from euterpe.theory.chord import _key_notes, _name

_NO_CHORD = "·"


def _key(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per part with notes: the share of its note time outside the key in force, each pitch of a stack counting
    alone. The raised 6th and 7th of a minor key are inside, as they are for the numerals."""
    findings = []
    for name in score.parts:
        total = outside = 0
        for placed in notes(score, name):
            inside = _key_notes(score.key_at(placed.bar))
            for pitch in placed.event.pitches:
                total += placed.event.duration
                outside += placed.event.duration * (_name(pitch) not in inside)
        if total:
            share = float(outside / total)
            findings.append(Finding("H-KEY", "metric", f"{share:.0%} of the note time is outside the key", share, part=name))
    return findings


def _label(beat: Harmony) -> str:
    """A beat's numeral, or its chord's name when no numeral fits, or a dot when it has no chord."""
    if beat.roman is not None:
        return beat.roman.text
    return beat.chord.name if beat.chord is not None else _NO_CHORD


def _roman(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric for a score with any chord: each beat's numeral in the message, bar by bar, and how many have one."""
    harmony = score.harmony()
    if not any(beat.chord for beat in harmony):
        return []
    bars: dict[int, list[str]] = {}
    for beat in harmony:
        bars.setdefault(beat.bar, []).append(_label(beat))
    message = " | ".join("–".join(labels) for labels in bars.values())
    return [Finding("H-ROMAN", "metric", message, float(sum(beat.roman is not None for beat in harmony)))]


def _same(first: Chord | None, second: Chord | None) -> bool:
    """Whether two chords are one chord, whatever their inversions."""
    return first is not None and second is not None and (first.root, first.quality) == (second.root, second.quality)


def _soprano(score: Score, start: Fraction, end: Fraction) -> Pitch | None:
    """The pitch of the highest line sounding in a stretch of time, or None."""
    for line in lines(score):
        for offset, until, pitch in line:
            if offset < end and start < until:
                return pitch
    return None


def _cadence(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each section that ends before the piece does, and the piece, whose last chords make no cadence, at the last
    chord's arrival, with how many chords that stretch holds as the value. A chord held through its inversions is one,
    read as it last sounded. final_cadences, when a profile gives it, is what the piece itself must end on."""
    findings = []
    beats = list(zip(score._beats(), score.harmony()))
    ends = [(f"section {section.name}", section.first, section.last)
            for section in score.sections if section.last < score.bars]
    final = params.get("final_cadences")
    for what, first, last in [*ends, ("the piece", 1, score.bars)]:
        heard = []  # each chord as (the beat it arrives on, the beat it last sounds on, that beat's window)
        for window, beat in beats:
            if first <= beat.bar <= last and beat.chord:
                arrival = heard.pop()[0] if heard and _same(heard[-1][1].chord, beat.chord) else beat
                heard.append((arrival, beat, window))
        if heard:
            arrival, sounding, (_, _, start, end) = heard[-1]
            kind = cadence([beat.chord for _, beat, _ in heard], score.key_at(sounding.bar), _soprano(score, start, end))
            message = None
            if kind is None:
                message = f"{what} ends on {_label(sounding)}, which makes no cadence"
            elif what == "the piece" and final and kind not in final:
                message = f"{what} ends on {kind}, not {' or '.join(final)}"
            if message:
                findings.append(Finding("H-CADENCE", severity, message, float(len(heard)), bar=arrival.bar,
                                        beat=float(arrival.beat)))
    return findings


def _moves(score: Score, read: Iterable[VoiceLine]) -> Iterator[tuple[VoiceLine, Harmony, Pitch, Pitch, int, float]]:
    """Each move of each line out of a chord with a numeral, as (line, the beat it leaves, from, to, the bar and beat it
    lands on). A note is read at its last moment, so one held over a chord change leaves the later chord. A note that
    stays, or goes to a tone of the chord it is on, has not left it yet. This measures what the beats read as: a passing
    tone that fills its own beat makes that beat another chord, so the move into it counts as leaving."""
    harmony = score.harmony()
    ends = [end for _, _, _, end in score._beats()]

    def at(index: int) -> Harmony | None:  # None past the end of an overfull last bar
        return harmony[index] if index < len(harmony) else None

    for line in read:
        for (_, until, pitch), (after, _, landing) in zip(line, line[1:]):
            here, there = at(bisect_left(ends, until)), at(bisect_right(ends, after))
            if (here is not None and here.roman is not None and there is not None
                    and pitch.number != landing.number and not _same(here.chord, there.chord)):
                in_bar = after - score.bar_start(there.bar) + score._lead(there.bar)
                yield line, here, pitch, landing, there.bar, beat_at(score.meter_at(there.bar), in_bar)


def _leading(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each leading tone of a V or a vii° in the top voice that does not rise to the tonic, at the note it goes to, with
    its semitones as the value."""
    findings = []
    for line, beat, pitch, landing, bar, place in _moves(score, lines(score)[:1]):
        roman = beat.roman
        if (roman.function == "dominant" and not roman.secondary and _name(pitch) in roman.chord.tones
                and _name(pitch) == _name(roman.key.leading_tone)
                and not (Interval.between(pitch, landing).number == 2 and _name(landing) == _name(roman.key.degree(1)))):
            message = named(line.voice, f"{pitch!r} in {roman.text} goes to {landing!r}, not up to the tonic")
            findings.append(Finding("H-LEADING", severity, message, float(landing - pitch), part=line.part, bar=bar,
                                    beat=place))
    return findings


def _seventh(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each chord's seventh, in any line, that does not fall by step, at the note it goes to, with its semitones as the
    value."""
    findings = []
    for line, beat, pitch, landing, bar, place in _moves(score, lines(score)):
        tones = beat.roman.chord.tones
        if len(tones) == 4 and _name(pitch) == tones[3] and Interval.between(pitch, landing).number != -2:
            message = named(line.voice, f"{pitch!r}, the seventh of {beat.roman.text}, goes to {landing!r}, "
                                        "not down by step")
            findings.append(Finding("H-SEVENTH", severity, message, float(landing - pitch), part=line.part, bar=bar,
                                    beat=place))
    return findings


RULES = (
    Rule("H-KEY", "H", "each part's note time against the key in force", "metric", _key),
    Rule("H-ROMAN", "H", "the score's harmony on each beat", "metric", _roman),
    Rule("H-CADENCE", "H", "the last chords of each section and of the piece", "metric", _cadence),
    Rule("H-LEADING", "H", "the top line's leading tones in V and vii°", "metric", _leading),
    Rule("H-SEVENTH", "H", "each line's chord sevenths", "metric", _seventh),
)
