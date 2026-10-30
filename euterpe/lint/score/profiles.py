"""Profiles: which rules of which severity make a style. Lint is not taste: a profile only says what a style asks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from euterpe.lint.finding import Severity


@dataclass(frozen=True)
class Profile:
    """A style's severities by rule id and its thresholds. None turns a rule off, and a rule it does not name keeps its
    own severity."""

    name: str
    severities: dict[str, Severity | None] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)


_NOTATION = {"N-MEASURE": "error", "N-TUPLET": "error", "N-TIE": "error", "N-SPELLING": "warn", "N-ARTIC": "warn"}
_INSTRUMENT = {"R-PLAYABLE": "error", "R-COMFORT": "warn", "R-POLYPHONY": "warn", "R-ARTIC": "warn"}
_AUDIO = {"A-PEAK": "metric", "A-TRUEPEAK": "warn", "A-CLIP": "error", "A-LUFS": "metric", "A-DC": "warn",
          "A-TAIL": "warn", "A-SILENCE": "warn", "A-BALANCE-LOW": "metric", "A-BALANCE-MID": "metric",
          "A-BALANCE-HIGH": "metric", "A-SEAM": "warn"}
_EVERY_STYLE = {**_NOTATION, **_INSTRUMENT, **_AUDIO}

PROFILES = {
    "chorale": Profile("chorale", {
        **_EVERY_STYLE,
    }),
    "pop": Profile("pop", {
        **_EVERY_STYLE,
    }),
    "techno": Profile("techno", {
        **_EVERY_STYLE,
    }),
}
