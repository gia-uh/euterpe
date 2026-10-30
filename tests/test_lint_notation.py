from fractions import Fraction
from importlib import import_module

import pytest

from euterpe.instruments.core import Accent, Feedback, Legato, PalmMute, Staccato, Tenuto
from euterpe.lint.score import lint_score
from euterpe.pitch import C4, E4
from euterpe.score import Line, Note, Rest, Score, melody
from euterpe.theory import Key, Meter

CASES = [
    ("N-MEASURE", "error", "alto", 2, 5.0),
    ("N-TUPLET", "error", "alto", 1, 2.0),
    ("N-TIE", "error", "alto", 1, 3.0),
    ("N-SPELLING", "warn", "alto", 1, 2.0),
    ("N-ARTIC", "warn", "alto", 1, 3.0),
]


def _found(score, rule):
    return [f for f in lint_score(score).findings if f.rule == rule]


def _score(text, **kwargs):
    s = Score(**kwargs)
    s.part("alto").add(melody(text))
    return s


@pytest.mark.parametrize("rule, severity, part, bar, beat", CASES)
def test_trigger_finds_the_rule_and_clean_does_not(rule, severity, part, bar, beat):
    fixture = import_module(f"tests.fixtures.score.{rule.lower().replace('-', '_')}")
    [f] = _found(fixture.trigger(), rule)
    assert (f.severity, f.part, f.bar, f.beat) == (severity, part, bar, beat)
    assert not _found(fixture.clean(), rule)


def test_a_bar_of_r_passes_in_any_meter():
    s = Score(meter=Meter("6/8"))
    s.part("alto").add(melody("R | c4:e d e f g a | R"))
    assert not _found(s, "N-MEASURE")


def test_a_short_bar_reports_where_the_voice_stops():
    [f] = _found(_score("c4:q d e | f g a b"), "N-MEASURE")
    assert (f.bar, f.beat, f.value) == (1, 4.0, 0.75)


def test_an_empty_voice_in_a_bar_is_not_a_short_bar():
    s = Score()
    s.part("alto").add(melody("c4:w")).add(melody("e4:w"), voice=1, at=2).add(melody("d4:w"), at=2)
    assert not _found(s, "N-MEASURE")


def test_a_full_bar_of_another_voice_does_not_hide_a_short_one():
    s = Score()
    s.part("alto").add(melody("c4:w")).add(melody("e4:h"), voice=1, at=1)
    [f] = _found(s, "N-MEASURE")
    assert (f.part, f.bar, f.beat) == ("alto", 1, 3.0)


def test_a_correct_pickup_passes():
    assert not _found(_score("g4:q | c5:w | c5:h.", pickup=Fraction(1, 4)), "N-MEASURE")


def test_a_full_last_bar_after_a_pickup_passes():
    assert not _found(_score("g4:q | c5:w | c5:w", pickup=Fraction(1, 4)), "N-MEASURE")


def test_a_short_last_bar_needs_a_pickup():
    [f] = _found(_score("c5:w | c5:h."), "N-MEASURE")
    assert (f.bar, f.beat) == (2, 4.0)


def test_a_last_bar_must_complete_the_pickup_exactly():
    [f] = _found(_score("g4:q | c5:w | c5:h", pickup=Fraction(1, 4)), "N-MEASURE")
    assert (f.bar, f.beat) == (3, 3.0)


def test_only_the_last_bar_may_complete_a_pickup():
    [f] = _found(_score("g4:q | c5:h. | c5:w", pickup=Fraction(1, 4)), "N-MEASURE")
    assert f.bar == 2


def test_a_short_part_ending_before_the_score_does_not_complete_a_pickup():
    s = _score("g4:q | c5:h.", pickup=Fraction(1, 4))
    s.part("bass").add(melody("g3:q | c3:w | c3:h."))
    [f] = _found(s, "N-MEASURE")
    assert (f.part, f.bar) == ("alto", 2)


def test_a_pickup_that_runs_over_counts_from_the_end_of_the_bar():
    [f] = _found(_score("g4:h | c5:w", pickup=Fraction(1, 4)), "N-MEASURE")
    assert (f.bar, f.beat) == (1, 4.0)


def test_a_beat_counts_the_meters_groups():
    s = Score(meter=Meter("7/8", groups=(2, 2, 3)))
    s.part("alto").add(melody("c4:e d e f g a b c5"))
    [f] = _found(s, "N-MEASURE")
    assert f.beat == 4.0
    s = Score(meter=Meter("6/8"))
    s.part("alto").add(melody("c4:e d e f g"))
    assert _found(s, "N-MEASURE")[0].beat == pytest.approx(2 + 2 / 3)


def test_two_triplets_in_a_row_fill_and_one_and_a_half_do_not():
    assert not _found(_score("3[c4:e d e] 3[f g a] c5:h"), "N-TUPLET")
    assert _found(_score("3[c4:e d e] 3[f g] c5:h"), "N-TUPLET")


def test_a_triplet_of_mixed_values_fills():
    assert not _found(_score("3[c4:q d:e] e4:q f:h"), "N-TUPLET")


def test_a_rest_counts_in_a_tuplet_and_a_duplet_fills_on_two():
    assert not _found(_score("3[r:e d4 e4] f4:q g4:h"), "N-TUPLET")
    assert not _found(_score("2:3[c4:e d] e4:e f g a b"), "N-TUPLET")
    assert _found(_score("2:3[c4:e] e4:e f g a b"), "N-TUPLET")


def test_a_tie_with_a_rest_or_nothing_after_it():
    [f] = _found(_score("c4:w~"), "N-TIE")
    assert "nothing" in f.message and (f.bar, f.beat) == (1, 1.0)
    assert _found(_score("c4:h~ r:h"), "N-TIE")


def test_a_tie_across_a_bar_joins():
    assert not _found(_score("c4:w~ | c4:w"), "N-TIE")


def test_a_tie_over_an_empty_bar_has_nothing_after_it():
    s = Score()
    s.part("alto").add(melody("c4:w~")).add(melody("c4:w"), at=3)
    assert _found(s, "N-TIE")


def test_a_stack_ties_pitch_by_pitch():
    assert not _found(_score("<c4 e4>:h~ <c4 g4>:h"), "N-TIE")
    assert _found(_score("<c4 e4>:h~ <d4 g4>:h"), "N-TIE")


def test_a_tie_to_another_spelling_is_another_pitch():
    assert _found(_score("c#4:h~ db4:h"), "N-TIE")


def test_ties_read_each_voice_alone():
    s = Score()
    s.part("alto").add(melody("c4:h~ c4:h")).add(melody("e4:h e4:h"), voice=1, at=1)
    assert not _found(s, "N-TIE")


def test_a_raised_fourth_keeps_its_spelling():
    assert not _found(_score("c4:q f#4 g4 c5"), "N-SPELLING")


def test_a_note_the_key_does_not_name_may_be_spelled_either_way():
    assert not _found(_score("c4:q ab4 g#4 c5"), "N-SPELLING")


def test_a_note_of_the_key_under_another_name_is_found():
    [f] = _found(_score("c4:q cb4 g4 c5"), "N-SPELLING")
    assert "Cb4" in f.message and "B3" in f.message


def test_spelling_follows_a_key_change():
    s = _score("c4:q db5 g4 c5 | d4:q db5 a4 d5")
    s.change(2, key=Key("D major"))
    [f] = _found(s, "N-SPELLING")
    assert (f.bar, f.beat) == (2, 2.0)


@pytest.mark.parametrize("pair, found", [
    ((Staccato(), Feedback()), True),
    ((Legato(), Staccato()), True),
    ((Tenuto(), Accent()), False),
    ((Tenuto(), Staccato()), False),
    ((PalmMute(), Accent()), False),
    ((PalmMute(),), False),
])
def test_two_articulations_an_instrument_reads(pair, found):
    s = Score()
    s.part("alto").add(Line([[Note((C4, E4), Fraction(1), articulations=pair)]]))
    assert bool(_found(s, "N-ARTIC")) is found


def test_rests_and_empty_parts_have_no_notation_findings():
    s = Score()
    s.part("alto").add(Line([[Rest(1)]]))
    s.part("empty")
    assert lint_score(s).findings == []


def test_a_bar_far_over_its_meter_is_one_finding_and_leaves_the_next_bar_alone():
    [f] = _found(_score("c4:q d e f g a | c4:q d e f"), "N-MEASURE")
    assert (f.bar, f.beat, f.value) == (1, 5.0, 1.5)
