from importlib import import_module

import pytest

import euterpe.lint
from euterpe.lint import PROFILES, Profile, lint_piece, lint_score
from euterpe.lint.score import RULES
from euterpe.score import Score, melody
from tests.helpers import Theremin

COLUMNS = (None, "chorale", "pop", "techno")

TABLE = [  # section 08's table, a row per rule it names: no profile, chorale, pop, techno
    ("N-MEASURE", "error", "error", "error", "error"),
    ("N-SPELLING", "warn", "warn", "warn", "warn"),
    ("N-ARTIC", "warn", "warn", "warn", "warn"),
    ("R-PLAYABLE", "error", "error", "error", "error"),
    ("R-ARTIC", "warn", "warn", "warn", "warn"),
    ("T-STRONG", "metric", "metric", "metric", "metric"),
    ("T-BACKBEAT", "metric", "metric", "warn", "metric"),
    ("T-FOURFLOOR", "metric", "metric", "metric", "warn"),
    ("T-TEMPO", "metric", "metric", "metric", "warn"),
    ("M-LEAP", "metric", "warn", "metric", None),
    ("M-CONTOUR", "metric", "metric", "metric", None),
    ("M-RANGE", "metric", "warn", "metric", "metric"),
    ("H-KEY", "metric", "metric", "metric", "metric"),
    ("H-ROMAN", "metric", "metric", "metric", None),
    ("H-CADENCE", "metric", "warn", "metric", None),
    ("H-LEADING", "metric", "warn", "metric", None),
    ("H-SEVENTH", "metric", "warn", "metric", None),
    ("V-PARALLEL", None, "error", "metric", None),
    ("V-DIRECT", None, "warn", None, None),
    ("V-CROSSING", None, "warn", None, None),
    ("V-OVERLAP", None, "warn", None, None),
    ("V-SPACING", None, "warn", None, None),
    ("V-RANGE", None, "warn", None, None),
    ("V-DOUBLING", None, "warn", None, None),
    ("F-MOTIF", "metric", "metric", "metric", "metric"),
    ("F-REPEAT", "metric", "metric", "metric", "metric"),
]
CELLS = [(row[0], column, severity) for row in TABLE for column, severity in zip(COLUMNS, row[1:])]

AUDIO = [("A-PEAK", "metric"), ("A-LUFS", "metric"), ("A-BALANCE-LOW", "metric")]


def _short():
    s = Score()
    s.part("alto", Theremin()).add(melody("a4:h"))
    return s


def _fixture(rule):
    return import_module(f"tests.fixtures.score.{rule.lower().replace('-', '_')}")


@pytest.mark.parametrize("rule, profile, severity", CELLS)
def test_each_cell_of_the_table_is_what_the_rule_reports(rule, profile, severity):
    found = {f.severity for f in lint_score(_fixture(rule).trigger(), profile).findings if f.rule == rule}
    # a rule that warns under a profile still measures, so the cell is the strongest it reports
    assert next((level for level in ("error", "warn", "metric") if level in found), None) == severity


@pytest.mark.parametrize("profile", COLUMNS)
@pytest.mark.parametrize("rule, severity", AUDIO)
def test_audio_rules_stay_as_they_are(rule, severity, profile):
    assert {f.severity for f in lint_piece(_short(), profile).findings if f.rule == rule} == {severity}


def test_every_rule_on_a_score_is_counted():
    ids = {rule.id for rule in RULES}
    assert len(RULES) == len(ids) == 36
    assert len(ids - {"R-PLAYABLE", "R-COMFORT", "R-POLYPHONY"}) == 33


def test_rules_run_in_the_order_of_the_table():
    groups = list(dict.fromkeys(rule.group for rule in RULES))
    assert groups == ["N", "T", "R", "M", "H", "V", "F"]


@pytest.mark.parametrize("name", ["chorale", "pop", "techno"])
def test_each_profile_names_every_rule_on_a_score(name):
    assert {rule.id for rule in RULES} <= set(PROFILES[name].severities)


def test_euterpe_lint_exports_the_score_lint():
    for name in ("lint_score", "lint_piece", "Profile", "PROFILES"):
        assert name in euterpe.lint.__all__ and hasattr(euterpe.lint, name)
    assert Profile("my").name == "my"
