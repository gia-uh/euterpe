"""Rules that check a phrase's notes against its instrument, before any sound is rendered."""

from __future__ import annotations

from euterpe.instruments import Phrase
from euterpe.lint.finding import Finding, Report
from euterpe.pitch import Pitch

COMFORT_WARN = 0.25  # share of note time outside the comfortable range that earns a warning


def lint_notes(phrase: Phrase) -> Report:
    """R-PLAYABLE, R-COMFORT and R-POLYPHONY on the notes a phrase was written with."""
    instrument, notes = phrase.instrument, phrase.notes
    report = Report()
    playable = getattr(instrument, "playable", None)
    if playable is not None:
        lo, hi = playable
        for i, n in enumerate(notes, 1):
            side = "below the bottom" if _freq(n.pitch) < lo.freq else "above the top" if _freq(n.pitch) > hi.freq else None
            if side:
                report.findings.append(Finding(
                    "R-PLAYABLE", "error",
                    f"note {i} at {n.time:.2f} s: {_name(n.pitch)} is {side} of {lo!r} to {hi!r}", at=n.time))
    comfortable = getattr(instrument, "comfortable", None)
    total = sum(n.duration for n in notes)
    if comfortable is not None and total > 0:
        lo, hi = comfortable
        share = sum(n.duration for n in notes if not lo.freq <= _freq(n.pitch) <= hi.freq) / total
        span = f"{lo!r} to {hi!r}"
        report.findings.append(Finding("R-COMFORT", "metric", f"{share:.0%} of note time outside {span}", value=share))
        if share > COMFORT_WARN:
            report.findings.append(Finding(
                "R-COMFORT", "warn", f"{share:.0%} of note time is outside the comfortable range {span}",
                value=share))
    _polyphony(report, notes, instrument.polyphony)
    return report


def _polyphony(report: Report, notes, polyphony: int) -> None:
    """The largest number of notes written to sound at once, when it is above polyphony."""
    # at equal times an end (-1) comes before a start (+1): a note that starts as another ends is not over it
    edges = sorted([(n.time, 1) for n in notes] + [(n.time + n.duration, -1) for n in notes])
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


def _freq(pitch: Pitch | float) -> float:
    return pitch.freq if isinstance(pitch, Pitch) else float(pitch)


def _name(pitch: Pitch | float) -> str:
    return repr(pitch) if isinstance(pitch, Pitch) else f"{float(pitch):g} Hz"
