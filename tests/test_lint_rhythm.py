from dataclasses import replace
from fractions import Fraction
from importlib import import_module

import pytest

from euterpe.lint.score import PROFILES, Profile, lint_score
from euterpe.lint.score.rhythm import phrase_ends
from euterpe.score import Score, drums, melody
from euterpe.theory import Meter

WARNINGS = [
    ("T-BACKBEAT", "pop", "drums", 1, 2.0),
    ("T-FOURFLOOR", "techno", "drums", 1, 2.0),
    ("T-TEMPO", "techno", None, 1, None),
]

METRICS = [
    ("T-STRONG", "alto", [4 / 9], []),
    ("T-SYNCOPATION", "alto", [1.0], [0.0]),
    ("T-DENSITY", "alto", [6.0, 8.0], [5 / 3, 4.0]),
    ("T-PHRASE", "alto", [4.0, 4.0], [8.0]),
    ("T-BACKBEAT", "drums", [0.0], [1.0]),
    ("T-FOURFLOOR", "drums", [0.5], [1.0]),
    ("T-TEMPO", None, [90.0, 90.0], [130.0, 130.0]),
]


def _fixture(rule):
    return import_module(f"tests.fixtures.score.{rule.lower().replace('-', '_')}")


def _found(score, rule, profile=None):
    return [f for f in lint_score(score, profile).findings if f.rule == rule]


def _values(score, rule, profile=None):
    return [f.value for f in _found(score, rule, profile)]


def _warnings(score, rule, profile):
    return [f for f in _found(score, rule, profile) if f.severity == "warn"]


def _score(text, **kwargs):
    s = Score(**kwargs)
    s.part("alto").add(melody(text))
    return s


def _drums(grid, **kwargs):
    s = Score(**kwargs)
    s.part("drums").add(drums(grid, step="q"))
    return s


@pytest.mark.parametrize("rule, part, trigger, clean", METRICS)
def test_a_metric_reports_its_known_values(rule, part, trigger, clean):
    fixture = _fixture(rule)
    assert _values(fixture.trigger(), rule) == pytest.approx(trigger)
    assert _values(fixture.clean(), rule) == pytest.approx(clean)
    assert {(f.severity, f.part) for f in _found(fixture.trigger(), rule)} == {("metric", part)}


@pytest.mark.parametrize("rule, profile, part, bar, beat", WARNINGS)
def test_trigger_warns_at_its_place_and_clean_does_not(rule, profile, part, bar, beat):
    fixture = _fixture(rule)
    [f] = _warnings(fixture.trigger(), rule, profile)
    assert (f.part, f.bar, f.beat) == (part, bar, beat)
    assert f.message.endswith(f", a warning under the {profile} profile")
    assert not _warnings(fixture.clean(), rule, profile)


def test_t_strong_counts_a_stack_and_two_voices_once_at_each_place():
    s = _score("<c4 e4>:q d4 e4 f4")
    s.part("alto").add(melody("c4:q d4 e4 f4"), voice=1, at=1)
    assert _values(s, "T-STRONG") == [0.5]


def test_t_strong_in_other_meters():
    assert _values(_score("c4:q d e", meter=Meter("3/4")), "T-STRONG") == pytest.approx([1 / 3])
    assert _values(_score("c4:q d", meter=Meter("2/4")), "T-STRONG") == [0.5]
    assert _values(_score("c4:e d e f g a", meter=Meter("6/8")), "T-STRONG") == pytest.approx([1 / 6])


def test_t_strong_does_not_count_a_tie_as_an_onset():
    assert _values(_score("c4:h~ c4:q d4"), "T-STRONG") == [0.5]


def test_t_strong_counts_a_pickup_from_the_end_of_its_bar():
    assert _values(_score("g4:q | c5:w", pickup=Fraction(1, 4)), "T-STRONG") == [0.5]


def test_t_strong_reads_hits_too():
    assert _values(_drums({"kick": "x.x.", "hihat": "...x"}), "T-STRONG") == pytest.approx([2 / 3])


def test_a_part_with_nothing_struck_reports_no_rhythm():
    for rule in ("T-STRONG", "T-SYNCOPATION", "T-DENSITY", "T-PHRASE", "T-BACKBEAT", "T-FOURFLOOR"):
        assert not _found(_score("R"), rule)


def test_a_score_with_no_bars_has_no_tempo():
    assert not _found(Score(), "T-TEMPO")


def test_t_syncopation_a_note_held_across_a_stronger_beat_needs_no_tie():
    assert _values(_score("c4:q d4:h e4:q"), "T-SYNCOPATION") == [1.0]


def test_t_syncopation_a_rest_on_a_stronger_beat_counts():
    assert _values(_score("c4:q d4:q r:q e4:q"), "T-SYNCOPATION") == [1.0]


def test_t_syncopation_a_note_tied_over_the_bar_line_counts_the_downbeat():
    assert _values(_score("c4:h d4:q e4:q~ | e4:q f4:q g4:h"), "T-SYNCOPATION") == [2.0]


def test_t_syncopation_a_downbeat_held_on_is_not_syncopated():
    assert _values(_score("c4:w | c4:h d4:h"), "T-SYNCOPATION") == [0.0]


def test_t_syncopation_a_triplet_is_not_syncopated_by_the_grid_it_is_not_on():
    assert _values(_score("3[c4:e d e] f4:q g4:h"), "T-SYNCOPATION") == [0.0]


def test_t_syncopation_a_quarter_triplet_is_not_syncopated():
    assert _values(_score("3[c4:q d e] f4:h"), "T-SYNCOPATION") == [0.0]


def test_t_syncopation_a_tuplet_note_tied_past_a_beat_counts():
    assert _values(_score("3[c4:e d e~] e4:e f4:e g4:h"), "T-SYNCOPATION") == [2.0]


@pytest.mark.parametrize("text", ["c4:q d4:q e4:q", "c4:q d4:q~ d4:e f4:e"])
def test_t_syncopation_in_6_8_sees_the_second_beat(text):
    assert _values(_score(text, meter=Meter("6/8")), "T-SYNCOPATION") == [1.0]


def test_t_syncopation_counts_within_the_beat():
    assert _values(_score("c4:s d4:e e4:s f4:q g4:h"), "T-SYNCOPATION") == [1.0]


def test_t_syncopation_after_a_pickup_counts_in_the_bar_it_borrows_from():
    assert _values(_score("g4:e a4:q~ | a4:e b4:e c5:q d5:h", pickup=Fraction(3, 8)), "T-SYNCOPATION") == [2.0]


def test_t_syncopation_inside_a_pickup_bar_counts_from_its_borrowed_beats():
    assert _values(_score("r:e c4:q. d4:q | e4:w", pickup=Fraction(3, 4)), "T-SYNCOPATION") == [2.0]


def test_t_syncopation_across_a_meter_change_finds_the_new_downbeat():
    s = _score("c4:h d4:q e4:e f4:e~ | f4:q g4:h")
    s.change(2, meter=Meter("3/4"))
    assert _values(s, "T-SYNCOPATION") == [3.0]


def test_t_syncopation_another_voice_on_the_beat_fills_it():
    s = _score("c4:q d4:h e4:q")
    s.part("alto").add(melody("c3:q g3 c3 g3"), voice=1, at=1)
    assert _values(s, "T-SYNCOPATION") == [0.0]


def test_t_density_finds_the_bar_of_the_largest():
    mean, largest = _found(_fixture("T-DENSITY").trigger(), "T-DENSITY")
    assert (mean.part, mean.bar) == ("alto", None)
    assert (largest.part, largest.bar) == ("alto", 2)


def test_t_density_says_one_onset_in_the_singular():
    _, largest = _found(_score("c4:w"), "T-DENSITY")
    assert largest.message == "at most 1 onset in a bar"


def test_t_phrase_says_one_bar_in_the_singular():
    [f] = _found(_score("c4:w"), "T-PHRASE")
    assert f.message == "a phrase of 1 bar, ending in bar 1"


def test_t_phrase_sits_at_the_bar_each_phrase_starts_in():
    assert [f.bar for f in _found(_fixture("T-PHRASE").trigger(), "T-PHRASE")] == [1, 5]


def test_t_phrase_a_rest_ends_a_phrase():
    assert _values(_score("c4:q d e f | g a r:h | c:q d e f"), "T-PHRASE") == [2.0, 1.0]


def test_t_phrase_a_note_of_half_a_bar_ends_a_phrase_in_the_meter_in_force():
    assert _values(_score("c4:q d e | f:q. g:e a:q | c:q d e", meter=Meter("3/4")), "T-PHRASE") == [2.0, 2.0]
    assert _values(_score("c4:q. d:q. | e:e f g a b c", meter=Meter("6/8")), "T-PHRASE") == [1.0, 1.0, 1.0]


def test_t_phrase_a_tied_note_ends_a_phrase_in_the_bar_it_stops():
    s = _score("c4:q d e f:q~ | f:q g a b | c d e f")
    assert phrase_ends(s.parts["alto"]) == [2, 3]
    assert _values(s, "T-PHRASE") == [2.0, 2.0]


def test_t_phrase_begins_where_the_first_note_is_after_a_rest():
    assert _values(_score("R | c4:q d e f | g a b c"), "T-PHRASE") == [2.0]
    assert _values(_score("c4:q d e r | R | R | c4:q d e f"), "T-PHRASE") == [1.0, 1.0]


def test_t_phrase_reads_each_voice():
    s = _score("c4:q d e f | g a b c")
    s.part("alto").add(melody("c3:w | c3:w"), voice=1, at=1)
    phrases = _found(s, "T-PHRASE")
    assert [f.value for f in phrases] == [2.0, 1.0, 1.0]
    assert "voice 1" in phrases[1].message


def test_phrase_ends_are_the_bars_a_phrase_stops_in():
    s = _fixture("T-PHRASE").trigger()
    assert phrase_ends(s.parts["alto"]) == [4, 8]
    assert phrase_ends(_fixture("T-PHRASE").clean().parts["alto"]) == [8]
    assert phrase_ends(_score("R").parts["alto"]) == []


def test_two_phrases_ending_in_one_bar_are_one_end():
    assert phrase_ends(_score("c4:q r d r | e f g a").parts["alto"]) == [1, 2]


def test_phrase_ends_reads_the_voice_it_is_given():
    s = _score("c4:q d e f | g a b c")
    s.part("alto").add(melody("c3:w | c3:w"), voice=1, at=1)
    assert phrase_ends(s.parts["alto"], 1) == [1, 2]


def test_t_backbeat_a_part_with_no_drums_reports_nothing():
    assert not _found(_score("c4:q d e f"), "T-BACKBEAT", "pop")
    assert not _found(_score("c4:q d e f"), "T-FOURFLOOR", "techno")


def test_t_backbeat_is_a_share_of_bars_that_hold_hits():
    s = _drums({"snare": ".x.x | x.x. | .x.x | .x.."})
    assert _values(s, "T-BACKBEAT") == [0.5]
    s = _drums({"snare": ".x.x | .... | .x.x"})
    assert _values(s, "T-BACKBEAT") == [1.0]


def test_t_backbeat_warns_only_below_its_threshold():
    half = _drums({"snare": ".x.x | x.x."})
    assert not _warnings(half, "T-BACKBEAT", "pop")
    [f] = _warnings(_drums({"snare": ".x.x | x.x. | x.x."}), "T-BACKBEAT", "pop")
    assert (f.bar, f.beat) == (2, 2.0)


def test_t_backbeat_is_a_warning_under_pop_and_a_metric_with_no_profile():
    s = _fixture("T-BACKBEAT").trigger()
    assert not _warnings(s, "T-BACKBEAT", None)
    assert _warnings(s, "T-BACKBEAT", "pop")
    assert not _warnings(s, "T-BACKBEAT", "chorale")
    assert not _warnings(s, "T-BACKBEAT", "techno")


def test_t_backbeat_finds_a_missing_four():
    [f] = _warnings(_drums({"snare": ".x.."}), "T-BACKBEAT", "pop")
    assert (f.bar, f.beat) == (1, 4.0)


def test_t_backbeat_in_other_meters():
    s = Score(meter=Meter("6/8"))
    s.part("drums").add(drums({"snare": "...x.."}, step="e"))
    assert _values(s, "T-BACKBEAT") == [1.0]
    s = Score(meter=Meter("1/4"))
    s.part("drums").add(drums({"snare": "x"}, step="q"))
    assert not _found(s, "T-BACKBEAT")


def test_a_pickup_is_held_only_to_the_beats_it_has():
    s = Score(pickup=Fraction(1, 4))
    s.part("drums").add(drums({"kick": "x | xxxx", "snare": "x | .x.x"}, step="q"))
    assert _values(s, "T-BACKBEAT") == [1.0]
    assert _values(s, "T-FOURFLOOR") == [1.0]


def test_a_hit_between_the_beats_is_not_on_them():
    s = Score()
    s.part("drums").add(drums({"kick": "xx.x.x.x"}, step="e"))
    assert _values(s, "T-FOURFLOOR") == [0.25]


def test_t_fourfloor_warns_only_below_its_threshold():
    s = _drums({"kick": "xxxx | xxxx | xxxx | xxxx | xxxx | xxx."})
    assert _values(s, "T-FOURFLOOR") == pytest.approx([23 / 24])
    assert not _warnings(s, "T-FOURFLOOR", "techno")
    assert not _warnings(_fixture("T-FOURFLOOR").trigger(), "T-FOURFLOOR", "pop")


def test_t_tempo_reads_changes_and_ramps():
    s = _score("c4:w | c4:w | c4:w | c4:w", tempo=120)
    s.ramp(2, 2, 90)
    assert _values(s, "T-TEMPO") == [90.0, 120.0]
    s = _score("c4:w | c4:w", tempo=120)
    s.change(2, tempo=140)
    assert _values(s, "T-TEMPO") == [120.0, 140.0]


def test_t_tempo_reaches_a_ramp_that_ends_with_the_piece():
    s = _score("c4:w", tempo=120)
    s.ramp(1, 1, 90)
    assert _values(s, "T-TEMPO") == [90.0, 120.0]
    [f] = _warnings(s, "T-TEMPO", Profile("my", {"T-TEMPO": "warn"}, {"tempo": (100, 150)}))
    assert (f.bar, f.value) == (1, 90.0)


def test_t_tempo_reads_a_ramp_the_piece_cuts_off_where_it_stops():
    s = _score("c4:w | c4:w", tempo=120)
    s.ramp(1, 4, 60)
    assert _values(s, "T-TEMPO") == [90.0, 120.0]


def test_t_tempo_warns_at_the_bar_a_ramp_arrives_before_a_later_downbeat():
    s = _score("c4:w | c4:w", tempo=120)
    s.ramp(1, 1, 90)
    [f] = _warnings(s, "T-TEMPO", Profile("my", {"T-TEMPO": "warn"}, {"tempo": (100, 150)}))
    assert f.bar == 1


def test_t_tempo_is_a_float_however_it_is_written():
    assert all(isinstance(f.value, float) for f in _found(_fixture("T-TEMPO").trigger(), "T-TEMPO", "techno"))


def test_t_tempo_does_not_read_a_change_past_the_last_bar():
    s = _score("c4:w", tempo=130)
    s.change(2, tempo=60)
    s.ramp(3, 2, 40)
    assert _values(s, "T-TEMPO") == [130.0, 130.0]


def test_t_tempo_warns_at_the_first_bar_outside_the_range():
    s = _score("c4:w | c4:w | c4:w", tempo=130)
    s.change(3, tempo=160)
    [f] = _warnings(s, "T-TEMPO", "techno")
    assert (f.bar, f.value) == (3, 160.0)


def test_each_profile_holds_the_t_row():
    expected = {"chorale": {}, "pop": {"T-BACKBEAT"}, "techno": {"T-FOURFLOOR", "T-TEMPO"}}
    for name, warned in expected.items():
        held = PROFILES[name].severities
        for rule in ("T-STRONG", "T-SYNCOPATION", "T-DENSITY", "T-PHRASE", "T-BACKBEAT", "T-FOURFLOOR", "T-TEMPO"):
            assert held[rule] == ("warn" if rule in warned else "metric")


def test_the_profiles_hold_the_thresholds():
    assert PROFILES["pop"].params["min_backbeat"] == 0.5
    assert PROFILES["techno"].params["min_floor"] == 0.9
    assert PROFILES["techno"].params["tempo"] == (118, 150)


def test_a_custom_profile_changes_a_threshold():
    s = _fixture("T-TEMPO").clean()
    assert not _warnings(s, "T-TEMPO", "techno")
    mine = replace(PROFILES["techno"], name="my", params={"tempo": (60, 100)})
    [f] = _warnings(s, "T-TEMPO", mine)
    assert (f.value, f.message.endswith(", a warning under the my profile")) == (130.0, True)
    assert not _warnings(_drums({"kick": "x.x."}), "T-FOURFLOOR", Profile("my", {"T-FOURFLOOR": "warn"}, {"min_floor": 0.5}))


def test_a_custom_profile_without_the_param_uses_the_default():
    [f] = _warnings(_fixture("T-BACKBEAT").trigger(), "T-BACKBEAT", Profile("my", {"T-BACKBEAT": "warn"}))
    assert f.bar == 1
