from fractions import Fraction
from importlib import import_module

import pytest

from euterpe.lint.score import Profile, lint_score
from euterpe.score import Score, melody
from euterpe.theory import Key

ALL_ON = Profile("all", dict.fromkeys(
    ("V-PARALLEL", "V-DIRECT", "V-CROSSING", "V-OVERLAP", "V-SPACING", "V-RANGE", "V-DOUBLING"), "warn"))

LOCATED = [
    ("V-PARALLEL", "error", "alto", 3, 2.0),
    ("V-DIRECT", "warn", "soprano", 1, 3.0),
    ("V-CROSSING", "warn", "alto", 1, 3.0),
    ("V-OVERLAP", "warn", "tenor", 1, 3.0),
    ("V-SPACING", "warn", "alto", 1, 3.0),
    ("V-RANGE", "warn", "soprano", 1, 3.0),
    ("V-DOUBLING", "warn", "tenor", 1, 3.0),
]


def _fixture(rule):
    return import_module(f"tests.fixtures.score.{rule.lower().replace('-', '_')}")


def _found(score, rule, profile=ALL_ON):
    return [f for f in lint_score(score, profile).findings if f.rule == rule]


def _score(*voices, **kwargs):
    s = Score(**kwargs)
    for name, text in zip(("soprano", "alto", "tenor", "bass"), voices):
        s.part(name).add(melody(text))
    return s


@pytest.mark.parametrize("rule, severity, part, bar, beat", LOCATED)
def test_trigger_finds_the_rule_at_its_place_and_clean_does_not(rule, severity, part, bar, beat):
    fixture = _fixture(rule)
    [f] = _found(fixture.trigger(), rule, "chorale")
    assert (f.severity, f.part, f.bar, f.beat) == (severity, part, bar, beat)
    assert not _found(fixture.clean(), rule, "chorale")


@pytest.mark.parametrize("rule", [row[0] for row in LOCATED])
def test_v_rules_are_off_with_no_profile(rule):
    assert not _found(_fixture(rule).trigger(), rule, None)


def test_v_parallel_says_what_it_found_under_the_chorale_profile():
    [f] = _found(_fixture("V-PARALLEL").trigger(), "V-PARALLEL", "chorale")
    expected = "part alto, bar 3, beat 2: parallel fifths with the soprano (D4–A4 to E4–B4), an error under the chorale profile"
    assert f.place + f.message == expected
    assert f.value == 7.0


def test_the_corrected_chorale_breaks_no_voice_rule():
    findings = lint_score(_fixture("V-PARALLEL").clean(), "chorale").findings
    assert [f.rule for f in findings if f.rule[0] == "V"] == []


def test_the_chorale_with_fifths_breaks_only_that_rule():
    findings = lint_score(_fixture("V-PARALLEL").trigger(), "chorale").findings
    assert [f.rule for f in findings if f.rule[0] == "V"] == ["V-PARALLEL"]


def test_v_parallel_is_a_metric_under_pop_naming_no_profile():
    [f] = _found(_fixture("V-PARALLEL").trigger(), "V-PARALLEL", "pop")
    assert f.severity == "metric" and "profile" not in f.message


@pytest.mark.parametrize("top, low, kind", [
    ("g4:h a4:h", "c4:h d4:h", "fifths"),
    ("g5:h a5:h", "c4:h d4:h", "fifths"),  # a twelfth is a fifth
    ("c5:h d5:h", "c4:h d4:h", "octaves"),
    ("c6:h d6:h", "c4:h d4:h", "octaves"),
    ("c4:h d4:h", "c4:h d4:h", "unisons"),
    ("a4:h g4:h", "d4:h c4:h", "fifths"),
    ("c5:h d5:h", "c4:h d5:h", "unisons"),  # an octave going to a unison the same way
])
def test_v_parallel_reads_each_perfect_interval_both_ways(top, low, kind):
    [f] = _found(_score(top, low), "V-PARALLEL")
    assert f"parallel {kind}" in f.message


@pytest.mark.parametrize("top, low", [
    ("g4:h g4:h", "c4:h d4:h"),  # oblique
    ("g4:h f4:h", "c4:h d4:h"),  # contrary
    ("g4:h a4:h", "c4:h c#4:h"),  # a fifth to a sixth in the same direction
    ("g4:h f4:h", "c4:h b3:h"),  # a perfect fifth to a diminished one
    ("c5:h a4:h", "c4:h d4:h"),  # an octave to a fifth
    ("ab4:h bb4:h", "c#4:h d#4:h"),  # sounds like fifths, spelled as sixths
    ("g4:q a4:q b4:h", "c4:h d4:h"),  # the voices do not move together
    ("c5:h d5:h", "g4:h a4:h"),  # fourths
])
def test_v_parallel_leaves_other_motion_alone(top, low):
    assert not _found(_score(top, low), "V-PARALLEL")


def test_v_parallel_reads_a_tied_note_as_held():
    assert _found(_score("g4:h~ g4:q a4:q", "c4:h c4:q d4:q"), "V-PARALLEL")
    assert not _found(_score("g4:h~ g4:h", "c4:h d4:h"), "V-PARALLEL")


def test_v_parallel_compares_only_where_both_lines_sound():
    assert not _found(_score("g4:q r:q a4:h", "c4:q r:q d4:h"), "V-PARALLEL")
    assert not _found(_score("g4:q r:q a4:h", "c4:q d4:q e4:h"), "V-PARALLEL")


def test_a_stack_going_from_three_pitches_to_two_leaves_the_missing_line_as_a_rest():
    s = Score()
    s.part("choir").add(melody("<c4 e4 g4>:h <d4 f4>:h"))
    assert not _found(s, "V-PARALLEL")  # g4 has no note to go to: the fifth from c4 is not compared with d4
    s = Score()
    s.part("choir").add(melody("<c4 g4 c5>:h <d4 a4>:h"))
    [f] = _found(s, "V-PARALLEL")
    assert f.part == "choir" and "with another line (C4–G4 to D4–A4)" in f.message


def test_each_voice_of_a_part_is_a_line_and_a_finding_names_its_voice():
    s = Score()
    s.part("p").add(melody("g4:h a4:h"))
    s.part("p").add(melody("c4:h d4:h"), voice=1)
    [f] = _found(s, "V-PARALLEL")
    assert f.part == "p"
    assert f.message.startswith("voice 1: parallel fifths with another line (C4–G4 to D4–A4)")


def test_thin_and_uneven_scores_do_not_crash_the_v_rules():
    assert [f.rule for f in lint_score(Score(), ALL_ON).findings] == ["V-SPACING", "V-RANGE"]
    s = Score()
    s.part("empty")
    s.part("bass").add(melody("c3:w"))
    assert not _found(s, "V-PARALLEL")
    assert not _found(_score("g4:h g4:h | b4:w", "c4:h d4:h"), "V-CROSSING")


def test_v_rules_place_a_pickup_from_the_end_of_its_bar():
    s = _score("g4:q | a4:h g4:h", "c4:q | d4:h e4:h", pickup=Fraction(1, 4))
    [f] = _found(s, "V-PARALLEL")
    assert (f.part, f.bar, f.beat) == ("alto", 2, 1.0)
    s = _score("e5:q | e5:w", "c5:q | c5:h g5:h", pickup=Fraction(1, 4))
    [f] = _found(s, "V-CROSSING")
    assert (f.bar, f.beat) == (2, 3.0)
    s = _score("e5:e e5:e | e5:w", "c5:e g5:e | c5:w", pickup=Fraction(1, 4))
    [f] = _found(s, "V-CROSSING")
    assert (f.bar, f.beat) == (1, 4.5)


def test_v_direct_reads_only_the_outer_voices():
    assert _found(_score("g4:h c5:h", "e4:h e4:h", "c4:h c4:h", "a3:h c4:h"), "V-DIRECT")
    assert not _found(_score("c6:h c6:h", "g4:h c5:h", "c4:h c4:h", "a3:h c4:h"), "V-DIRECT")


def test_v_direct_reaches_a_fifth_or_an_octave_and_leaves_the_rest():
    assert _found(_score("d4:h g4:h", "a3:h c4:h"), "V-DIRECT")  # a fifth
    assert not _found(_score("g4:h c5:h", "a3:h b3:h"), "V-DIRECT")  # a minor ninth
    assert not _found(_score("g4:h c5:h", "d4:h c4:h"), "V-DIRECT")  # contrary
    assert not _found(_score("g4:h c5:h", "c4:h f4:h"), "V-DIRECT")  # parallel fifths are V-PARALLEL's
    assert not _found(_score("c4:h g4:h", "b3:h d4:h"), "V-DIRECT")  # a fourth


def test_v_direct_needs_two_lines():
    assert not _found(_score("g4:h c5:h"), "V-DIRECT")


def test_v_crossing_reports_where_it_starts_and_counts_every_pair():
    [f] = _found(_score("e5:w", "c5:q g5:q g5:q c5:q"), "V-CROSSING")
    assert (f.beat, f.value) == (2.0, 3.0)
    assert "G5" in f.message and "E5" in f.message
    assert len(_found(_score("e5:w", "c5:q g5:q c5:q g5:q"), "V-CROSSING")) == 2
    assert len(_found(_score("g4:w", "e4:w", "c4:h a4:h"), "V-CROSSING")) == 2  # above the alto and the soprano
    assert not _found(_score("c5:w", "c5:w"), "V-CROSSING")  # a unison is not a crossing


def test_v_overlap_reads_neighbours_either_way():
    [f] = _found(_score("e4:h b3:h", "c4:h a3:h"), "V-OVERLAP")
    assert (f.part, f.value) == ("soprano", -1.0)
    [f] = _found(_score("e4:h g4:h", "c4:h f4:h"), "V-OVERLAP")
    assert (f.part, f.value) == ("alto", 1.0)


def test_v_overlap_leaves_lines_already_crossed_to_v_crossing():
    s = _score("c5:q d5:q c5:h | c6:w", "g5:q f5:q g5:h | c4:w")
    assert not _found(s, "V-OVERLAP")
    assert len(_found(s, "V-CROSSING")) == 1


def test_v_overlap_is_a_crossing_when_the_neighbour_stays():
    s = _score("e4:w", "c4:h f4:h")
    assert not _found(s, "V-OVERLAP")
    assert _found(s, "V-CROSSING")


def test_v_overlap_reads_only_neighbours():
    assert not _found(_score("c5:h b4:h", "e4:h f4:h", "c4:h d4:h"), "V-OVERLAP")


@pytest.mark.parametrize("rule", ["V-RANGE", "V-SPACING"])
@pytest.mark.parametrize("voices", [("c5:w",), ("c5:w", "g4:w", "c4:w")])
def test_range_and_spacing_on_any_other_count_report_one_metric_saying_so(rule, voices):
    [f] = _found(_score(*voices), rule, "chorale")
    assert (f.severity, f.value) == ("metric", float(len(voices)))
    assert f"{len(voices)} line" in f.message and "four" in f.message and "profile" not in f.message
    assert (f.part, f.bar, f.beat) == (None, None, None)


@pytest.mark.parametrize("rule", ["V-RANGE", "V-SPACING"])
def test_a_stack_of_four_counts_as_four_lines(rule):
    s = Score()
    s.part("choir").add(melody("<c3 g3 e4 c5>:w"))
    assert not _found(s, rule, "chorale")


def test_v_spacing_leaves_the_tenor_and_bass_alone():
    assert not _found(_score("c5:w", "g4:w", "c4:w", "c2:w"), "V-SPACING")
    [f] = _found(_score("c6:w", "g5:w", "c4:w", "c3:w"), "V-SPACING")
    assert (f.part, f.value) == ("tenor", 19.0)
    assert not _found(_score("c5:w", "c4:w", "g3:w", "c3:w"), "V-SPACING")  # an octave is fine


@pytest.mark.parametrize("voices, part, value", [
    (("a5:w", "g4:w", "c4:w", "c3:w"), "soprano", 2.0),
    (("b3:w", "b3:w", "b3:w", "b2:w"), "soprano", -1.0),
    (("g5:w", "e5:w", "c4:w", "c3:w"), "alto", 2.0),
    (("g4:w", "f3:w", "c3:w", "c2:w"), "alto", -2.0),
    (("g5:w", "c5:w", "a4:w", "c3:w"), "tenor", 2.0),
    (("g5:w", "c5:w", "b2:w", "b2:w"), "tenor", -1.0),
    (("g5:w", "d5:w", "g4:w", "d4:w"), "bass", 2.0),
    (("g5:w", "d5:w", "g4:w", "d2:w"), "bass", -2.0),
])
def test_v_range_names_the_voice_and_how_far_outside(voices, part, value):
    assert [(f.part, f.value) for f in _found(_score(*voices), "V-RANGE") if f.part == part] == [(part, value)]


def test_v_range_takes_each_range_with_its_ends():
    assert not _found(_score("c4:h g5:h", "g3:h d5:h", "c3:h g4:h", "e2:h c4:h"), "V-RANGE")


def test_v_doubling_follows_the_key_in_force():
    s = _score("b4:w | c#5:w", "g4:w | a4:w", "b3:w | c#4:w", "g2:w | a2:w")
    s.change(2, key=Key("D major"))
    assert [(f.bar, f.value) for f in _found(s, "V-DOUBLING")] == [(1, 2.0), (2, 2.0)]


def test_v_doubling_reads_a_key_change_under_notes_tied_across_it():
    s = _score("c#5:w~ | c#5:w", "c#4:w~ | c#4:w")
    s.change(2, key=Key("D major"))
    [f] = _found(s, "V-DOUBLING")
    assert (f.part, f.bar, f.beat, f.value) == ("alto", 2, 1.0, 2.0)


def test_v_doubling_counts_once_when_tied_over_a_bar_in_one_key():
    [f] = _found(_score("b4:w~ | b4:w", "b3:w~ | b3:w"), "V-DOUBLING")
    assert (f.bar, f.beat) == (1, 1.0)


def test_v_doubling_reads_the_raised_seventh_of_minor_and_its_spelling():
    assert _found(_score("g#4:w", "g#3:w", key=Key("A minor")), "V-DOUBLING")
    assert not _found(_score("g4:w", "g3:w", key=Key("A minor")), "V-DOUBLING")
    assert not _found(_score("cb5:w", "cb4:w"), "V-DOUBLING")


def test_v_doubling_counts_once_while_it_lasts():
    [f] = _found(_score("b4:q b4:q b4:h", "g4:w", "b3:h b3:h"), "V-DOUBLING")
    assert (f.part, f.beat) == ("tenor", 1.0)
