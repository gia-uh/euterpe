from importlib import import_module

import pytest

from euterpe.lint.score import PROFILES, lint_score
from euterpe.score import Score, drums, melody


def _fixture(rule):
    return import_module(f"tests.fixtures.score.{rule.lower().replace('-', '_')}")


def _found(score, rule, profile=None):
    return [f for f in lint_score(score, profile).findings if f.rule == rule]


def _score(text):
    s = Score()
    s.part("alto").add(melody(text))
    return s


def test_f_motif_reports_a_sequences_motif_and_its_count():
    three, four = _found(_fixture("F-MOTIF").trigger(), "F-MOTIF")
    assert (three.severity, three.part, three.value) == ("metric", "alto", 3.0)
    assert "+2 +2 -3" in three.message
    assert four.value == 2.0 and "+2 +2 -3 +2" in four.message


def test_f_motif_on_a_scale_run_reports_only_steps():
    three, four = _found(_fixture("F-MOTIF").clean(), "F-MOTIF")
    assert "+2 +2 +2 " in three.message and three.value == 5.0
    assert "+2 +2 +2 +2 " in four.message and four.value == 4.0


def test_f_motif_counts_a_motif_moved_by_step_as_one_when_its_third_changes():
    # c e g is a major third then a minor one, d f a the other way round
    [three] = _found(_score("c4:q e4 g4 c4 | d4 f4 a4 d4"), "F-MOTIF")[:1]
    assert "+3 +3 -5" in three.message and three.value == 2.0


def test_f_motif_says_nothing_of_what_occurs_once():
    assert not _found(_score("c4:q d4 f4 c5 | d4"), "F-MOTIF")


def test_f_motif_is_per_line_and_names_a_later_voice():
    s = _score("c4:q d4 e4 c4 | d4 e4 f4 d4")
    s.part("alto").add(melody("c3:q e3 g3 c3 | e3 g3 b3 e3"), voice=1, at=1)
    found = _found(s, "F-MOTIF")
    assert [f.value for f in found] == [2.0, 2.0]
    assert "voice" not in found[0].message and "voice 1" in found[1].message


def test_f_motif_reads_ties_as_one_note_and_goes_past_a_rest():
    plain = _found(_score("c4:q d4 e4 c4 | d4 e4 f4 d4"), "F-MOTIF")
    tied = _found(_score("c4:q d4~ d4 e4 | c4 r d4 e4 | f4 d4"), "F-MOTIF")
    assert [f.message for f in tied] == [f.message for f in plain]


def test_f_motif_reports_nothing_on_drums_or_rests():
    s = Score()
    s.part("drums").add(drums({"kick": "xxxx"}, step="q"))
    s.part("alto").add(melody("R"))
    assert not _found(s, "F-MOTIF")


def test_f_repeat_is_high_on_a_variation_and_low_on_another_section():
    [high] = _found(_fixture("F-REPEAT").trigger(), "F-REPEAT")
    [low] = _found(_fixture("F-REPEAT").clean(), "F-REPEAT")
    assert (high.severity, high.part) == ("metric", None)
    assert high.value > 0.5 > low.value
    assert low.value == 0.0
    assert high.message == "sections A and B hold 64% of their n-grams in common"


def test_f_repeat_is_one_for_equal_sections_and_reads_each_pair():
    s = _score("c4:q d4 e4 c4 | g4 f4 e4 d4 | c4 d4 e4 c4 | g4 f4 e4 d4 | c5 g4 c4 g4 | e5 b4 f5 a4")
    s.section("A", 1, 2)
    s.section("A again", 3, 4)
    s.section("C", 5, 6)
    assert [f.value for f in _found(s, "F-REPEAT")] == [1.0, 0.0, 0.0]


def test_f_repeat_needs_two_labelled_sections_with_n_grams():
    assert not _found(_fixture("F-MOTIF").trigger(), "F-REPEAT")
    s = _score("c4:w | c4:w")
    s.section("A", 1, 1)
    s.section("B", 2, 2)
    assert not _found(s, "F-REPEAT")


def test_f_repeat_finds_a_tune_passed_to_another_part():
    s = Score()
    s.part("alto").add(melody("c4:q d4 e4 c4 | g4 f4 e4 d4"))
    s.part("tenor").add(melody("c3:q d3 e3 c3 | g3 f3 e3 d3"), at=3)
    s.section("A", 1, 2)
    s.section("B", 3, 4)
    assert [f.value for f in _found(s, "F-REPEAT")] == [1.0]


@pytest.mark.parametrize("profile", [None, "chorale", "pop", "techno"])
def test_form_is_a_metric_under_each_profile(profile):
    assert {f.severity for f in _found(_fixture("F-MOTIF").trigger(), "F-MOTIF", profile)} == {"metric"}
    assert {f.severity for f in _found(_fixture("F-REPEAT").trigger(), "F-REPEAT", profile)} == {"metric"}


def test_each_profile_holds_the_f_row():
    for profile in PROFILES.values():
        assert [profile.severities[r] for r in ("F-MOTIF", "F-REPEAT")] == ["metric", "metric"]
