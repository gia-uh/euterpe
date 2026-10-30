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
_RHYTHM = dict.fromkeys(("T-STRONG", "T-SYNCOPATION", "T-DENSITY", "T-PHRASE", "T-BACKBEAT", "T-FOURFLOOR", "T-TEMPO"), "metric")
_MELODY = ("M-RANGE", "M-LEAP", "M-CLIMAX", "M-REPEAT", "M-AUGMENTED", "M-CONTOUR")

THRESHOLDS = {"min_backbeat": 0.5, "min_floor": 0.9, "tempo": (118, 150), "max_range": 19, "max_repeat": 4}  # a rule's own

PROFILES = {
    "chorale": Profile("chorale", {
        **_EVERY_STYLE,
        **_RHYTHM,
        **dict.fromkeys(_MELODY, "warn"),
        "M-CONTOUR": "metric",
    }, {"max_range": THRESHOLDS["max_range"], "max_repeat": THRESHOLDS["max_repeat"]}),
    "pop": Profile("pop", {
        **_EVERY_STYLE,
        **_RHYTHM,
        "T-BACKBEAT": "warn",
        **dict.fromkeys(_MELODY, "metric"),
    }, {"min_backbeat": THRESHOLDS["min_backbeat"]}),
    "techno": Profile("techno", {
        **_EVERY_STYLE,
        **_RHYTHM,
        "T-FOURFLOOR": "warn",
        "T-TEMPO": "warn",
        **dict.fromkeys(_MELODY, None),
        "M-RANGE": "metric",
    }, {"min_floor": THRESHOLDS["min_floor"], "tempo": THRESHOLDS["tempo"]}),
}
