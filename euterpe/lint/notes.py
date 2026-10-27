"""Rules that check a phrase's notes against its instrument, before any sound is rendered."""

from __future__ import annotations

from euterpe.instruments import Phrase
from euterpe.instruments.core import _name, outside
from euterpe.lint.finding import Finding, Report
from euterpe.sound.core import RATE

COMFORT_WARN = 0.25  # share of note time outside the comfortable range that earns a warning


def lint_notes(phrase: Phrase) -> Report:
    """R-PLAYABLE, R-COMFORT and R-POLYPHONY on the notes a phrase was written with."""
    instrument, notes = phrase.instrument, phrase.notes
    report = Report()
    playable = getattr(instrument, "playable", None)
    if playable is not None:
        lo, hi = playable
        for i, n in enumerate(notes, 1):
            side = outside(n.pitch, playable)
            if side:
                report.findings.append(Finding(
                    "R-PLAYABLE", "error",
                    f"note {i} at {n.time:.2f} s: {_name(n.pitch)} is {side} of {lo!r} to {hi!r}", at=n.time))
    comfortable = getattr(instrument, "comfortable", None)
    total = sum(n.duration for n in notes)
    if comfortable is not None and total > 0:
        lo, hi = comfortable
        share = sum(n.duration for n in notes if outside(n.pitch, comfortable)) / total
        span = f"{lo!r} to {hi!r}"
        report.findings.append(Finding("R-COMFORT", "metric", f"{share:.0%} of note time outside {span}", value=share))
        if share > COMFORT_WARN:
            report.findings.append(Finding(
                "R-COMFORT", "warn", f"{share:.0%} of note time is outside the comfortable range {span}",
                value=share))
    _polyphony(report, notes, instrument.polyphony)
    return report


def _polyphony(report: Report, notes, polyphony: int) -> None:
    """The largest number of notes written to sound at once, when it is above polyphony. On a
    monophonic instrument overlapping notes are a slur, so only notes that start together count."""
    if polyphony == 1:
        edges = [(n.time, 1) for n in notes] + [(n.time, -1) for n in notes]
        edges.sort(key=lambda e: (round(e[0] * RATE), -e[1]))  # every start at one time before its ends
    else:
        # in samples, an end (-1) before a start (+1) at one time: back to back is not over
        edges = sorted((round(t * RATE), step, t) for n in notes
                       for t, step in ((n.time, 1), (n.time + n.duration, -1)))
        edges = [(t, step) for _, step, t in edges]
    count, most, first = 0, 0, None
    for t, step in edges:
        count += step
        if count > polyphony and first is None:
            first = t
        most = max(most, count)
    if first is not None:
        report.findings.append(Finding(
            "R-POLYPHONY", "warn",
            f"{most} notes are written to sound at once at {first:.2f} s; the instrument plays {polyphony}",
            value=most, at=first))

