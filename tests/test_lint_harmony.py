from fractions import Fraction
from importlib import import_module

import pytest

from euterpe.lint.score import PROFILES, Profile, lint_score
from euterpe.score import Score, drums, melody
from euterpe.theory import Key

LOCATED = [
    ("H-CADENCE", None, "metric", None, 1, 3.0),
    ("H-CADENCE", "chorale", "warn", None, 1, 3.0),
    ("H-LEADING", None, "metric", "soprano", 1, 3.0),
    ("H-LEADING", "chorale", "warn", "soprano", 1, 3.0),
    ("H-SEVENTH", None, "metric", "alto", 1, 3.0),
    ("H-SEVENTH", "chorale", "warn", "alto", 1, 3.0),
]


def _fixture(rule):
    return import_module(f"tests.fixtures.score.{rule.lower().replace('-', '_')}")


def _found(score, rule, profile=None):
    return [f for f in lint_score(score, profile).findings if f.rule == rule]


def _values(score, rule, profile=None):
    return [f.value for f in _found(score, rule, profile)]


def _score(text, **kwargs):
    s = Score(**kwargs)
    s.part("choir").add(melody(text))
    return s


@pytest.mark.parametrize("rule, profile, severity, part, bar, beat", LOCATED)
def test_trigger_finds_the_rule_at_its_place_and_clean_does_not(rule, profile, severity, part, bar, beat):
    fixture = _fixture(rule)
    [f] = _found(fixture.trigger(), rule, profile)
    assert (f.severity, f.part, f.bar, f.beat) == (severity, part, bar, beat)
    assert not _found(fixture.clean(), rule, profile)


def test_h_key_is_the_share_of_note_time_outside_the_key():
    fixture = _fixture("H-KEY")
    [f] = _found(fixture.trigger(), "H-KEY")
    assert (f.severity, f.part, f.value) == ("metric", "alto", 0.25)
    assert "25%" in f.message
    assert _values(fixture.clean(), "H-KEY") == [0.0]


def test_h_key_weighs_by_time_and_counts_each_pitch_of_a_stack():
    assert _values(_score("c#4:h d4:q e4:q"), "H-KEY") == [0.5]
    assert _values(_score("<c4 c#4>:w"), "H-KEY") == [0.5]


def test_h_key_follows_a_change():
    s = _score("c#4:w | c#4:w")
    s.change(2, key=Key("D major"))
    assert _values(s, "H-KEY") == [0.5]


def test_h_key_takes_the_raised_sixth_and_seventh_of_minor_as_inside():
    assert _values(_score("f#4:q g#4 a4 b4", key=Key("A minor")), "H-KEY") == [0.0]
    assert _values(_score("g#4:q g4 a4 c#5", key=Key("A minor")), "H-KEY") == [0.25]


def test_h_key_is_per_part_and_a_part_with_no_notes_reports_nothing():
    s = _score("c4:w")
    s.part("other").add(melody("c#4:w"))
    s.part("drums").add(drums({"kick": "xxxx"}, step="q"))
    s.part("rests").add(melody("R"))
    assert [(f.part, f.value) for f in _found(s, "H-KEY")] == [("choir", 0.0), ("other", 1.0)]


def test_h_roman_reads_i_iv_v_i():
    [f] = _found(_fixture("H-ROMAN").trigger(), "H-ROMAN")
    assert f.severity == "metric" and f.value == 4.0
    assert "I–IV–V–I" in f.message


def test_h_roman_on_a_single_line_reports_nothing():
    assert not _found(_fixture("H-ROMAN").clean(), "H-ROMAN")


def test_h_roman_separates_bars_and_marks_what_has_no_numeral():
    [f] = _found(_score("<c4 e4 g4>:h c4:q r | <c4 e4 g4>:q r:h <c4 f4 g4>"), "H-ROMAN")
    assert f.message == "I–I–·–· | I–·–·–Csus4"
    assert f.value == 3.0


def test_h_roman_reads_each_bar_in_its_key():
    s = _score("<c4 e4 g4>:w | <c4 e4 g4>:w")
    s.change(2, key=Key("G major"))
    [f] = _found(s, "H-ROMAN")
    assert f.message == "I–I–I–I | IV–IV–IV–IV"


def test_h_cadence_says_what_it_ends_on():
    [f] = _found(_fixture("H-CADENCE").trigger(), "H-CADENCE")
    assert f.message == "the piece ends on ii, which makes no cadence"


def test_h_cadence_holds_a_chord_as_one():
    assert not _found(_score("<g3 b3 d4>:w | <c4 e4 g4>:w"), "H-CADENCE")


def test_h_cadence_holds_a_chord_through_its_inversions():
    assert not _found(_score("<g3 b3 d4>:h <e4 g4 c5>:h | <c4 e4 g4>:w"), "H-CADENCE")


def test_h_cadence_leaves_out_what_has_no_chord_after_it():
    assert not _found(_score("<g3 b3 d4>:h <c4 e4 g4>:h | c5:q r:q r:h"), "H-CADENCE")


def test_h_cadence_on_a_single_line_reports_nothing():
    assert not _found(_score("c4:q d4 e4 f4"), "H-CADENCE", "chorale")


def test_h_cadence_reads_a_section_ending_on_its_own_chords():
    s = _score("<c4 e4 g4>:h <d4 f4 a4>:h | <g3 b3 d4>:h <c4 e4 g4>:h")
    s.section("A", 1, 1)
    s.section("B", 2, 2)
    [f] = _found(s, "H-CADENCE")
    assert (f.bar, f.beat) == (1, 3.0)
    assert f.message == "section A ends on ii, which makes no cadence"


def test_h_cadence_passes_a_section_ending_on_a_half_cadence():
    s = _score("<c4 e4 g4>:h <g3 b3 d4>:h | <g3 b3 d4 g4>:h <c4 e4 g4 c5>:h")
    s.section("A", 1, 1)
    assert not _found(s, "H-CADENCE", "chorale")


def test_h_cadence_reports_the_end_of_the_piece_once_when_a_section_ends_it():
    s = _fixture("H-CADENCE").trigger()
    s.section("A", 1, 1)
    [f] = _found(s, "H-CADENCE")
    assert f.message.startswith("the piece ends")


def test_h_cadence_reads_the_key_in_force_at_the_end():
    s = _score("<c4 e4 g4>:w | <a3 c#4 e4>:h <d4 f#4 a4>:h")
    s.change(2, key=Key("D major"))
    assert not _found(s, "H-CADENCE", "pop")
    assert _found(_score("<c4 e4 g4>:w | <a3 c#4 e4>:h <d4 f#4 a4>:h"), "H-CADENCE", "pop")


@pytest.mark.parametrize("text", [
    "<g3 b3 d4 g4>:h <c3 g3 e4 c5>:h",  # a PAC
    "<f3 a3 c4 f4>:h <c3 g3 c4 e4>:h",  # plagal, whichever tone is on top
])
def test_h_cadence_under_chorale_takes_a_pac_or_plagal_at_the_end(text):
    assert not _found(_score(text), "H-CADENCE", "chorale")


@pytest.mark.parametrize("text, kind", [
    ("<g3 b3 d4 g4>:h <c3 g3 c4 e4>:h", "IAC"),  # V to I with the third on top
    ("<c3 g3 c4 e4>:h <g3 b3 d4 g4>:h", "HC"),
    ("<g3 b3 d4 g4>:h <a3 c4 e4 a4>:h", "deceptive"),
])
def test_h_cadence_under_chorale_wants_more_than_any_cadence(text, kind):
    assert not _found(_score(text), "H-CADENCE")
    [f] = _found(_score(text), "H-CADENCE", "chorale")
    assert f.severity == "warn"
    assert f.message == f"the piece ends on {kind}, not PAC or plagal, a warning under the chorale profile"


def test_h_cadence_under_chorale_lets_a_section_end_on_any_cadence():
    s = _score("<g3 b3 d4 g4>:h <c3 g3 c4 e4>:h | <g3 b3 d4 g4>:h <c3 g3 e4 c5>:h")
    s.section("A", 1, 1)
    assert not _found(s, "H-CADENCE", "chorale")


def test_a_custom_profile_chooses_the_final_cadences():
    s = _score("<g3 b3 d4 g4>:h <c3 g3 c4 e4>:h")
    profile = Profile("my", {"H-CADENCE": "warn"}, {"final_cadences": ("IAC",)})
    assert not _found(s, "H-CADENCE", profile)
    assert _found(_fixture("H-CADENCE").clean(), "H-CADENCE", profile)[0].message.startswith("the piece ends on PAC")


def test_h_leading_names_the_move_and_gives_its_semitones():
    [f] = _found(_fixture("H-LEADING").trigger(), "H-LEADING")
    assert "B4" in f.message and "G4" in f.message and "V" in f.message
    assert f.value == -4.0


def test_h_leading_reads_only_the_top_voice():
    s = Score()
    s.part("soprano").add(melody("d5:h c5:h"))
    s.part("lower").add(melody("<g3 b3>:h <g3 c4>:h"))
    s.part("alto").add(melody("b4:h g4:h"))
    assert not _found(s, "H-LEADING")


def test_h_leading_reads_vii_as_well():
    assert _found(_score("<d4 f4 b4>:h <c4 e4 g4>:h"), "H-LEADING")
    assert not _found(_score("<d4 f4 b4>:h <c4 e4 c5>:h"), "H-LEADING")


def test_h_leading_reads_the_raised_seventh_of_minor():
    assert not _found(_score("<e3 b3 g#4>:h <a3 c4 a4>:h", key=Key("A minor")), "H-LEADING")
    [f] = _found(_score("<e3 b3 g#4>:h <a3 c4 e4>:h", key=Key("A minor")), "H-LEADING")
    assert "G#4" in f.message


@pytest.mark.parametrize("text", [
    "<g3 b3 d4 b4>:h <g3 b3 d4 g4>:h",  # moving inside the chord it is on
    "<g3 d4 b4>:h <b3 d4 g4>:h",  # and so is this, into an inversion of it
    "<g3 d4 b4>:h <g3 e4 b4>:q <g3 e4 c5>:q",  # held into a chord change, then rising
    "<g3 d4 g4>:h <c4 e4 g4>:h",  # no leading tone on top
    "<e3 g3 b4>:h <f3 a3 c5>:h",  # B in iii is no leading tone
    "<g3 d4 b4>:w",  # nothing after it
])
def test_h_leading_passes(text):
    assert not _found(_score(text), "H-LEADING")


def test_h_leading_skips_a_beat_with_no_numeral():
    assert not _found(_score("b4:h g4:h"), "H-LEADING")


def test_h_seventh_names_the_move():
    [f] = _found(_fixture("H-SEVENTH").trigger(), "H-SEVENTH")
    assert "F4" in f.message and "G4" in f.message and "V7" in f.message
    assert f.value == 2.0


def test_h_seventh_reads_every_line():
    [f] = _found(_score("<g3 b3 d4 f4 g4>:h <g3 c4 e4 g4 c5>:h"), "H-SEVENTH")
    assert "F4" in f.message
    assert not _found(_score("<g3 b3 d4 f4 g4>:h <g3 c4 c4 e4 c5>:h"), "H-SEVENTH")


@pytest.mark.parametrize("text", [
    "<g3 b3 d4 f4>:h <c3 g3 c4 c4>:h",  # falling a fourth is no step
    "<g3 b3 d4 f4>:h <c3 g3 c4 a4>:h",  # rising
])
def test_h_seventh_finds_any_move_but_a_falling_step(text):
    assert len(_found(_score(text), "H-SEVENTH")) == 1


@pytest.mark.parametrize("text", [
    "<g3 b3 d4 f4>:h <g3 b3 f4 d4>:h",  # moving inside the chord it is on
    "<g3 b3 d4 f4>:h <c3 g3 c4 f4>:q <c3 g3 c4 e4>:q",  # held over, then the note is no seventh here
    "<c4 e4 g4>:h <a3 c4 f4>:h",  # no seventh
    "<g3 b3 d4 f4>:w",  # nothing after it
])
def test_h_seventh_passes(text):
    assert not _found(_score(text), "H-SEVENTH")


def test_an_overfull_last_bar_does_not_crash_the_chord_rules():
    s = _score("<g3 d4 b4>:w c5:q")
    assert not _found(s, "H-LEADING")
    assert not _found(s, "H-SEVENTH")


def test_a_pickup_places_a_finding_in_its_own_bar():
    s = Score(pickup=Fraction(1, 4))
    s.part("choir").add(melody("<g3 d4 b4>:q | <c4 e4 g4>:w"))
    [f] = _found(s, "H-LEADING")
    assert (f.bar, f.beat) == (2, 1.0)


def test_an_empty_score_reports_no_harmony():
    for rule in ("H-KEY", "H-ROMAN", "H-CADENCE", "H-LEADING", "H-SEVENTH"):
        assert not _found(Score(), rule, "chorale")


@pytest.mark.parametrize("rule, profile, severity", [
    ("H-CADENCE", "chorale", "warn"),
    ("H-CADENCE", "pop", "metric"),
    ("H-KEY", "chorale", "metric"),
    ("H-KEY", "pop", "metric"),
    ("H-KEY", "techno", "metric"),
])
def test_one_rule_under_each_profile(rule, profile, severity):
    assert {f.severity for f in _found(_fixture(rule).trigger(), rule, profile)} == {severity}


@pytest.mark.parametrize("rule", ["H-ROMAN", "H-CADENCE", "H-LEADING", "H-SEVENTH"])
def test_techno_turns_off_all_but_h_key(rule):
    assert not _found(_fixture(rule).trigger(), rule, "techno")


def test_each_profile_holds_the_h_row():
    rules = ("H-KEY", "H-ROMAN", "H-CADENCE", "H-LEADING", "H-SEVENTH")
    assert [PROFILES["chorale"].severities[r] for r in rules] == ["metric", "metric", "warn", "warn", "warn"]
    assert [PROFILES["pop"].severities[r] for r in rules] == ["metric"] * 5
    assert [PROFILES["techno"].severities[r] for r in rules] == ["metric"] + [None] * 4
