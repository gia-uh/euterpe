"""N rules: whether the score is written correctly, in force under every profile."""

from __future__ import annotations

from fractions import Fraction
from itertools import groupby

from euterpe.instruments.core import Accent, Tenuto
from euterpe.lint.finding import Finding, Severity
from euterpe.lint.score.core import Rule, found, notes
from euterpe.score.model import Note, Placed, Score


def _voices(score: Score) -> list[list[Placed]]:
    """Each voice of each part that holds anything, as its events bar by bar, so an overfull bar stays whole."""
    voices: dict[tuple[str, int], list[Placed]] = {}
    for placed in score.events():
        voices.setdefault((placed.part, placed.voice), []).append(placed)
    return [sorted(voice, key=lambda placed: placed.bar) for voice in voices.values()]


def _measure(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A bar's voice that does not add up to its meter. The first bar with a pickup holds the pickup, and the piece's
    last bar may hold what the pickup leaves. A voice with nothing in a bar is silent there."""
    findings = []
    for voice in _voices(score):
        for bar, bar_events in groupby(voice, key=lambda placed: placed.bar):
            placed = list(bar_events)
            held = sum(p.event.duration for p in placed)
            length = score._bar_length(bar)
            if held == length or (bar == score.bars and score.pickup and held == length - score.pickup):
                continue
            full = score.meter_at(bar).bar
            over = next((p.in_bar for p in placed if p.in_bar + p.event.duration > full), None)
            where = placed[-1].in_bar + placed[-1].event.duration if over is None else over
            findings.append(found("N-MEASURE", severity, f"voice {placed[0].voice} holds {held} where the bar holds {length}",
                                  score, placed[0], float(held), where))
    return findings


def _tuplet(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A run of events in one tuplet, in one bar, that is not a whole number of groups, a group being the tuplet's
    actual count of the run's finest undotted value, which is one over its largest denominator. So two triplets in a
    row fill, a duplet fills on its second, and two dotted eighths fill a triplet of sixteenths."""
    findings = []
    for voice in _voices(score):
        keyed = groupby(voice, key=lambda placed: (placed.bar, getattr(placed.event, "tuplet", None)))
        for (_, tuplet), run in keyed:
            if tuplet is not None:
                placed = list(run)
                written = [p.event.duration * tuplet.actual / tuplet.normal for p in placed]
                group = tuplet.actual * Fraction(1, max(w.denominator for w in written))
                if sum(written) % group:
                    findings.append(found(
                        "N-TUPLET", severity,
                        f"a {tuplet.actual}:{tuplet.normal} tuplet holds {sum(written)} of written time, "
                        f"not a whole number of groups of {group}", score, placed[0]))
    return findings


def _tie(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A tie with no note starting where it ends, in its voice, or whose next note shares no pitch with it. Performance
    joins a tie pitch by pitch and spelled alike, so a stack may tie only some of its pitches."""
    findings = []
    for voice in _voices(score):
        for placed, after in zip(voice, [*voice[1:], None]):
            event = placed.event
            if not isinstance(event, Note) or not event.tie:
                continue
            name = " ".join(map(repr, event.pitches))
            if after is None or after.offset != placed.offset + event.duration or not isinstance(after.event, Note):
                findings.append(found("N-TIE", severity, f"the tie from {name} has nothing after it", score, placed))
            elif not set(event.pitches) & set(after.event.pitches):
                joined = " ".join(map(repr, after.event.pitches))
                findings.append(found("N-TIE", severity, f"a tie joins {name} to {joined}, another pitch", score, placed))
    return findings


def _spelling(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A pitch the key names, among its own notes and the altered ones it keeps, written under another name. A note the
    key does not name may be spelled either way: A flat and G sharp are both at home in C major."""
    findings = []
    for placed in notes(score):
        key = score.key_at(placed.bar)
        named = {pitch.number % 12 for pitch in key._spellings()}
        for pitch in placed.event.pitches:
            spelled = key.spell(pitch.number)
            if pitch.number % 12 in named and spelled != pitch:
                findings.append(found("N-SPELLING", severity, f"the key in force spells {pitch!r} as {spelled!r}",
                                      score, placed))
    return findings


def _artic(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Two articulations on one note that an instrument reads, of which only one reaches it. Accent and Tenuto end in
    the performance, so they go with any other."""
    findings = []
    for placed in notes(score):
        read = [type(a).__name__ for a in placed.event.articulations if not isinstance(a, (Accent, Tenuto))]
        if len(read) > 1:
            findings.append(found("N-ARTIC", severity, f"{' and '.join(read)} on one note: an instrument reads only one",
                                  score, placed))
    return findings


RULES = (
    Rule("N-MEASURE", "N", "each voice's events against the meter and pickup", "error", _measure),
    Rule("N-TUPLET", "N", "each voice's tuplet groups", "error", _tuplet),
    Rule("N-TIE", "N", "each voice's ties and the note after each", "error", _tie),
    Rule("N-SPELLING", "N", "each pitch against Key.spell", "warn", _spelling),
    Rule("N-ARTIC", "N", "each note's articulations", "warn", _artic),
)
