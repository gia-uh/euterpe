"""R rules: whether a part's instrument can play what it is given, in force under every profile. Written time here is
what lint_notes measures in seconds; lint_notes stays for phrases that have no score."""

from __future__ import annotations

from euterpe.instruments.core import outside
from euterpe.lint.finding import Finding, Severity
from euterpe.lint.notes import COMFORT_WARN
from euterpe.lint.score.core import Rule, found, notes
from euterpe.score.model import Placed, Score


def _played(score: Score) -> list:
    """Each part that has an instrument."""
    return [part for part in score.parts.values() if part.instrument is not None]


def _playable(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """Each pitch outside what its part's instrument can play."""
    findings = []
    for part in _played(score):
        playable = part.instrument.playable
        if playable is not None:
            lo, hi = playable
            for placed in notes(score, part.name):
                for pitch in placed.event.pitches:
                    side = outside(pitch, playable)
                    if side:
                        findings.append(found("R-PLAYABLE", severity, f"{pitch!r} is {side} of {lo!r} to {hi!r}", score, placed))
    return findings


def _comfort(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """A metric per part: the share of its note time outside the comfortable range, each pitch of a stack counting. When
    that share is above COMFORT_WARN, a finding at the first such note too."""
    findings = []
    for part in _played(score):
        comfortable = part.instrument.comfortable
        placed_notes = list(notes(score, part.name))
        if comfortable is None or not placed_notes:
            continue
        lo, hi = comfortable
        total = sum(p.event.duration * len(p.event.pitches) for p in placed_notes)
        outer = sum(p.event.duration * sum(1 for q in p.event.pitches if outside(q, comfortable)) for p in placed_notes)
        share = float(outer / total)
        span = f"{lo!r} to {hi!r}"
        findings.append(Finding("R-COMFORT", "metric", f"{share:.0%} of note time outside {span}", share, part=part.name))
        if share > COMFORT_WARN and severity != "metric":
            first = next(p for p in placed_notes if any(outside(q, comfortable) for q in p.event.pitches))
            findings.append(found("R-COMFORT", severity, f"{share:.0%} of note time is outside the comfortable range {span}",
                                  score, first, share))
    return findings


def _polyphony(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """The most notes written to sound at once on one instrument object, parts sharing it counted together, when that
    is above its polyphony, at the note that first goes over."""
    shared: dict[int, tuple] = {}
    for part in _played(score):
        shared.setdefault(id(part.instrument), (part.instrument, []))[1].extend(notes(score, part.name))
    findings = []
    for instrument, placed_notes in shared.values():
        count, most, first = 0, 0, None
        for _, step, placed in _edges(placed_notes, instrument.polyphony):
            count += step
            if count > instrument.polyphony and first is None:
                first = placed
            most = max(most, count)
        if first is not None:
            findings.append(found("R-POLYPHONY", severity, f"{most} notes are written to sound at once; the instrument "
                                                           f"plays {instrument.polyphony}", score, first, most))
    return findings


def _edges(placed_notes: list[Placed], polyphony: int) -> list[tuple]:
    """Each pitch's start (+1) and end (-1) in order. On a monophonic instrument overlapping notes are a slur, so only
    notes that start together count, and each ends where it starts. Otherwise back to back is not over: an end comes
    before a start at one time."""
    pitches = [placed for placed in placed_notes for _ in placed.event.pitches]
    if polyphony == 1:
        edges = [(p.offset, 1, p) for p in pitches] + [(p.offset, -1, p) for p in pitches]
        return sorted(edges, key=lambda edge: (edge[0], -edge[1]))
    edges = [(p.offset, 1, p) for p in pitches] + [(p.offset + p.event.duration, -1, p) for p in pitches]
    return sorted(edges, key=lambda edge: edge[:2])


def _artic(score: Score, params: dict, severity: Severity) -> list[Finding]:
    """An articulation outside those a preset declares, when it declares them."""
    findings = []
    for part in _played(score):
        declared = part.instrument.articulations
        if declared is not None:
            for placed in notes(score, part.name):
                for articulation in placed.event.articulations:
                    if not isinstance(articulation, tuple(declared)):
                        findings.append(found("R-ARTIC", severity, f"{type(part.instrument).__name__} does not list "
                                                                   f"{type(articulation).__name__}", score, placed))
    return findings


RULES = (
    Rule("R-PLAYABLE", "R", "each pitch against the instrument's playable range", "error", _playable),
    Rule("R-COMFORT", "R", "note time against the instrument's comfortable range", "warn", _comfort),
    Rule("R-POLYPHONY", "R", "the notes sounding on each instrument object", "warn", _polyphony),
    Rule("R-ARTIC", "R", "each note's articulations against the preset's", "warn", _artic),
)
