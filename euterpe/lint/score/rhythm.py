"""T rules: what a score's onsets, phrases, drums and tempo measure. Only T-BACKBEAT, T-FOURFLOOR and T-TEMPO warn, and
only under a profile that asks for that style."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import accumulate
from math import ceil

from euterpe.lint.finding import Finding, Severity
from euterpe.lint.score.core import Rule, notes
from euterpe.lint.score.profiles import THRESHOLDS
from euterpe.score.model import Hit, Part, Placed, Score
from euterpe.theory import Meter


@dataclass(frozen=True)
class Sound:
    """A note as it sounds: its first written Note, the last one tied on from it, and their whole length."""

    first: Placed
    last: Placed
    length: Fraction

    @property
    def end(self) -> Fraction:
        return self.first.offset + self.length


def sounds(score: Score, part: str) -> dict[int, list[Sound]]:
    """Each voice of a part that holds notes, by voice, as its sounds in order. A tie joins a note to the next when that
    note starts where it ends and adds no pitch."""
    voices: dict[int, list[Sound]] = {}
    for placed in notes(score, part):
        line = voices.setdefault(placed.voice, [])
        before = line[-1] if line else None
        if (before and before.last.event.tie and before.end == placed.offset
                and set(placed.event.pitches) <= set(before.last.event.pitches)):
            line[-1] = Sound(before.first, placed, before.length + placed.event.duration)
        else:
            line.append(Sound(placed, placed, placed.event.duration))
    return dict(sorted(voices.items()))


def named(voice: int, message: str) -> str:
    """A message, saying which voice it reads when that is not the part's first."""
    return f"voice {voice}: {message}" if voice else message


def _onsets(score: Score, part: str) -> list[Placed]:
    """The places a part strikes a sound, in order: a stack or two voices together strike one place."""
    struck = {placed.offset: placed for placed in score.events(part) if isinstance(placed.event, Hit)}
    for line in sounds(score, part).values():
        for sound in line:
            struck.setdefault(sound.first.offset, sound.first)
    return [struck[offset] for offset in sorted(struck)]


def _beat_starts(meter: Meter) -> list[Fraction]:
    """Where each beat of the meter starts, from the downbeat."""
    return [Fraction(start, meter.denominator) for start in accumulate(meter.groups[:-1], initial=0)]


def _strong(meter: Meter, in_bar: Fraction) -> bool:
    """Whether a place is stronger than the meter's weakest beats: in 4/4 beats 1 and 3, and in 3/4, 2/4 or 6/8 the
    downbeat."""
    return meter.strength(in_bar) < max(1, max(meter.strength(start) for start in _beat_starts(meter)))


def _strong_share(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per part: the share of its onsets on strong beats."""
    findings = []
    for part in score.parts:
        struck = _onsets(score, part)
        if struck:
            share = sum(_strong(score.meter_at(p.bar), p.in_bar) for p in struck) / len(struck)
            findings.append(Finding("T-STRONG", "metric", f"{share:.0%} of onsets on strong beats", share, part=part))
    return findings


def _syncopated(score: Score, starts: list[Fraction], placed: Placed, stop: Fraction) -> int:
    """Longuet-Higgins and Lee's weight for one onset: how much stronger than it is the strongest place it leaves
    unstruck, held or silent, before the next onset at stop. Only places on the onset's own grid count, so a triplet
    is not measured against the eighth it does not fall on."""
    own = score.meter_at(placed.bar).strength(placed.in_bar)
    step = Fraction(1, placed.in_bar.denominator)
    strongest = own
    for bar in range(placed.bar, score.bars + 1):
        if starts[bar - 1] >= stop:
            break
        meter = score.meter_at(bar)
        downbeat = starts[bar - 1] - score._lead(bar)
        for count in range(ceil(meter.bar / step)):
            if placed.offset < downbeat + count * step < stop:
                strongest = min(strongest, meter.strength(count * step))
    return own - strongest


def _syncopation(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per part: the sum of its onsets' syncopation weights, 0 when every onset is at least as strong as what
    it leaves unstruck."""
    findings = []
    starts = score._starts(score.bars)
    for part in score.parts:
        struck = _onsets(score, part)
        if struck:
            end = max(placed.offset + placed.event.duration for placed in score.events(part))
            stops = [placed.offset for placed in struck[1:]] + [end]
            index = sum(_syncopated(score, starts, placed, stop) for placed, stop in zip(struck, stops))
            findings.append(Finding("T-SYNCOPATION", "metric", f"syncopation index {index}", float(index), part=part))
    return findings


def _density(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Two metrics per part: its onsets per bar, an empty bar counting 0, and the largest count, at its first bar."""
    findings = []
    for name, part in score.parts.items():
        counts = [0] * part.bars
        for placed in _onsets(score, name):
            counts[placed.bar - 1] += 1
        if any(counts):
            mean, largest = sum(counts) / len(counts), max(counts)
            findings.append(Finding("T-DENSITY", "metric", f"{mean:.2f} onsets per bar", mean, part=name))
            findings.append(Finding("T-DENSITY", "metric", f"at most {largest} onsets in a bar", float(largest), part=name,
                                    bar=counts.index(largest) + 1))
    return findings


def _phrases(part: Part, voice: int) -> list[tuple[int, int]]:
    """The first and last bar of each phrase of a voice. A phrase ends at a silence or at a note of at least half a bar,
    in the meter where the note starts, and in the bar where that note stops."""
    phrases = []
    first = None
    line = sounds(part.score, part.name).get(voice, [])
    for sound, following in zip(line, [*line[1:], None]):
        first = first or sound.first.bar
        long = sound.length >= part.score.meter_at(sound.first.bar).bar / 2
        if long or following is None or following.first.offset > sound.end:
            phrases.append((first, sound.last.bar))
            first = None
    return phrases


def phrase_ends(part: Part, voice: int = 0) -> list[int]:
    """The bars in which a voice's phrases end, each once."""
    return sorted({last for _, last in _phrases(part, voice)})


def _phrase(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per phrase of each voice: its length in bars, at the bar it starts in."""
    findings = []
    for name, part in score.parts.items():
        for voice in sounds(score, name):
            for first, last in _phrases(part, voice):
                length = last - first + 1
                message = named(voice, f"a phrase of {length} bar{'s' if length > 1 else ''}, ending in bar {last}")
                findings.append(Finding("T-PHRASE", "metric", message, float(length), part=name, bar=first))
    return findings


def _beats(score: Score, part: str, drum: str) -> list[tuple[int, int, bool]]:
    """Each beat inside the bars where a part strikes any drum, as (bar, beat, whether this drum is struck on it)."""
    hits = [placed for placed in score.events(part) if isinstance(placed.event, Hit)]
    on = {(placed.bar, placed.in_bar) for placed in hits if placed.event.drum == drum}
    return [(bar, number, (bar, start) in on) for bar in sorted({placed.bar for placed in hits})
            for number, start in enumerate(_beat_starts(score.meter_at(bar)), 1) if start >= score._lead(bar)]


def _backbeat(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per part with drums: the share of its bars with a snare on every even beat. When that share is below
    min_backbeat, a finding at the first beat missing it too."""
    findings = []
    limit = params.get("min_backbeat", THRESHOLDS["min_backbeat"])
    for part in score.parts:
        even = [beat for beat in _beats(score, part, "snare") if beat[1] % 2 == 0]
        missing = [beat for beat in even if not beat[2]]
        if even:
            share = 1 - len({bar for bar, _, _ in missing}) / len({bar for bar, _, _ in even})
            message = f"{share:.0%} of bars with a snare on the backbeat"
            findings.append(Finding("T-BACKBEAT", "metric", message, share, part=part))
            if share < limit and severity != "metric":
                bar, beat, _ = missing[0]
                findings.append(Finding("T-BACKBEAT", severity, f"{message}, below {limit:.0%}", share, part=part, bar=bar,
                                        beat=float(beat)))
    return findings


def _fourfloor(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per part with drums: the share of its beats with a kick. When that share is below min_floor, a finding
    at the first beat missing it too."""
    findings = []
    limit = params.get("min_floor", THRESHOLDS["min_floor"])
    for part in score.parts:
        beats = _beats(score, part, "kick")
        if beats:
            missing = [beat for beat in beats if not beat[2]]
            share = 1 - len(missing) / len(beats)
            message = f"{share:.0%} of beats with a kick"
            findings.append(Finding("T-FOURFLOOR", "metric", message, share, part=part))
            if share < limit and severity != "metric":
                bar, beat, _ = missing[0]
                findings.append(Finding("T-FOURFLOOR", severity, f"{message}, below {limit:.0%}", share, part=part, bar=bar,
                                        beat=float(beat)))
    return findings


def _tempo(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Two metrics for the score: its lowest and highest tempo, read at each bar's downbeat and where each ramp that
    finishes inside the piece arrives. When one is outside the tempo range, a finding at the first bar reaching it too."""
    bars = score.bars
    if not bars:
        return []
    tempos = [(bar, score.tempo_at(bar)) for bar in range(1, bars + 1)]
    tempos += [(ramp.bar + ramp.bars - 1, ramp.to) for ramp in score.ramps if ramp.bar + ramp.bars <= bars + 1]
    tempos.sort(key=lambda tempo: tempo[0])
    lowest, highest = min(tempo for _, tempo in tempos), max(tempo for _, tempo in tempos)
    findings = [Finding("T-TEMPO", "metric", f"lowest tempo {lowest:g} bpm", lowest),
                Finding("T-TEMPO", "metric", f"highest tempo {highest:g} bpm", highest)]
    low, high = params.get("tempo", THRESHOLDS["tempo"])
    if severity != "metric":
        for bar, tempo in tempos:
            if not low <= tempo <= high:
                message = f"{tempo:g} bpm is outside {low:g} to {high:g} bpm"
                findings.append(Finding("T-TEMPO", severity, message, tempo, bar=bar))
                break
    return findings


RULES = (
    Rule("T-STRONG", "T", "each part's onsets against the meter's strong beats", "metric", _strong_share),
    Rule("T-SYNCOPATION", "T", "each part's onsets against the places they leave unstruck", "metric", _syncopation),
    Rule("T-DENSITY", "T", "each part's onsets per bar", "metric", _density),
    Rule("T-PHRASE", "T", "each voice's rests and long notes", "metric", _phrase),
    Rule("T-BACKBEAT", "T", "the snare hits on the even beats", "metric", _backbeat),
    Rule("T-FOURFLOOR", "T", "the kick hits on the beats", "metric", _fourfloor),
    Rule("T-TEMPO", "T", "the tempo at each bar and at the end of each ramp", "metric", _tempo),
)
