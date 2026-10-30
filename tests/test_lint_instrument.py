from importlib import import_module

import pytest

from euterpe.instruments import ElectricGuitar, Guitar, Kit, Violin
from euterpe.instruments.core import Feedback, Instrument, PalmMute, Staccato
from euterpe.lint.score import lint_score
from euterpe.pitch import A4
from euterpe.score import Line, Note, Score, drums, melody
from tests.helpers import Theremin

CASES = [
    ("R-PLAYABLE", "error", "alto", 2, 3.0),
    ("R-COMFORT", "warn", "alto", 1, 3.0),
    ("R-POLYPHONY", "warn", "alto", 1, 3.0),
    ("R-ARTIC", "warn", "alto", 2, 2.0),
]


def _found(score, rule):
    return [f for f in lint_score(score).findings if f.rule == rule]


def _score(text, instrument=None):
    s = Score()
    s.part("alto", instrument or Theremin()).add(melody(text))
    return s


@pytest.mark.parametrize("rule, severity, part, bar, beat", CASES)
def test_trigger_finds_the_rule_and_clean_does_not(rule, severity, part, bar, beat):
    fixture = import_module(f"tests.fixtures.score.{rule.lower().replace('-', '_')}")
    [f] = [f for f in _found(fixture.trigger(), rule) if f.severity != "metric"]
    assert (f.severity, f.part, f.bar, f.beat) == (severity, part, bar, beat)
    assert not [f for f in _found(fixture.clean(), rule) if f.severity != "metric"]


def test_playable_names_the_pitch_and_each_pitch_of_a_stack():
    [low, high] = _found(_score("<a3 b7>:w"), "R-PLAYABLE")
    assert "below the bottom" in high.message or "below the bottom" in low.message
    assert "B7" in high.message + low.message and "A3" in high.message + low.message


def test_comfort_measures_the_share_of_written_time():
    s = _score("a4:h d6:q a4:q")
    assert lint_score(s).value("R-COMFORT") == 0.25
    assert [f.severity for f in _found(s, "R-COMFORT")] == ["metric"]
    [metric, warn] = _found(_score("a4:h d6:h"), "R-COMFORT")
    assert (metric.severity, metric.part, metric.bar, metric.beat, metric.value) == ("metric", "alto", None, None, 0.5)
    assert warn.value == 0.5


def test_comfort_on_a_part_of_rests_reports_nothing():
    assert not _found(_score("r:w"), "R-COMFORT")


def test_polyphony_counts_the_pitches_of_a_stack():
    [f] = _found(_score("c4:h <c4 e4 g4>:h"), "R-POLYPHONY")
    assert f.value == 3


def test_a_slur_on_one_voice_is_not_a_polyphony_warning():
    s = Score()
    s.part("alto", Theremin()).add(melody("c4:h d4:h")).add(melody("r:q e4:h f4:q"), voice=1, at=1)
    assert not _found(s, "R-POLYPHONY")


def test_back_to_back_notes_are_not_over():
    class Duo(Instrument):
        polyphony = 2

    assert not _found(_score("<c4 e4>:h <d4 f4>:h", Duo()), "R-POLYPHONY")


def test_overlapping_voices_count_on_a_polyphonic_instrument():
    class Duo(Instrument):
        polyphony = 2

    s = Score()
    s.part("alto", Duo()).add(melody("<c4 e4>:w")).add(melody("r:h g4:h"), voice=1, at=1)
    [f] = _found(s, "R-POLYPHONY")
    assert (f.value, f.bar, f.beat) == (3, 1, 3.0)


def test_two_parts_on_one_instrument_count_together():
    class Duo(Instrument):
        polyphony = 2

    keys = Duo()
    s = Score()
    s.part("right", keys).add(melody("<c5 e5>:w"))
    s.part("left", keys).add(melody("r:h c3:h"))
    [f] = _found(s, "R-POLYPHONY")
    assert (f.part, f.value, f.bar, f.beat) == ("left", 3, 1, 3.0)


def test_two_instruments_of_one_make_count_apart():
    class Duo(Instrument):
        polyphony = 2

    s = Score()
    s.part("right", Duo()).add(melody("<c5 e5>:w"))
    s.part("left", Duo()).add(melody("<c3 e3>:w"))
    assert not _found(s, "R-POLYPHONY")


def test_a_part_with_no_instrument_gets_no_r_finding():
    s = Score()
    s.part("alto").add(melody("b8:w"))
    s.part("alto").add(Line([[Note(A4, 1, articulations=(PalmMute(),))]]))
    assert not [f for f in lint_score(s).findings if f.rule.startswith("R-")]


def test_a_preset_that_declares_nothing_takes_any_articulation():
    assert Guitar.articulations is None and Instrument.articulations is None
    s = Score()
    s.part("alto", Guitar()).add(Line([[Note(A4, 1, articulations=(Feedback(),))]]))
    assert not _found(s, "R-ARTIC")


def test_violin_and_electric_guitar_declare_theirs():
    assert PalmMute in ElectricGuitar.articulations and Feedback in ElectricGuitar.articulations
    assert PalmMute not in Violin.articulations and Staccato in Violin.articulations


def test_a_slur_is_not_an_articulation_warning():
    assert not _found(_score("(a4:q b4 c5 d5)", Violin()), "R-ARTIC")
    assert not _found(_score("(a3:q b3 c4 d4)", ElectricGuitar()), "R-ARTIC")


def test_a_drum_part_lints():
    s = Score()
    s.part("drums", Kit()).add(drums({"kick": "x...x..."}, step="e"))
    assert not [f for f in lint_score(s).findings if f.rule.startswith("R-")]
