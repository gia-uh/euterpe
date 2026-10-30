"""What a lint rule reports, and the report that collects it."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Literal

Severity = Literal["error", "warn", "metric"]


@dataclass
class Finding:
    """One result of one rule: an error, a warning or a measurement. at is in seconds. part, bar and beat place a
    finding on a score, and beat counts from 1, as a float."""

    rule: str
    severity: Severity
    message: str
    value: float | None = None
    at: float | None = None
    part: str | None = None
    bar: int | None = None
    beat: float | None = None

    @property
    def place(self) -> str:
        """Where the finding is, as "part alto, bar 3, beat 2: ", or nothing when it has no place."""
        named = (self.part is not None and f"part {self.part}", self.bar is not None and f"bar {self.bar}",
                 self.beat is not None and f"beat {self.beat:g}")
        return ", ".join(filter(None, named)) + ": " if any(named) else ""


@dataclass
class Report:
    """The findings of a lint run, in the order the rules ran."""

    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        """The findings with severity error."""
        return [f for f in self.findings if f.severity == "error"]

    def value(self, rule: str) -> float | None:
        """The value of the first finding of rule, or None when the rule found nothing."""
        return next((f.value for f in self.findings if f.rule == rule), None)

    def to_json(self) -> str:
        """The findings as JSON: {"findings": [{rule, severity, message, value, at, part, bar, beat}, ...]}."""
        return json.dumps({"findings": [asdict(f) for f in self.findings]}, indent=2)

    def to_text(self) -> str:
        """One line per finding: severity, rule, place if it has one, message."""
        return "\n".join(f"{f.severity:<6} {f.rule:<14} {f.place}{f.message}" for f in self.findings)
