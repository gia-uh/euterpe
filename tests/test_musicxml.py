import xml.etree.ElementTree as ET
from fractions import Fraction

import pytest
import verovio

from euterpe import Key, Meter, Score, drums, melody
from euterpe.instruments import Harp, Kit
from euterpe.pitch import Pitch
from euterpe.score import Line, Note, Rest
from euterpe.score.musicxml import musicxml_bytes


def _root(score: Score, **options) -> ET.Element:
    return ET.fromstring(musicxml_bytes(score, **options))


def _score(text: str = "c4:q d4 e4 f4", **options) -> Score:
    s = Score(**options)
    s.part("a").add(melody(text))
    return s


def _measures(root: ET.Element, part: int = 0) -> list[ET.Element]:
    return root.findall("part")[part].findall("measure")


def _notes(element: ET.Element) -> list[ET.Element]:
    return element.findall(".//note")


def _engraved(data: bytes) -> str:
    toolkit = verovio.toolkit()
    toolkit.setOptions({"xmlIdSeed": 1})
    assert toolkit.loadData(data.decode()) is True
    return toolkit.renderToSVG(1)


def _line(*events) -> Line:
    return Line([list(events)])


def _every_feature() -> Score:
    s = Score(key=Key("D major"), meter=Meter("4/4"), tempo=96, pickup=Fraction(1, 4), title="All of it")
    s.change(3, key=Key("F major"), meter=Meter("6/8"), tempo=60)
    s.ramp(4, 1, 40)
    s.section("A", 2, 3, repeat=3)
    s.section("B", 4, 5)
    tune = s.part("tune", Harp())
    tune.add(melody("a4:q | mf f#4:e' g4> a4_ gb4 < 3[c5:e d5 e5] ( f5:q | g5:q.~ g5:q. ) | f! a4:h. | b4:q. <c4 e4 g4>:q."))
    tune.hairpin((5, 1), (5, 2), ">")
    s.part("bass", clef="bass").add(melody("R | c3:w | R | R | c3:h."))
    s.part("kit", Kit()).add(drums({"kick": "x...", "hihat": "XgoX"}, step="q"), at=2)
    return s


def test_it_is_partwise_4_0_with_the_standard_doctype():
    data = musicxml_bytes(_score(title="Song"))
    assert b'<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN"' in data
    root = ET.fromstring(data)
    assert (root.tag, root.get("version")) == ("score-partwise", "4.0")
    assert root.findtext("work/work-title") == "Song"


def test_each_part_has_a_score_part_named_after_it():
    s = _score()
    s.part("b").add(melody("c3:w"))
    root = _root(s)
    assert [p.findtext("part-name") for p in root.findall("part-list/score-part")] == ["a", "b"]
    assert [p.get("id") for p in root.findall("part-list/score-part")] == [p.get("id") for p in root.findall("part")]


def test_the_key_writes_its_signature_and_mode():
    root = _root(_score(key=Key("D major")))
    assert root.findtext(".//key/fifths") == "2"
    assert root.findtext(".//key/mode") == "major"
    assert _root(_score(key=Key("D", "dorian"))).findtext(".//key/mode") == "dorian"
    assert _root(_score(key=Key("F major"))).findtext(".//key/fifths") == "-1"


def test_the_time_writes_beats_and_beat_type():
    root = _root(_score("c4:e d e f g a", meter=Meter("6/8")))
    assert (root.findtext(".//time/beats"), root.findtext(".//time/beat-type")) == ("6", "8")


def test_uneven_groups_write_in_the_beats():
    root = _root(_score("c4:e d e f g a b", meter=Meter("7/8", groups=(2, 2, 3))))
    assert root.findtext(".//time/beats") == "2+2+3"
    assert root.findtext(".//time/beat-type") == "8"


def test_divisions_is_the_least_common_multiple_of_the_denominators():
    assert _root(_score("c4:w")).findtext(".//divisions") == "1"
    assert _root(_score("c4:q d4 e4 f4:e g4")).findtext(".//divisions") == "2"
    assert _root(_score("c4:q d4 e4 3[f4:e g4 a4]")).findtext(".//divisions") == "3"
    root = _root(_score("c4:s d4 e4 f4 g4:q 3[f4:e g4 a4] c4:q"))
    assert root.findtext(".//divisions") == "12"
    assert [n.findtext("duration") for n in _notes(root)][:7] == ["3", "3", "3", "3", "12", "4", "4"]


def test_spelled_pitches_keep_their_letter():
    gb, fs = _notes(_root(_score("gb4:h f#4")))
    assert (gb.findtext("pitch/step"), gb.findtext("pitch/alter"), gb.findtext("pitch/octave")) == ("G", "-1", "4")
    assert (fs.findtext("pitch/step"), fs.findtext("pitch/alter"), fs.findtext("pitch/octave")) == ("F", "1", "4")


def test_a_natural_note_writes_no_alter():
    assert _notes(_root(_score("c4:w")))[0].find("pitch/alter") is None


def test_an_accidental_is_written_only_against_the_key_and_the_bar():
    def marks(text, key):
        return [n.findtext("accidental") for n in _notes(_root(_score(text, key=Key(key))))]

    assert marks("f#4:q g4 f#4 f4", "C major") == ["sharp", None, None, "natural"]
    assert marks("f#4:q f4 f#4 g4", "G major") == [None, "natural", "sharp", None]
    assert marks("bb4:q eb4 b4 a4", "F major") == [None, "flat", "natural", None]
    assert marks("f##4:h fb4", "C major") == ["double-sharp", "flat"]
    assert marks("f#4:w | f#4", "C major") == ["sharp", "sharp"]


def test_a_tied_note_repeats_no_accidental():
    first, second = _notes(_root(_score("f#4:w~ | f#4")))
    assert first.findtext("accidental") == "sharp" and second.find("accidental") is None


def test_note_values_and_dots():
    notes = _notes(_root(_score("c4:q. d4:e e4:h")))
    assert [(n.findtext("type"), len(n.findall("dot"))) for n in notes] == [("quarter", 1), ("eighth", 0), ("half", 0)]
    assert [(n.findtext("type"), len(n.findall("dot"))) for n in _notes(_root(_score("c4:q.. d4:s e4:h")))] == [
        ("quarter", 2), ("16th", 0), ("half", 0)]


def test_a_written_tie_has_both_ends():
    first, second = _notes(_root(_score("c4:h~ c4")))
    assert [t.get("type") for t in first.findall("tie")] == ["start"]
    assert [t.get("type") for t in first.findall("notations/tied")] == ["start"]
    assert [t.get("type") for t in second.findall("tie")] == ["stop"]
    assert [t.get("type") for t in second.findall("notations/tied")] == ["stop"]


def test_a_tie_with_nothing_to_reach_writes_nothing():
    root = _root(_score("c4:h~ d4"))
    assert root.find(".//tie") is None and root.find(".//tied") is None
    assert _root(_score("c4:w~")).find(".//tie") is None


def test_a_stack_ties_only_the_pitches_that_go_on():
    notes = _notes(_root(_score("<c4 e4>:h~ <c4 g4>")))
    assert [[t.get("type") for t in n.findall("tie")] for n in notes] == [["start"], [], ["stop"], []]


def test_a_dotted_note_crossing_a_bar_comes_out_tied():
    root = _root(_score("c4:h. d4:h."))
    first, second = _measures(root)
    assert [(n.findtext("type"), len(n.findall("dot"))) for n in _notes(first)] == [("half", 1), ("quarter", 0)]
    assert [(n.findtext("pitch/step"), n.findtext("duration")) for n in _notes(first)] == [("C", "3"), ("D", "1")]
    tail = _notes(second)[0]
    assert (tail.findtext("pitch/step"), tail.findtext("duration"), tail.findtext("type")) == ("D", "2", "half")
    assert [t.get("type") for t in _notes(first)[1].findall("tie")] == ["start"]
    assert [t.get("type") for t in tail.findall("tie")] == ["stop"]


def test_a_value_no_note_can_write_splits_at_the_strongest_beat():
    five = Fraction(5, 8)
    s = Score()
    s.part("a").add(_line(Note(Pitch("C4"), five), Rest(Fraction(3, 8))))
    first, second, rest = _notes(_root(s))
    assert (first.findtext("type"), second.findtext("type")) == ("half", "eighth")
    assert first.find("tie").get("type") == "start" and second.find("tie").get("type") == "stop"
    assert rest.find("rest") is not None and rest.find("dot") is not None


def test_a_value_inside_a_beat_splits_greatest_first():
    s = Score()
    s.part("a").add(_line(Note(Pitch("C4"), Fraction(5, 32))))
    assert [n.findtext("type") for n in _notes(_root(s))][:2] == ["eighth", "32nd"]


def test_a_note_one_value_can_write_stays_whole_across_a_beat():
    notes = _notes(_root(_score("c4:q d4:h e4:q")))
    assert [n.findtext("type") for n in notes] == ["quarter", "half", "quarter"]
    assert not any(n.find("tie") is not None for n in notes)


def test_a_chord_marks_all_but_its_first_pitch():
    notes = _notes(_root(_score("<c4 e4 g4>:w")))
    assert [n.find("chord") is not None for n in notes] == [False, True, True]
    assert {n.findtext("duration") for n in notes} == {"4"}


def test_a_triplet_writes_its_ratio_and_bracket():
    notes = _notes(_root(_score("3[c4:e d4 e4] 3[f4 g4 a4] b4:h")))
    assert [n.findtext("type") for n in notes[:3]] == ["eighth"] * 3
    assert [n.findtext("time-modification/actual-notes") for n in notes[:3]] == ["3"] * 3
    assert [n.findtext("time-modification/normal-notes") for n in notes[:3]] == ["2"] * 3
    assert [[t.get("type") for t in n.findall("notations/tuplet")] for n in notes[:6]] == [
        ["start"], [], ["stop"], ["start"], [], ["stop"]]
    assert notes[6].find("time-modification") is None


def test_a_quintuplet_and_a_duplet_write_their_ratios():
    notes = _notes(_root(_score("5:4[c4:s d4 e4 f4 g4] 2:3[a4:e b4] r:q", meter=Meter("7/8"))))
    assert [(n.findtext("time-modification/actual-notes"), n.findtext("time-modification/normal-notes"),
             n.findtext("type")) for n in notes[:7]] == [("5", "4", "16th")] * 5 + [("2", "3", "eighth")] * 2


def test_a_note_in_no_written_tuplet_still_writes_its_ratio():
    s = Score()
    s.part("a").add(_line(*[Note(Pitch("C4"), Fraction(1, 12))] * 3, Rest(Fraction(3, 4))))
    first = _notes(_root(s))[0]
    assert (first.findtext("time-modification/actual-notes"), first.findtext("time-modification/normal-notes")) == ("3", "2")
    assert first.findtext("type") == "eighth"


def test_a_slur_has_both_ends():
    notes = _notes(_root(_score("( c4:q d4 e4 ) f4")))
    assert [[t.get("type") for t in n.findall("notations/slur")] for n in notes] == [["start"], [], ["stop"], []]


def test_a_slur_on_a_split_note_ends_on_its_last_piece():
    notes = _notes(_root(_score("( c4:h. d4:h. )")))
    assert [[t.get("type") for t in n.findall("notations/slur")] for n in notes] == [["start"], [], ["stop"], []]
    assert notes[3].find("rest") is not None


def test_articulations_are_written():
    notes = _notes(_root(_score("c4:q' d4> e4_ f4")))
    assert [[a.tag for a in n.findall("notations/articulations/*")] for n in notes] == [["staccato"], ["accent"], ["tenuto"], []]


def test_a_dynamic_and_a_hairpin_are_directions():
    root = _root(_score("mf c4:q < d4 e4 f! f4"))
    assert [d.tag for d in root.findall(".//direction/direction-type/dynamics/*")] == ["mf", "f"]
    assert sorted(w.get("type") for w in root.findall(".//wedge")) == ["crescendo", "stop"]
    assert [w.get("type") for w in _root(_score("c4:q > d4 e4 f4")).findall(".//wedge")] == ["diminuendo", "stop"]


def test_a_hairpin_stops_before_the_next_starts_and_before_its_dynamic():
    measure = _measures(_root(_score("c4:q < d4 > e4 f! f4")))[0]
    marks = [d.find("direction-type/*") for d in measure.findall("direction")]
    assert [(m.tag, m.get("type")) for m in marks if m.tag in ("wedge", "dynamics")] == [
        ("wedge", "crescendo"), ("wedge", "stop"), ("wedge", "diminuendo"), ("wedge", "stop"), ("dynamics", None)]


def test_a_mark_between_notes_writes_its_offset():
    s = _score("c4:w")
    s.part("a").dynamic(1, 3, "p")
    direction = next(d for d in _root(s).findall(".//direction") if d.find("direction-type/dynamics") is not None)
    assert direction.findtext("offset") == "2"


def test_marks_after_the_music_do_not_invent_bars():
    s = _score("c4:w")
    s.part("a").dynamic(9, 1, "p")
    s.part("a").hairpin((1, 1), (9, 1), "<")
    root = _root(s)
    assert len(_measures(root)) == 1
    assert [w.get("type") for w in root.findall(".//wedge")] == ["crescendo", "stop"]
    assert root.find(".//dynamics") is None


def test_overlapping_hairpins_take_different_numbers():
    s = _score("c4:w")
    s.part("a").hairpin((1, 1), (1, 4), "<").hairpin((1, 2), (1, 3), ">")
    numbers = {w.get("type"): w.get("number") for w in _root(s).findall(".//wedge") if w.get("type") != "stop"}
    assert numbers["crescendo"] != numbers["diminuendo"]


def test_tempo_writes_sound_and_metronome_in_the_meters_beat():
    root = _root(_score(tempo=96))
    assert root.find(".//direction/sound").get("tempo") == "96"
    assert (root.findtext(".//metronome/beat-unit"), root.findtext(".//metronome/per-minute")) == ("quarter", "96")
    assert root.find(".//metronome/beat-unit-dot") is None


def test_compound_time_at_60_is_a_dotted_quarter():
    root = _root(_score("c4:h.", meter=Meter("6/8"), tempo=60))
    assert root.findtext(".//metronome/beat-unit") == "quarter"
    assert root.find(".//metronome/beat-unit-dot") is not None
    assert root.findtext(".//metronome/per-minute") == "60"
    assert root.find(".//direction/sound").get("tempo") == "90"


def test_cut_time_counts_half_notes():
    root = _root(_score("c4:w", meter=Meter("2/2"), tempo=60))
    assert root.findtext(".//metronome/beat-unit") == "half"
    assert root.find(".//direction/sound").get("tempo") == "120"


def test_a_beat_no_note_writes_counts_the_denominator():
    root = _root(_score("c4:q d4:q e4:e", meter=Meter("5/8", groups=(5,)), tempo=60))
    assert (root.findtext(".//metronome/beat-unit"), root.findtext(".//metronome/per-minute")) == ("eighth", "300")
    assert root.find(".//direction/sound").get("tempo") == "150"


def test_changes_write_in_their_bar_and_only_there():
    s = _score("c4:w | c4 | c4:h. | c4")
    s.change(2, key=Key("G major"))
    s.change(3, meter=Meter("3/4"))
    s.change(4, tempo=90)
    measures = _measures(_root(s))
    assert [m.findtext("attributes/key/fifths") for m in measures] == ["0", "1", None, None]
    assert [m.findtext("attributes/time/beats") for m in measures] == ["4", None, "3", None]
    assert [m.findtext("attributes/divisions") for m in measures] == ["1", None, None, None]
    assert [m.find("direction/sound") is not None for m in measures] == [True, False, False, True]


def test_a_change_to_the_same_key_writes_nothing():
    s = _score("c4:w | c4")
    s.change(2, key=Key("C major"))
    assert _measures(_root(s))[1].find("attributes") is None


def test_a_ramp_writes_words_over_its_bars():
    s = _score("c4:w | c4 | c4 | c4", tempo=120)
    s.ramp(2, 2, 60)
    measures = _measures(_root(s))
    assert measures[1].findtext("direction/direction-type/words") == "rit."
    assert [d.get("type") for d in measures[1].findall("direction/direction-type/dashes")] == ["start"]
    assert [d.get("type") for d in measures[2].findall("direction/direction-type/dashes")] == ["stop"]
    assert measures[2].find(".//sound").get("tempo") == "90"
    assert measures[3].findtext(".//metronome/per-minute") == "60"


def test_a_rising_ramp_is_an_accelerando():
    s = _score("c4:w | c4", tempo=60)
    s.ramp(1, 1, 120)
    assert _root(s).findtext(".//words") == "accel."


def test_tempo_and_sections_go_on_the_first_part_only():
    s = _score("c4:w")
    s.part("b").add(melody("c3:w"))
    s.section("A", 1, 1)
    root = _root(s)
    assert _measures(root, 0)[0].findtext("direction/direction-type/rehearsal") == "A"
    assert _measures(root, 1)[0].find("direction") is None


def test_a_repeat_writes_forward_and_backward_barlines_in_every_part():
    s = _score("c4:w | c4 | c4")
    s.part("b").add(melody("c3:w | c3 | c3"))
    s.section("A", 2, 3, repeat=2)
    for part in (0, 1):
        measures = _measures(_root(s), part)
        forward, backward = measures[1].find("barline"), measures[2].find("barline")
        assert (forward.get("location"), forward.find("repeat").get("direction")) == ("left", "forward")
        assert (backward.get("location"), backward.find("repeat").get("direction")) == ("right", "backward")
        assert backward.find("repeat").get("times") is None


def test_a_third_pass_writes_times():
    s = _score("c4:w | c4")
    s.section("A", 1, 2, repeat=3)
    assert _measures(_root(s))[1].find("barline/repeat").get("times") == "3"


def test_a_section_played_once_has_no_repeat():
    s = _score("c4:w | c4")
    s.section("A", 1, 2)
    assert _root(s).find(".//barline") is None


def test_a_repeat_past_the_last_bar_closes_on_it():
    s = _score("c4:w | c4")
    s.section("A", 1, 5, repeat=2)
    assert _measures(_root(s))[1].find("barline/repeat").get("direction") == "backward"


def test_a_short_part_is_padded_with_rests_filling_each_measure():
    s = _score("c4:w | d4 | e4")
    s.part("b").add(melody("c3:w"))
    measures = _measures(_root(s), 1)
    assert len(measures) == 3
    for measure in measures[1:]:
        note, = _notes(measure)
        assert note.find("rest").get("measure") == "yes"
        assert note.findtext("duration") == "4"
        assert note.find("type") is None


def test_a_part_with_no_notes_still_has_every_measure():
    s = _score("c4:w | d4")
    s.part("b")
    assert len(_measures(_root(s), 1)) == 2
    assert _root(s).find("part-list/score-part[2]/part-name").text == "b"


def test_a_score_with_only_an_empty_part_has_one_measure():
    s = Score()
    s.part("a")
    assert len(_measures(_root(s))) == 1


def test_a_part_starting_later_is_padded_before_it():
    s = _score("c4:w | d4")
    s.part("b").add(melody("c3:w"), at=2)
    first, second = _measures(_root(s), 1)
    assert _notes(first)[0].find("rest") is not None and _notes(second)[0].find("pitch") is not None


def test_a_short_bar_is_filled_with_rests():
    notes = _notes(_root(_score("c4:q")))
    assert [(n.find("rest") is not None, n.findtext("duration")) for n in notes][0] == (False, "1")
    assert sum(int(n.findtext("duration")) for n in notes) == 4
    assert all(n.find("rest") is not None for n in notes[1:])


def test_a_bar_written_too_long_runs_into_the_next_as_a_second_layer():
    root = _root(_score("c4:w d4:q | e4:w"))
    first, second = _measures(root)
    assert [n.findtext("pitch/step") for n in _notes(second)] == ["D", "E"]
    assert second.findtext("backup/duration") == "1"
    assert all(n.findtext("voice") == "1" for n in _notes(second))
    _engraved(musicxml_bytes(_score("c4:w d4:q | e4:w")))


def test_a_tie_reaches_over_the_rests_that_fill_a_bar():
    notes = _notes(_root(_score("c4:q~ | c4:q r:h.")))
    pitched = [n for n in notes if n.find("pitch") is not None]
    assert [[t.get("type") for t in n.findall("tie")] for n in pitched] == [["start"], ["stop"]]


def test_no_parts_raises():
    with pytest.raises(ValueError, match="no parts"):
        Score().to_musicxml("x.musicxml")
    with pytest.raises(ValueError, match="no parts"):
        musicxml_bytes(Score())


def test_a_pickup_is_an_implicit_measure_one():
    s = Score(pickup=Fraction(1, 4))
    s.part("a").add(melody("g4:q | c5:w"))
    first, second = _measures(_root(s))
    assert (first.get("number"), first.get("implicit")) == ("1", "yes")
    assert (second.get("number"), second.get("implicit")) == ("2", None)
    assert [n.findtext("duration") for n in _notes(first)] == ["1"]


def test_a_padded_pickup_bar_fills_only_the_pickup():
    s = Score(pickup=Fraction(1, 4))
    s.part("a").add(melody("g4:q | c5:w"))
    s.part("b").add(melody("c3:w"), at=2)
    note, = _notes(_measures(_root(s), 1)[0])
    assert note.find("rest") is not None and note.find("rest").get("measure") is None
    assert (note.findtext("duration"), note.findtext("type")) == ("1", "quarter")


def test_a_pickup_no_one_value_can_write_pads_with_values_it_can():
    s = Score(pickup=Fraction(5, 16))
    s.part("a").add(_line(Note(Pitch("C4"), Fraction(5, 16))))
    s.part("b")
    rests = _notes(_measures(_root(s), 1)[0])
    assert [n.findtext("type") for n in rests] == ["16th", "quarter"]
    assert all(n.find("rest").get("measure") is None for n in rests)


def test_a_whole_bar_rest_stays_one_rest_in_a_bar_no_one_value_can_write():
    s = _score("c4:q d4:q e4:e | R", meter=Meter("5/8"))
    note, = _notes(_measures(_root(s))[1])
    assert note.find("rest").get("measure") == "yes" and note.find("type") is None


def test_a_note_after_a_pickup_splits_at_the_beats_of_the_bar_it_borrows_from():
    s = Score(pickup=Fraction(3, 8))
    s.part("a").add(_line(Note(Pitch("C4"), Fraction(5, 16))))
    written = [(n.findtext("type"), len(n.findall("dot"))) for n in _notes(_root(s)) if n.find("pitch") is not None]
    assert written == [("eighth", 0), ("eighth", 1)]


def test_voices_write_with_backup_and_a_voice_number():
    s = _score("c5:w")
    s.part("a").add(melody("c4:q d4 e4 f4"), voice=1, at=1)
    measure = _measures(_root(s))[0]
    assert [n.findtext("voice") for n in _notes(measure)] == ["1", "2", "2", "2", "2"]
    assert measure.findtext("backup/duration") == "4"


def test_an_empty_second_voice_writes_nothing_in_that_bar():
    s = _score("c5:w | d5")
    s.part("a").add(melody("c4:w"), voice=1, at=1)
    assert [n.findtext("voice") for n in _notes(_measures(_root(s))[1])] == ["1"]


def test_a_kit_part_writes_unpitched_on_the_percussion_clef():
    s = Score()
    s.part("kit", Kit()).add(drums({"kick": "x...", "snare": "..x.", "hihat": "xxxx"}, step="q"))
    root = _root(s)
    assert root.findtext(".//clef/sign") == "percussion"
    assert root.find(".//note/pitch") is None
    struck = [n for n in _notes(root) if n.find("unpitched") is not None]
    assert len(struck) == 6
    assert {n.findtext("unpitched/display-step") + n.findtext("unpitched/display-octave") for n in struck} == {"F4", "C5", "G5"}
    assert {n.findtext("notehead") for n in struck} == {None, "x"}


def test_a_kit_part_names_its_drums_by_general_midi():
    s = Score()
    s.part("kit", Kit()).add(drums({"kick": "x...", "hihat": "x..."}, step="q"))
    root = _root(s)
    ids = {i.get("id"): i.findtext("instrument-name") for i in root.findall("part-list/score-part/score-instrument")}
    assert sorted(ids.values()) == ["hihat", "kick"]
    unpitched = {m.get("id"): m.findtext("midi-unpitched") for m in root.findall("part-list/score-part/midi-instrument")}
    assert {ids[key]: value for key, value in unpitched.items()} == {"kick": "37", "hihat": "43"}
    assert {m.findtext("midi-channel") for m in root.findall("part-list/score-part/midi-instrument")} == {"10"}
    assert {ids[n.find("instrument").get("id")] for n in _notes(root) if n.find("unpitched") is not None} == {"kick", "hihat"}


def test_a_hit_with_no_instrument_also_writes_percussion():
    s = Score()
    s.part("kit").add(drums({"kick": "x..."}, step="q"))
    assert _root(s).findtext(".//clef/sign") == "percussion"


def test_a_kit_with_nothing_written_has_the_percussion_clef():
    s = _score("c4:w")
    s.part("kit", Kit())
    assert _measures(_root(s), 1)[0].findtext("attributes/clef/sign") == "percussion"


def test_a_percussion_staff_takes_no_key_and_no_key_change():
    s = Score(key=Key("D major"))
    s.part("tune").add(melody("f#4:w | f#4"))
    s.part("kit", Kit()).add(drums({"kick": "x... | x..."}, step="q"))
    s.part("odd", clef="percussion").add(melody("f#4:w | f#4"))
    s.change(2, key=Key("F major"))
    root = _root(s)
    assert [m.findtext("attributes/key/fifths") for m in _measures(root, 0)] == ["2", "-1"]
    for part in (1, 2):
        assert [m.findtext("attributes/key/fifths") for m in _measures(root, part)] == ["0", None]
    assert _notes(_measures(root, 2)[0])[0].findtext("accidental") == "sharp"


def test_a_hits_grid_character_writes_its_mark():
    s = Score()
    s.part("kit", Kit()).add(drums({"hihat": "xXgo"}, step="q"))
    x, accent, ghost, opened = [n for n in _notes(_root(s)) if n.find("unpitched") is not None]
    assert x.find("notations") is None
    assert accent.find("notations/articulations/accent") is not None
    assert ghost.find("notehead").get("parentheses") == "yes"
    assert opened.find("notations/technical/open-string") is not None


def test_the_default_clef_follows_the_mean_pitch():
    clef = lambda text: _root(_score(text)).findtext(".//clef/sign")
    assert clef("c4:w") == "G"
    assert clef("b3:w") == "F"
    assert clef("c2:h c6") == "G"
    assert clef("c2:h c5") == "F"
    assert _root(_score("c4:w")).findtext(".//clef/line") == "2"
    assert _root(_score("c3:w")).findtext(".//clef/line") == "4"


def test_a_part_with_no_notes_is_on_the_treble_clef():
    s = Score()
    s.part("a")
    assert _root(s).findtext(".//clef/sign") == "G"


@pytest.mark.parametrize("name,sign,line", [("treble", "G", "2"), ("bass", "F", "4"), ("alto", "C", "3"), ("tenor", "C", "4")])
def test_clef_overrides_the_default(name, sign, line):
    s = Score()
    s.part("a", clef=name).add(melody("c6:w" if name == "bass" else "c2:w"))
    root = _root(s)
    assert (root.findtext(".//clef/sign"), root.findtext(".//clef/line")) == (sign, line)


def test_an_unknown_clef_names_itself():
    s = Score()
    s.part("a", clef="soprano").add(melody("c4:w"))
    with pytest.raises(ValueError, match="soprano"):
        musicxml_bytes(s)


def test_two_renders_are_byte_equal():
    assert musicxml_bytes(_every_feature()) == musicxml_bytes(_every_feature())
    s = _every_feature()
    assert musicxml_bytes(s) == musicxml_bytes(s)


def test_to_musicxml_writes_the_bytes_and_returns_the_path(tmp_path):
    s = _score()
    path = s.to_musicxml(tmp_path / "x.musicxml")
    assert path == tmp_path / "x.musicxml"
    assert path.read_bytes() == musicxml_bytes(s)
    assert s.to_musicxml(str(tmp_path / "y.musicxml")) == tmp_path / "y.musicxml"


def test_bars_writes_only_those_measures_keeping_their_numbers():
    measures = _measures(_root(_score("c4:w | d4 | e4 | f4"), bars=(2, 3)))
    assert [m.get("number") for m in measures] == ["2", "3"]
    assert [_notes(m)[0].findtext("pitch/step") for m in measures] == ["D", "E"]


def test_bars_starts_with_what_is_in_force():
    s = Score(key=Key("D major"), tempo=80)
    s.part("a", clef="bass").add(melody("c4:w | d4 | e4 | f4"))
    s.change(2, key=Key("G major"), meter=Meter("4/4"), tempo=70)
    first = _measures(_root(s, bars=(3, 4)))[0]
    assert first.findtext("attributes/key/fifths") == "1"
    assert first.findtext("attributes/time/beats") == "4"
    assert first.findtext("attributes/clef/sign") == "F"
    assert first.findtext("attributes/divisions") == "1"
    assert first.find("direction/sound").get("tempo") == "70"


def test_bars_divisions_and_clef_read_the_whole_score():
    s = _score("c4:w | c6:q d6 e6 3[f6:e g6 a6] | c2:w")
    assert _root(s, bars=(1, 1)).findtext(".//divisions") == _root(s).findtext(".//divisions")
    assert _root(s, bars=(3, 3)).findtext(".//clef/sign") == _root(s).findtext(".//clef/sign")


def test_bars_drops_a_tie_and_a_slur_cut_by_its_edge():
    s = _score("( c4:w~ | c4 | d4 ) | e4")
    first = _root(s, bars=(1, 1))
    assert first.find(".//tie") is None and first.find(".//slur") is None
    second = _root(s, bars=(2, 3))
    assert second.find(".//tie") is None and second.find(".//slur") is None


def test_bars_keeps_ties_and_slurs_inside_it():
    root = _root(_score("c4:w | ( d4:w~ | d4 ) | e4"), bars=(2, 3))
    assert sorted(t.get("type") for t in root.findall(".//tie")) == ["start", "stop"]
    assert sorted(t.get("type") for t in root.findall(".//slur")) == ["start", "stop"]


def test_bars_cuts_a_hairpin_to_its_edge():
    s = _score("c4:w | d4 | e4 | f4")
    s.part("a").hairpin((1, 1), (4, 1), "<")
    wedges = _root(s, bars=(2, 3)).findall(".//wedge")
    assert [w.get("type") for w in wedges] == ["crescendo", "stop"]


def test_bars_cuts_a_ramp_to_its_edge():
    s = _score("c4:w | d4 | e4 | f4", tempo=120)
    s.ramp(1, 4, 60)
    root = _root(s, bars=(2, 3))
    assert root.findtext(".//words") == "rit."
    assert [d.get("type") for d in root.findall(".//dashes")] == ["start", "stop"]


def test_bars_keeps_a_repeat_sign_only_inside_it():
    s = _score("c4:w | d4 | e4")
    s.section("A", 1, 3, repeat=2)
    assert _root(s, bars=(2, 2)).find(".//barline") is None
    assert _root(s, bars=(3, 3)).find(".//repeat").get("direction") == "backward"


@pytest.mark.parametrize("bars", [(0, 1), (2, 1), (1, 9), (9, 9)])
def test_bars_outside_the_score_raises(bars):
    with pytest.raises(ValueError, match="bars"):
        musicxml_bytes(_score("c4:w | d4"), bars=bars)


def test_bars_on_a_pickup_marks_only_the_short_bar_implicit():
    s = Score(pickup=Fraction(1, 4))
    s.part("a").add(melody("g4:q | c5:w | d5"))
    assert [m.get("implicit") for m in _measures(_root(s, bars=(2, 3)))] == [None, None]
    assert _measures(_root(s, bars=(1, 2)))[0].get("implicit") == "yes"


def _numerals(root: ET.Element) -> list[str]:
    return [d.findtext("direction-type/words") for d in root.findall(".//direction")
            if d.get("placement") == "below" and d.find("direction-type/words") is not None]


def test_numerals_write_each_change_below_the_staff():
    s = Score()
    s.part("a").add(melody("<c4 e4 g4>:h <c4 e4 g4> | <g3 b3 d4> <c4 e4 g4>"))
    assert _numerals(_root(s, numerals=True)) == ["I", "V", "I"]


def test_numerals_are_off_by_default():
    s = Score()
    s.part("a").add(melody("<c4 e4 g4>:w"))
    assert _numerals(_root(s)) == []


def test_numerals_go_on_the_last_part():
    s = Score()
    s.part("a").add(melody("<c4 e4 g4>:w"))
    s.part("b").add(melody("c3:w"))
    root = _root(s, numerals=True)
    assert _numerals(_measures(root, 0)[0]) == []
    assert _numerals(_measures(root, 1)[0]) == ["I"]


def test_numerals_sit_on_their_beat():
    s = Score()
    s.part("a").add(melody("<c4 e4 g4>:h. <g3 b3 d4>:q"))
    below = [d for d in _root(s, numerals=True).findall(".//direction") if d.get("placement") == "below"]
    assert below[1].findtext("direction-type/words") == "V"
    assert below[1].find("offset") is None


def test_numerals_in_a_range_start_with_the_one_in_force():
    s = Score()
    s.part("a").add(melody("<c4 e4 g4>:w | <c4 e4 g4> | <g3 b3 d4>"))
    assert _numerals(_root(s, bars=(2, 3), numerals=True)) == ["I", "V"]


def test_a_full_score_loads_in_verovio():
    data = musicxml_bytes(_every_feature())
    svg = _engraved(data)
    assert "<svg" in svg and "notehead" in svg


def test_the_engraving_keeps_a_written_accidental():
    toolkit = verovio.toolkit()
    assert toolkit.loadData(musicxml_bytes(_score("f#4:q g4 gb4 g4")).decode()) is True
    mei = toolkit.getMEI()
    assert 'accid="s"' in mei and 'accid="f"' in mei and 'accid="n"' in mei


def test_two_engravings_are_equal():
    data = musicxml_bytes(_every_feature())
    assert _engraved(data) == _engraved(data)
