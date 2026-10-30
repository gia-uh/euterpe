from dataclasses import replace
from fractions import Fraction

import pytest

from euterpe.lint import Report, lint_audio
from euterpe.lint.score import PROFILES, Profile, Rule, lines, lint_piece, lint_score
from euterpe.pitch import Pitch
from euterpe.score import Score, melody
from tests.fixtures.score import n_measure, n_spelling, r_playable
from tests.helpers import Theremin


def _short(text="a4:q", tempo=480):
    s = Score(tempo=tempo)
    s.part("alto", Theremin()).add(melody(text))
    return s


def test_an_empty_score_has_no_findings():
    assert Score().lint().findings == []
    assert lint_piece(Score()).findings == []


def test_a_part_with_no_notes_has_no_findings():
    s = Score()
    s.part("alto", Theremin())
    assert s.lint().findings == []


def test_lint_is_lint_score():
    s = n_measure.trigger()
    assert s.lint() == lint_score(s)
    assert isinstance(s.lint(), Report)


def test_rules_run_in_the_order_of_the_spec():
    s = Score()
    s.part("alto", Theremin()).add(melody("b7:q~ c4:q gb4:q"))
    assert [f.rule for f in s.lint().findings if f.severity == "error"][:3] == ["N-MEASURE", "N-TIE", "R-PLAYABLE"]


def test_a_rule_is_a_small_object():
    rule = Rule("X", "N", "the notes", "warn", lambda score, params, severity: [])
    assert (rule.id, rule.group, rule.reads, rule.severity, rule.check(None, {}, "warn")) == ("X", "N", "the notes", "warn", [])


@pytest.mark.parametrize("name", ["chorale", "pop", "techno"])
def test_notation_and_instrument_rules_are_the_same_in_every_profile(name):
    for fixture in (n_measure, n_spelling, r_playable):
        s = fixture.trigger()
        assert s.lint(name) == s.lint() == lint_score(s, PROFILES[name])


@pytest.mark.parametrize("name", ["chorale", "pop", "techno"])
def test_each_profile_holds_the_same_n_r_and_a_rows(name):
    held = PROFILES[name].severities
    assert PROFILES[name].name == name
    assert (held["N-MEASURE"], held["N-SPELLING"], held["N-ARTIC"]) == ("error", "warn", "warn")
    assert (held["R-PLAYABLE"], held["R-COMFORT"], held["R-POLYPHONY"], held["R-ARTIC"]) == ("error", "warn", "warn", "warn")
    assert (held["A-CLIP"], held["A-LUFS"], held["A-PEAK"], held["A-BALANCE-LOW"]) == ("error", "metric", "metric", "metric")


def test_none_turns_a_rule_off():
    s = n_measure.trigger()
    assert not lint_score(s, Profile("my", {"N-MEASURE": None})).findings


def test_a_profile_raising_a_rule_says_so_in_its_message():
    [f] = lint_score(n_spelling.trigger(), Profile("my", {"N-SPELLING": "error"})).findings
    assert f.severity == "error" and f.message.endswith(", an error under the my profile")
    [f] = lint_score(n_measure.trigger(), Profile("my", {"N-MEASURE": "warn"})).findings
    assert f.severity == "warn" and f.message.endswith(", a warning under the my profile")


def test_a_profile_lowering_a_rule_to_a_metric_names_no_profile():
    [f] = lint_score(n_measure.trigger(), Profile("my", {"N-MEASURE": "metric"})).findings
    assert f.severity == "metric" and "profile" not in f.message


def test_a_profile_leaving_a_rule_alone_names_no_profile():
    [f] = lint_score(n_measure.trigger(), "chorale").findings
    assert f.severity == "error" and "profile" not in f.message


def test_a_rule_reads_its_profiles_params(monkeypatch):
    import euterpe.lint.score as package

    seen = []
    rule = Rule("X", "N", "nothing", "warn", lambda score, params, severity: seen.append((params, severity)) or [])
    monkeypatch.setattr(package, "RULES", (rule,))
    lint_score(Score(), Profile("my", {"X": "error"}, {"limit": 3}))
    lint_score(Score())
    assert seen == [({"limit": 3}, "error"), ({}, "warn")]


def test_a_copy_of_a_profile_is_a_profile():
    mine = replace(PROFILES["pop"], name="my", severities={**PROFILES["pop"].severities, "N-MEASURE": None})
    assert not lint_score(n_measure.trigger(), mine).findings
    assert PROFILES["pop"].severities["N-MEASURE"] == "error"


def test_an_unknown_profile_raises_naming_the_ones_there_are():
    with pytest.raises(ValueError, match="baroque.*chorale, pop, techno"):
        Score().lint("baroque")


def test_lint_piece_is_the_score_rules_then_the_audio_rules():
    s = _short("b7:q")
    report = lint_piece(s, audio=False)
    assert report == lint_score(s)
    rules = [f.rule for f in lint_piece(s).findings]
    assert rules.index("R-PLAYABLE") < rules.index("A-PEAK") and rules.index("N-MEASURE") < rules.index("A-PEAK")


def test_lint_piece_runs_lint_audio_on_the_render():
    s = _short()
    audio = lint_audio(s.play(3).take().samples)
    assert lint_piece(s, seed=3).findings[-len(audio.findings):] == audio.findings


def test_lint_piece_plays_from_its_seed(monkeypatch):
    seeds = []
    played = Score.play
    monkeypatch.setattr(Score, "play", lambda self, seed=0: seeds.append(seed) or played(self, seed))
    lint_piece(_short(), seed=3)
    assert seeds == [3]


def test_audio_rules_are_unchanged_under_every_profile():
    s = _short()
    plain = [f for f in lint_piece(s).findings if f.rule.startswith("A-")]
    assert plain
    for name in PROFILES:
        assert [f for f in lint_piece(s, name).findings if f.rule.startswith("A-")] == plain


def test_a_profile_may_turn_off_an_audio_rule():
    report = lint_piece(_short(), Profile("my", {"A-PEAK": None}))
    assert report.value("A-PEAK") is None and "A-PEAK" not in [f.rule for f in report.findings]


def test_a_profile_raising_an_audio_rule_says_so_in_its_message():
    report = lint_piece(_short(), Profile("my", {"A-PEAK": "error", "A-BALANCE-LOW": "warn"}))
    peak = next(f for f in report.findings if f.rule == "A-PEAK")
    low = next(f for f in report.findings if f.rule == "A-BALANCE-LOW")
    assert peak.severity == "error" and peak.message.endswith(", an error under the my profile")
    assert low.severity == "warn" and low.message.endswith(", a warning under the my profile")


def test_a_profile_leaving_an_audio_rule_alone_or_lowering_it_names_no_profile():
    report = lint_piece(_short(), Profile("my", {"A-TAIL": "metric", "A-PEAK": "metric"}))
    assert not [f for f in report.findings if f.rule.startswith("A-") and "profile" in f.message]


def test_lint_piece_skips_the_audio_of_a_score_it_cannot_play():
    s = Score()
    s.part("alto").add(melody("c4:w"))
    assert lint_piece(s).findings == []


def test_lint_piece_on_a_part_with_no_notes():
    s = Score()
    s.part("alto", Theremin())
    assert not lint_piece(s).errors


def _pitches(line):
    return [repr(pitch) for _, _, pitch in line]


def test_lines_of_a_stack_run_top_to_bottom():
    s = Score()
    s.part("alto").add(melody("<c4 e4 g4>:h <d4 f4 a4>:h"))
    found = lines(s)
    assert [_pitches(line) for line in found] == [["G4", "A4"], ["E4", "F4"], ["C4", "D4"]]
    half = Fraction(1, 2)
    assert found[0] == [(Fraction(0), half, Pitch("G4")), (half, Fraction(1), Pitch("A4"))]


def test_a_stack_going_from_three_to_two_leaves_the_missing_line_as_a_rest():
    s = Score()
    s.part("alto").add(melody("<c4 e4 g4>:q <e4 g4>:q <c4 e4>:q <c4 e4 g4>:q"))
    top, middle, bottom = lines(s)
    q = Fraction(1, 4)
    assert top == [(0 * q, q, Pitch("G4")), (q, 2 * q, Pitch("G4")), (3 * q, 4 * q, Pitch("G4"))]
    assert middle == [(0 * q, q, Pitch("E4")), (q, 2 * q, Pitch("E4")), (2 * q, 3 * q, Pitch("E4")), (3 * q, 4 * q, Pitch("E4"))]
    assert bottom == [(0 * q, q, Pitch("C4")), (2 * q, 3 * q, Pitch("C4")), (3 * q, 4 * q, Pitch("C4"))]


def test_a_note_before_a_stack_begins_on_the_line_it_leads_to():
    s = Score()
    s.part("alto").add(melody("c4:q <c4 e4 g4>:q g4:q"))
    assert [_pitches(line) for line in lines(s)] == [["G4", "G4"], ["E4"], ["C4", "C4"]]


def test_lines_order_voices_and_parts_by_mean_pitch_and_name_them():
    s = Score()
    s.part("tenor").add(melody("c4:w"))
    s.part("soprano").add(melody("c5:w"))
    s.part("alto").add(melody("g4:w")).add(melody("e4:w"), voice=1, at=1)
    found = lines(s)
    assert [_pitches(line) for line in found] == [["C5"], ["G4"], ["E4"], ["C4"]]
    assert [(line.part, line.voice) for line in found] == [("soprano", 0), ("alto", 0), ("alto", 1), ("tenor", 0)]


def test_a_rest_stays_a_gap_and_a_tie_joins_in_a_line():
    s = Score()
    s.part("alto").add(melody("c4:q r:q d4:q~ d4:q"))
    q = Fraction(1, 4)
    assert lines(s) == [[(0 * q, q, Pitch("C4")), (2 * q, 4 * q, Pitch("D4"))]]


def test_lines_of_a_thin_score():
    assert lines(Score()) == []
    s = Score()
    s.part("empty")
    s.part("rests").add(melody("R"))
    assert lines(s) == []
