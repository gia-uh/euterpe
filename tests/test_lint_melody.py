from importlib import import_module

import pytest

from euterpe.lint.score import PROFILES, Profile, lint_score
from euterpe.score import Score, drums, melody

LOCATED = [
    ("M-LEAP", None, "metric", 1, 2.0, 9.0),
    ("M-LEAP", "chorale", "warn", 1, 2.0, 9.0),
    ("M-REPEAT", None, "metric", 2, 1.0, 6.0),
    ("M-REPEAT", "chorale", "warn", 2, 1.0, 6.0),
    ("M-AUGMENTED", None, "metric", 1, 2.0, 6.0),
    ("M-AUGMENTED", "chorale", "warn", 1, 2.0, 6.0),
    ("M-RANGE", "chorale", "warn", 2, 1.0, 28.0),
    ("M-CLIMAX", "chorale", "warn", 1, 4.0, 3.0),
]

METRICS = [
    ("M-RANGE", [28.0], [16.0]),
    ("M-CLIMAX", [3.0], [1.0]),
    ("M-CONTOUR", [0.5, 0.5, 0.75], []),
]

# M-RANGE and M-CLIMAX also report a metric under chorale, which the place does not apply to
_ALSO_A_METRIC = {"M-RANGE", "M-CLIMAX"}


def _fixture(rule):
    return import_module(f"tests.fixtures.score.{rule.lower().replace('-', '_')}")


def _found(score, rule, profile=None):
    return [f for f in lint_score(score, profile).findings if f.rule == rule]


def _values(score, rule, profile=None):
    return [f.value for f in _found(score, rule, profile)]


def _warnings(score, rule, profile="chorale"):
    return [f for f in _found(score, rule, profile) if f.severity == "warn"]


def _score(text, **kwargs):
    s = Score(**kwargs)
    s.part("alto").add(melody(text))
    return s


@pytest.mark.parametrize("rule, trigger, clean", METRICS)
def test_a_metric_reports_its_known_values(rule, trigger, clean):
    fixture = _fixture(rule)
    assert _values(fixture.trigger(), rule) == pytest.approx(trigger)
    assert _values(fixture.clean(), rule) == pytest.approx(clean)
    assert {(f.severity, f.part) for f in _found(fixture.trigger(), rule)} == {("metric", "alto")}


@pytest.mark.parametrize("rule, profile, severity, bar, beat, value", LOCATED)
def test_trigger_finds_the_rule_at_its_place_and_clean_does_not(rule, profile, severity, bar, beat, value):
    fixture = _fixture(rule)
    [f] = [f for f in _found(fixture.trigger(), rule, profile) if f.severity == severity and f.bar is not None]
    assert (f.part, f.bar, f.beat, f.value) == ("alto", bar, beat, value)
    if rule in _ALSO_A_METRIC:
        assert not _warnings(fixture.clean(), rule, profile)
    else:
        assert not _found(fixture.clean(), rule, profile)


def test_a_warning_under_chorale_says_so():
    [f] = _warnings(_fixture("M-LEAP").trigger(), "M-LEAP")
    assert f.message.endswith(", a warning under the chorale profile")
    assert "profile" not in _found(_fixture("M-LEAP").trigger(), "M-LEAP")[0].message


def test_a_stack_contributes_its_top_pitch():
    assert _values(_score("<c4 g4>:q <d4 a4> <e4 b4> <f4 c5>"), "M-RANGE") == [5.0]
    assert _values(_score("<c4 g4>:q <d4 a4>"), "M-CONTOUR") == pytest.approx([1.0, 0.0, 1.0])


def test_each_voice_is_a_line():
    s = _score("c4:w | c5:w")
    s.part("alto").add(melody("e3:w | g3:w"), voice=1, at=1)
    ranges = _found(s, "M-RANGE")
    assert [f.value for f in ranges] == [12.0, 3.0]
    assert "voice 1" in ranges[1].message and "voice" not in ranges[0].message


def test_each_part_is_read_alone():
    s = _score("c4:w")
    s.part("tenor").add(melody("c3:w | e3:w"))
    assert [(f.part, f.value) for f in _found(s, "M-RANGE")] == [("alto", 0.0), ("tenor", 4.0)]


def test_a_part_of_drums_or_rests_has_no_line():
    s = Score()
    s.part("drums").add(drums({"kick": "xxxx"}, step="q"))
    s.part("alto").add(melody("R"))
    for rule in ("M-RANGE", "M-LEAP", "M-CLIMAX", "M-REPEAT", "M-AUGMENTED", "M-CONTOUR"):
        assert not _found(s, rule, "chorale")


def test_m_range_reads_spelling_as_sound():
    assert _values(_score("g#4:q ab4"), "M-RANGE") == [0.0]


def test_m_range_warns_only_above_its_threshold():
    assert not _warnings(_score("c4:w | g5:w"), "M-RANGE")
    [f] = _warnings(_score("c4:w | g#5:w"), "M-RANGE")
    assert f.value == 20.0


def test_m_range_warns_at_the_note_that_goes_over_from_either_side():
    [f] = _warnings(_score("c5:q c6 c5 c4"), "M-RANGE")
    assert (f.bar, f.beat) == (1, 4.0)


@pytest.mark.parametrize("text, beat, value", [
    ("c4:q a5 g5 f5", 2.0, 21.0),  # above an octave, even with a step back
    ("c5:q c4 b3 a3", 2.0, -12.0),  # an octave down, then down again
    ("c4:q ab4 ab4 g4", 2.0, 8.0),  # a minor sixth, then no motion
    ("c5:q e4 e3 f3", 2.0, -8.0),  # down a minor sixth, then down an octave
])
def test_m_leap_finds(text, beat, value):
    [f] = _found(_score(text), "M-LEAP")
    assert (f.beat, f.value) == (beat, value)


@pytest.mark.parametrize("text", [
    "c4:q g4 a4 b4",  # a fifth is no leap here
    "c4:q c5 b4 a4",  # an octave up and back
    "c5:q e4 g4 a4",  # a minor sixth down and back up
    "c4:q d4 e4 c5",  # the last note leaps and nothing follows it
    "c4:q a4~ a4 g4",  # the tied note holds the same place, then the line turns back
    "c4:q a4 r g4",  # a rest does not break the line
])
def test_m_leap_passes(text):
    assert not _found(_score(text), "M-LEAP")


def test_m_leap_past_a_rest_is_still_a_leap():
    [f] = _found(_score("c4:q r c6 d6"), "M-LEAP")
    assert (f.beat, f.value) == (3.0, 24.0)


def test_m_climax_counts_the_highest_pitch_of_each_line():
    assert _values(_score("c4:q g4 e4 g4 | c4 d4 e4 g4"), "M-CLIMAX") == [3.0]


def test_m_climax_is_once_for_a_tied_note():
    assert _values(_score("c4:q g4:h~ g4:q"), "M-CLIMAX") == [1.0]
    assert not _warnings(_score("c4:q g4:h~ g4:q"), "M-CLIMAX")


def test_m_climax_warns_per_phrase():
    [f] = _warnings(_score("c4:q g4 e4 d4 | c4 g4 e4 d4"), "M-CLIMAX")
    assert (f.bar, f.beat) == (2, 2.0)
    assert not _warnings(_score("c4:q g4 e4 r | c4 g4 e4 d4"), "M-CLIMAX")


def test_m_climax_phrases_are_those_of_the_voice_it_reads():
    s = _score("c4:q d e f | g a b c")
    s.part("alto").add(melody("g3:q c3 r:h | g3:q c3 d3 e3"), voice=1, at=1)
    assert not _warnings(s, "M-CLIMAX")


def test_m_repeat_is_one_finding_per_run_at_the_note_that_goes_over():
    [first, second] = _found(_score("c4:e c c c c d d d | e e e e e f f f"), "M-REPEAT")
    assert (first.bar, first.beat, first.value) == (1, 3.0, 5.0)
    assert (second.bar, second.beat, second.value) == (2, 3.0, 5.0)


def test_m_repeat_ties_are_one_note_and_rests_do_not_break_a_run():
    assert not _found(_score("c4:q~ c c~ c | c d e f"), "M-REPEAT")
    assert _values(_score("c4:q r c r | c r c r | c d e f"), "M-REPEAT") == [5.0]


def test_m_repeat_counts_equal_sound_across_spelling():
    assert _values(_score("g#4:q ab4 g#4 ab4 | g#4 c5 d5 e5"), "M-REPEAT") == [5.0]


def test_m_repeat_reads_its_threshold():
    s = _fixture("M-REPEAT").clean()
    assert not _found(s, "M-REPEAT")
    [f] = _found(s, "M-REPEAT", Profile("my", {}, {"max_repeat": 2}))
    assert (f.bar, f.beat, f.value) == (1, 3.0, 4.0)
    assert not _found(_fixture("M-REPEAT").trigger(), "M-REPEAT", Profile("my", {}, {"max_repeat": 6}))


@pytest.mark.parametrize("text", [
    "f4:q b4",  # an augmented fourth up
    "ab4:q b4",  # an augmented second up
    "b4:q ab4",  # an augmented second down
    "b4:q f4",  # an augmented fourth down
])
def test_m_augmented_finds(text):
    assert len(_found(_score(text), "M-AUGMENTED")) == 1


@pytest.mark.parametrize("text", [
    "f4:q c5",  # a fifth
    "g#4:q a4",  # a minor second
    "f4:q cb5",  # a diminished fifth is the same six semitones, spelled otherwise
    "f5:q b4",  # and so is this one, going down
    "ab4:q cb5",  # a minor third is the same three semitones, spelled otherwise
    "c4:q c#4",  # an augmented unison
    "c#4:q cb4 c##4 cb5",  # strange spellings do not crash
])
def test_m_augmented_passes(text):
    assert not _found(_score(text), "M-AUGMENTED")


def test_m_contour_shares_leave_repeats_out_of_steps_and_leaps():
    assert _values(_score("c4:q c d c"), "M-CONTOUR") == pytest.approx([2 / 3, 0.0, 1 / 3])


def test_m_contour_names_each_share():
    steps, leaps, upward = _found(_fixture("M-CONTOUR").trigger(), "M-CONTOUR")
    assert "steps" in steps.message and "leaps" in leaps.message and "up" in upward.message


def test_m_contour_is_a_metric_under_chorale():
    assert {f.severity for f in _found(_fixture("M-CONTOUR").trigger(), "M-CONTOUR", "chorale")} == {"metric"}


def test_m_leap_is_off_under_techno_and_only_m_range_stays():
    for rule in ("M-LEAP", "M-CLIMAX", "M-REPEAT", "M-AUGMENTED", "M-CONTOUR"):
        assert not _found(_fixture(rule).trigger(), rule, "techno")
    assert _values(_fixture("M-RANGE").trigger(), "M-RANGE", "techno") == [28.0]
    assert not _warnings(_fixture("M-RANGE").trigger(), "M-RANGE", "techno")


def test_pop_keeps_the_melody_rules_as_metrics():
    [f] = _found(_fixture("M-LEAP").trigger(), "M-LEAP", "pop")
    assert (f.severity, "profile" in f.message) == ("metric", False)
    assert not _warnings(_fixture("M-RANGE").trigger(), "M-RANGE", "pop")
    assert not _warnings(_fixture("M-CLIMAX").trigger(), "M-CLIMAX", "pop")


def test_each_profile_holds_the_m_row():
    rules = ("M-RANGE", "M-LEAP", "M-CLIMAX", "M-REPEAT", "M-AUGMENTED", "M-CONTOUR")
    assert [PROFILES["chorale"].severities[r] for r in rules] == ["warn"] * 5 + ["metric"]
    assert [PROFILES["pop"].severities[r] for r in rules] == ["metric"] * 6
    assert [PROFILES["techno"].severities[r] for r in rules] == ["metric"] + [None] * 5


def test_the_profiles_hold_the_thresholds():
    assert PROFILES["chorale"].params["max_range"] == 19
    assert PROFILES["chorale"].params["max_repeat"] == 4


def test_a_custom_profile_changes_a_threshold():
    s = _fixture("M-RANGE").clean()
    assert not _warnings(s, "M-RANGE")
    [f] = _warnings(s, "M-RANGE", Profile("my", {"M-RANGE": "warn"}, {"max_range": 12}))
    assert f.message.endswith(", a warning under the my profile")
    assert (f.bar, f.value) == (2, 16.0)
