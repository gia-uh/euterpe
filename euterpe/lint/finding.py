"""What a lint rule reports, and the report that collects it."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Literal


@dataclass
class Finding:
    """One result of one rule: an error, a warning or a measurement. at is in seconds."""

    rule: str
    severity: Literal["error", "warn", "metric"]
    message: str
    value: float | None = None
    at: float | None = None


@dataclass
class Report:
    """The findings of a lint run, in the order the rules ran."""

    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        """The findings with severity error."""
        return [f for f in self.findings if f.severity == "error"]

    def to_json(self) -> str:
        """The findings as JSON: {"findings": [{rule, severity, message, value, at}, ...]}."""
        return json.dumps({"findings": [asdict(f) for f in self.findings]}, indent=2)

    def to_text(self) -> str:
        """One line per finding: severity, rule, message."""
        return "\n".join(f"{f.severity:<6} {f.rule:<11} {f.message}" for f in self.findings)
