from fractions import Fraction

import pytest

import euterpe
import euterpe.score
from euterpe import Chord, EqualTemperament, Interval, JustIntonation, Key, Meter, Pitch, Pythagorean, Score
from euterpe.instruments import Accent, Articulation, Harp, Kit, Tenuto
from euterpe.instruments import Note as PerformedNote
from euterpe.score import BarRest, Harmony, Hit, Line, Measure, Note, Numeral, Part, Placed, Rest, Tuplet

Q = Fraction(1, 4)
E = Fraction(1, 8)


def note(name, duration=Q, **kwargs):
    return Note(Pitch(name), duration, **kwargs)


def stack(names, duration=Q):
    return Note(tuple(Pitch(name) for name in names.split()), duration)


def line(*bars):
    return Line(bars)


def pitches(score, part=None):
    return [p.event.pitches for p in score.events(part) if isinstance(p.event, Note)]


# Bars, pickups and time


def test_bars_count_from_one():
    s = Score()
    assert s.bars == 0
    s.part("a").add(line([note("C4", 1)], [note("D4", 1)]))
    assert s.bars == 2
    assert s.bar_start(1) == 0
    assert s.bar_start(2) == 1
    with pytest.raises(ValueError, match="bar 0"):
        s.bar_start(0)


def test_a_pickup_is_the_short_first_bar():
    s = Score(pickup=E)
    assert s.bar_start(1) == 0
    assert s.bar_start(2) == E
    assert s.bar_start(3) == E + 1


def test_a_placed_pickup_note_counts_from_the_end_of_the_short_bar():
    s = Score(pickup=E)
    s.part("a").add(line([note("E5", E)], [note("A4", 1)]))
    first, second = s.events()
    assert first == Placed("a", 0, 1, Fraction(7, 8), Fraction(0), note("E5", E))
    assert second == Placed("a", 0, 2, Fraction(0), E, note("A4", 1))
    assert Meter("4/4").strength(first.in_bar) > Meter("4/4").strength(Fraction(3, 4))


def test_placed_offset_counts_from_the_start_of_bar_one():
    s = Score(meter=Meter("3/4"))
    s.part("a").add(line([note("C4"), note("D4"), note("E4")], [Rest(Q), note("F4", Q)]))
    placed = list(s.events())
    assert [p.offset for p in placed] == [0, Q, 2 * Q, 3 * Q, 4 * Q]
    assert [p.in_bar for p in placed] == [0, Q, 2 * Q, 0, Q]
    assert [p.bar for p in placed] == [1, 1, 1, 2, 2]


def test_a_pickup_cannot_fill_or_pass_the_bar():
    for pickup in (Fraction(1), Fraction(5, 4), Fraction(-1, 8)):
        with pytest.raises(ValueError, match="pickup"):
            Score(pickup=pickup)


def test_a_change_of_the_first_meter_keeps_the_pickup_inside_the_bar():
    s = Score(pickup=Fraction(3, 4))
    with pytest.raises(ValueError, match="pickup"):
        s.change(1, meter=Meter("2/4"))
    s.change(1, meter=Meter("7/8"))
    assert s.bar_start(2) == Fraction(3, 4)
    s.part("a").add(line([note("C4", Fraction(3, 4))]))
    assert next(s.events()).in_bar == Fraction(1, 8)


def test_a_note_keeps_its_articulations_as_a_tuple():
    assert note("C4", articulations=[Accent()]).articulations == (Accent(),)


def test_a_note_needs_a_pitch():
    with pytest.raises(ValueError, match="pitch"):
        Note((), Q)


def test_written_time_refuses_floats():
    with pytest.raises(ValueError, match="Fraction"):
        Note(Pitch("C4"), 1 / 12)
    with pytest.raises(ValueError, match="Fraction"):
        Score(pickup=0.125)
    with pytest.raises(ValueError, match="above 0"):
        Rest(0)


def test_a_tuplet_note_keeps_its_sounding_duration_and_sums_exactly():
    triplet = Tuplet(3, 2)
    third = note("C5", Fraction(1, 12), tuplet=triplet)
    assert third.duration == Fraction(1, 12)
    assert third.tuplet == Tuplet(3, 2)
    s = Score()
    s.part("a").add(line([third, third, third, note("D5", Fraction(3, 4))]))
    assert [p.in_bar for p in s.events()] == [0, Fraction(1, 12), Fraction(1, 6), Fraction(1, 4)]
    assert Rest(Fraction(1, 12), tuplet=triplet).tuplet == triplet


def test_events_filter_by_part_and_order_by_offset_then_voice():
    s = Score()
    s.part("a").add(line([note("C4"), note("D4")])).add(line([note("E4", 2 * Q)]), voice=1, at=1)
    s.part("b").add(line([note("G2", 2 * Q)]))
    assert [(p.part, p.voice, p.offset) for p in s.events()] == [("a", 0, 0), ("a", 1, 0), ("a", 0, Q), ("b", 0, 0)]
    assert [p.part for p in s.events("b")] == ["b"]
    with pytest.raises(ValueError, match="'z'"):
        s.events("z")


# Changes


def test_change_holds_from_its_bar_on():
    s = Score(key=Key("C major"), meter=Meter("4/4"), tempo=100)
    s.change(3, key=Key("G major"), meter=Meter("6/8"), tempo=80)
    assert s.key_at(2) == Key("C major")
    assert s.key_at(3) == s.key_at(9) == Key("G major")
    assert (s.meter_at(2), s.meter_at(3)) == (Meter("4/4"), Meter("6/8"))
    assert (s.tempo_at(2), s.tempo_at(3)) == (100, 80)
    assert s.bar_start(4) == 2 + Fraction(3, 4)


def test_two_changes_on_one_bar_add_up():
    s = Score()
    s.change(2, key=Key("F major"))
    s.change(2, tempo=60)
    assert (s.key_at(2), s.tempo_at(2)) == (Key("F major"), 60)


def test_a_ramp_moves_the_tempo_linearly_in_written_time_and_stays_at_its_end():
    s = Score(tempo=120)
    s.ramp(2, 2, 60)
    assert [s.tempo_at(bar) for bar in (1, 2, 3, 4, 9)] == [120, 120, 90, 60, 60]
    s.change(6, tempo=100)
    assert s.tempo_at(6) == 100


def test_a_ramp_is_linear_in_written_time_across_a_meter_change():
    s = Score(tempo=120)
    s.change(2, meter=Meter("2/4"))
    s.ramp(1, 2, 60)
    assert s.tempo_at(2) == 80


@pytest.mark.parametrize("tempo", [0, -10])
def test_no_tempo_at_or_below_zero_is_accepted(tempo):
    with pytest.raises(ValueError, match="above 0"):
        Score().ramp(1, 2, tempo)
    with pytest.raises(ValueError, match="above 0"):
        Score(tempo=tempo)
    with pytest.raises(ValueError, match="above 0"):
        Score().change(2, tempo=tempo)


def test_a_ramp_cannot_overlap_a_ramp_or_a_tempo_change():
    s = Score()
    s.ramp(3, 4, 60)
    with pytest.raises(ValueError, match="ramp"):
        s.ramp(5, 4, 90)
    with pytest.raises(ValueError, match="ramp"):
        s.change(4, tempo=90)
    s.change(4, key=Key("G major"))
    s.change(3, tempo=100)
    s.change(7, tempo=100)
    assert s.tempo_at(3) == 100
    with pytest.raises(ValueError, match="ramp"):
        Score().ramp(1, 0, 60)
    t = Score()
    t.change(4, tempo=90)
    with pytest.raises(ValueError, match="ramp"):
        t.ramp(3, 4, 60)


# Parts


def test_two_calls_with_a_name_return_one_part():
    s = Score()
    assert s.part("a") is s.part("a")
    assert list(s.parts) == ["a"]
    assert isinstance(s.part("a"), Part)


def test_part_keeps_its_settings_and_refuses_new_ones():
    harp = Harp()
    s = Score()
    part = s.part("a", harp, gain=0.5, clef="bass")
    assert (part.name, part.instrument, part.gain, part.clef) == ("a", harp, 0.5, "bass")
    assert s.part("a") is part
    assert s.part("a", harp, gain=0.5, clef="bass") is part
    with pytest.raises(ValueError, match="'a'"):
        s.part("a", Harp())
    with pytest.raises(ValueError, match="'a'"):
        s.part("a", gain=0.7)


def test_add_appends_per_voice_and_at_places():
    s = Score()
    part = s.part("a")
    assert part.add(line([note("C4", 1)])) is part
    part.add(line([note("D4", 1)]))
    part.add(line([note("A3", 1)]), voice=1)
    part.add(line([note("E4", 1)]), at=5)
    part.add(line([note("F4", 1)]))
    assert part.bars == 6
    assert [m.number for m in part.measures] == [1, 2, 3, 4, 5, 6]
    assert all(isinstance(m, Measure) and len(m.voices) == 2 for m in part.measures)
    assert [p.bar for p in s.events() if p.voice == 0] == [1, 2, 5, 6]
    assert [p.bar for p in s.events() if p.voice == 1] == [1]
    assert part.measures[2].voices == [[], []]


def test_adding_over_written_bars_of_a_voice_raises_and_leaves_the_part_alone():
    s = Score()
    part = s.part("a").add(line([note("C4", 1)], [note("D4", 1)]))
    with pytest.raises(ValueError, match="'a'.*voice 0.*bar 2"):
        part.add(line([note("E4", 1)]), at=2)
    assert part.bars == 2
    part.add(line([note("E4", 1)]), voice=1, at=2)


@pytest.mark.parametrize("kwargs", [{"at": 0}, {"voice": -1}])
def test_add_refuses_a_bar_or_voice_below_the_first(kwargs):
    with pytest.raises(ValueError, match="'a'"):
        Score().part("a").add(line([note("C4", 1)]), **kwargs)


def test_part_dynamic_beat_counts_from_one_in_the_meters_beats():
    s = Score(meter=Meter("6/8"))
    part = s.part("a")
    part.dynamic(1, 2, "p")
    assert part.dynamics[0].in_bar == Fraction(3, 8)
    assert part.dynamics[0].offset == Fraction(3, 8)
    assert part.dynamics[0].mark == "p"
    assert part.dynamics[0].bar == 1


def test_part_dynamic_reads_unequal_groups_and_fractions_of_a_beat():
    s = Score(meter=Meter("7/8", groups=(2, 2, 3)))
    part = s.part("a").dynamic(1, 3, "f").dynamic(1, Fraction(3, 2), "p")
    assert [d.in_bar for d in part.dynamics] == [Fraction(1, 8), Fraction(4, 8)]
    with pytest.raises(ValueError, match="beat 4"):
        part.dynamic(1, 4, "p")
    with pytest.raises(ValueError, match="beat 0"):
        part.dynamic(1, 0, "p")


def test_part_dynamic_follows_a_meter_changed_later():
    s = Score()
    part = s.part("a").dynamic(2, 2, "p")
    s.change(2, meter=Meter("6/8"))
    assert part.dynamics[0].in_bar == Fraction(3, 8)


def test_a_dynamic_in_a_pickup_counts_from_the_end_of_the_short_bar():
    s = Score(pickup=Q)
    part = s.part("a").dynamic(1, 4, "p").dynamic(2, 1, "f")
    assert (part.dynamics[0].in_bar, part.dynamics[0].offset) == (Fraction(3, 4), 0)
    assert (part.dynamics[1].in_bar, part.dynamics[1].offset) == (0, Q)
    with pytest.raises(ValueError, match="before the pickup"):
        part.dynamic(1, 1, "p")


def test_part_hairpin_places_both_ends():
    s = Score()
    part = s.part("a").hairpin((1, 1), (2, 3), "<")
    pin = part.hairpins[0]
    assert (pin.start, pin.end, pin.kind) == (0, Fraction(3, 2), "<")
    with pytest.raises(ValueError, match="kind"):
        part.hairpin((1, 1), (2, 1), "v")
    with pytest.raises(ValueError, match="after"):
        part.hairpin((2, 1), (1, 1), ">")


def test_hairpins_read_in_order_of_their_start():
    part = Score().part("a").hairpin((2, 1), (2, 3), ">").hairpin((1, 1), (1, 3), "<")
    assert [pin.kind for pin in part.hairpins] == ["<", ">"]
    assert [pin.start for pin in part.hairpins] == [0, 1]


# Numerals and whole-bar rests


def test_a_line_keeps_numerals_until_add_and_resolves_them_in_the_bars_key():
    numeral = Numeral("V", Fraction(1))
    chords = line([Numeral("I", Fraction(1))], [numeral], [Numeral("I", Fraction(1))])
    assert chords.bars[1] == (numeral,)
    s = Score(key=Key("D major"))
    s.change(3, key=Key("G major"))
    s.part("a").add(chords)
    assert pitches(s) == [Chord("D").pitches(), Chord("A").pitches(), Chord("G").pitches()]


def test_a_numeral_follows_a_key_changed_after_the_add():
    s = Score(key=Key("D major"))
    s.part("a").add(line([Numeral("I", Fraction(1))], [Numeral("I", Fraction(1))]))
    s.change(2, key=Key("G major"))
    assert pitches(s) == [Chord("D").pitches(), Chord("G").pitches()]


def test_a_numeral_that_cannot_be_read_raises_at_add_naming_part_and_bar():
    part = Score().part("a")
    with pytest.raises(ValueError, match="'a'.*bar 1.*H9"):
        part.add(line([Numeral("H9", Q)]))
    assert part.bars == 0


def test_a_numeral_takes_a_realizer_with_the_previous_notes():
    def broken(chord, previous):
        seen.append(previous)
        return [Note(p, E) for p in chord.pitches()[:2]]

    seen = []
    s = Score()
    s.part("a").add(line([note("B3", Q), Numeral("I", Q, broken), Numeral("V", Q, broken)]))
    assert pitches(s)[1:] == [(Pitch("C4"),), (Pitch("E4"),), (Pitch("G4"),), (Pitch("B4"),)]
    # one call at add to check the line, one at this read
    assert seen == [(Pitch("B3"),), (Pitch("E4"),)] * 2


def test_line_transpose_refuses_numerals():
    with pytest.raises(ValueError, match=r"numerals move with the key: use s\.transpose"):
        line([Numeral("I", Q)]).transpose(Interval("M2"))


def test_a_whole_bar_rest_is_filled_by_the_meter_at_each_bar():
    s = Score(meter=Meter("3/4"))
    s.change(2, meter=Meter("6/8"))
    s.change(3, meter=Meter("2/2"))
    s.part("a").add(line([BarRest()], [BarRest()], [BarRest()]))
    assert [p.event for p in s.events()] == [Rest(Fraction(3, 4)), Rest(Fraction(3, 4)), Rest(Fraction(1))]


def test_a_whole_bar_rest_in_a_pickup_fills_the_short_bar():
    s = Score(pickup=E)
    s.part("a").add(line([BarRest()], [BarRest()]))
    assert [p.event.duration for p in s.events()] == [E, 1]
    assert [p.in_bar for p in s.events()] == [Fraction(7, 8), 0]


def test_line_duration_needs_a_meter_for_a_whole_bar_rest():
    with_rest = line([note("C4", Q), BarRest()])
    with pytest.raises(ValueError, match="meter"):
        with_rest.duration
    assert Line(with_rest.bars, meter=Meter("3/4")).duration == Q + Fraction(3, 4)


# Line


def test_line_duration_bars_add_and_repeat():
    a = line([note("C4", Q), Numeral("I", Q)], [Rest(E)])
    b = line([note("D4", 1)])
    assert a.duration == Fraction(5, 8)
    assert a.bars == ((note("C4", Q), Numeral("I", Q)), (Rest(E),))
    assert (a + b).bars == a.bars + b.bars
    assert (a * 2).bars == a.bars * 2
    assert (2 * b).duration == 2
    assert (a + b).duration == Fraction(13, 8)


def test_line_keeps_a_known_meter_through_add_and_repeat():
    known = Line(((BarRest(),),), meter=Meter("3/4"))
    plain = line([BarRest()])
    assert (known + plain).duration == (plain + known).duration == (known * 2).duration == Fraction(3, 2)


def test_line_transpose_moves_notes_spelled_by_the_interval_and_not_hits():
    hit = Hit("kick", Q, accent="x")
    moved = line([note("F#4", Q, tie=True), stack("C4 E4", E), Rest(E), hit]).transpose(Interval("m2"))
    assert moved.bars[0] == (note("G4", Q, tie=True), stack("Db4 F4", E), Rest(E), hit)


def test_line_transpose_names_a_note_past_a_double_accidental_and_its_bar():
    with pytest.raises(ValueError, match=r"bar 2.*F##4"):
        line([note("C4")], [note("F##4")]).transpose(Interval("A1"))


def test_line_joining_two_meters_knows_no_single_bar():
    three, four = Line(((BarRest(),),), Meter("3/4")), Line(((BarRest(),),), Meter("4/4"))
    assert (three + four).meter is None
    with pytest.raises(ValueError, match="meter"):
        (three + four).duration
    assert (three + three).meter == Meter("3/4")


# Hits


def test_a_hit_on_an_instrument_that_is_not_a_kit_raises_naming_the_part():
    with pytest.raises(ValueError, match="'lead'"):
        Score().part("lead", Harp()).add(line([Hit("kick", Q)]))


def test_a_hit_on_a_kit_or_no_instrument_is_allowed():
    s = Score()
    s.part("drums", Kit()).add(line([Hit("kick", Q)]))
    s.part("written").add(line([Hit("snare", Q)]))
    assert [p.event.drum for p in s.events()] == ["kick", "snare"]


# Sections


def test_sections_label_bars_and_keep_their_repeats():
    s = Score()
    s.section("A", 1, 4, repeat=2)
    s.section("B", 5, 8)
    assert [(x.name, x.first, x.last, x.repeat) for x in s.sections] == [("A", 1, 4, 2), ("B", 5, 8, 1)]


@pytest.mark.parametrize("first, last", [(3, 6), (1, 2), (2, 3), (1, 9), (4, 4), (0, 2)])
def test_sections_overlapping_or_nested_raise(first, last):
    s = Score()
    s.section("A", 1, 4)
    with pytest.raises(ValueError, match="section"):
        s.section("B", first, last)
    assert len(s.sections) == 1


@pytest.mark.parametrize("first, last, repeat", [(4, 2, 1), (0, 2, 1), (1, 2, 0)])
def test_a_section_with_no_bars_or_no_pass_raises(first, last, repeat):
    with pytest.raises(ValueError, match="section"):
        Score().section("A", first, last, repeat=repeat)


# Transpose


def test_transpose_returns_a_new_score_and_leaves_the_old_one():
    s = Score(key=Key("D major"), title="t", tempo=90, pickup=E)
    s.part("a", gain=0.5, clef="bass").add(line([note("D4", E)], [note("F#4", 1)]))
    moved = s.transpose(Interval("m2"))
    assert moved is not s
    assert (moved.title, moved.tempo, moved.pickup, moved.part("a").gain, moved.part("a").clef) == ("t", 90, E, 0.5, "bass")
    assert s.key == Key("D major")
    assert pitches(s) == [(Pitch("D4"),), (Pitch("F#4"),)]
    moved.part("a").add(line([note("C4", 1)]))
    assert s.bars == 2


def test_transpose_d_major_up_a_minor_second_is_e_flat_major():
    s = Score(key=Key("D major"))
    s.part("a").add(line([note(name) for name in "D4 E4 F#4 G4".split()], [note(name) for name in "A4 B4 C#5 D5".split()]))
    moved = s.transpose(Interval("m2"))
    assert moved.key == Key("Eb major")
    names = [ps[0] for ps in pitches(moved)]
    assert names == [Pitch(name) for name in "Eb4 F4 G4 Ab4 Bb4 C5 D5 Eb5".split()]
    assert Pitch("Gb4") not in names


def test_transpose_d_major_up_an_augmented_unison_is_d_sharp_major():
    s = Score(key=Key("D major"))
    s.part("a").add(line([note(name) for name in "D4 F#4 C#5".split()]))
    moved = s.transpose(Interval("A1"))
    assert moved.key == Key("D# major")
    assert [ps[0] for ps in pitches(moved)] == [Pitch("D#4"), Pitch("F##4"), Pitch("C##5")]


def test_transpose_goes_down_by_a_negative_interval():
    s = Score(key=Key("C major"))
    s.part("a").add(line([note("E4")]))
    moved = s.transpose(-Interval("m2"))
    assert moved.key == Key("B major")
    assert pitches(moved) == [(Pitch("D#4"),)]


def test_transpose_moves_each_changes_key_and_each_numeral_with_it():
    s = Score(key=Key("C major"))
    s.change(2, key=Key("A minor"), tempo=60)
    s.part("a").add(line([Numeral("V", 1)], [Numeral("V", 1)]))
    moved = s.transpose(Interval("M2"))
    assert (moved.key_at(1), moved.key_at(2), moved.tempo_at(2)) == (Key("D major"), Key("B minor"), 60)
    assert pitches(moved) == [Chord("A").pitches(), Chord("F#").pitches()]


@pytest.mark.parametrize("kind", [JustIntonation, Pythagorean])
def test_transpose_moves_a_tunings_tonic(kind):
    assert Score(tuning=kind(Pitch("C4"))).transpose(Interval("M2")).tuning == kind(Pitch("D4"))


def test_transpose_keeps_equal_temperament():
    assert Score(tuning=EqualTemperament(442.0)).transpose(Interval("M2")).tuning == EqualTemperament(442.0)


def test_transpose_names_a_note_past_a_double_accidental_and_its_bar():
    s = Score()
    s.part("a").add(line([note("C4")], [note("C4")], [note("F##4")]))
    with pytest.raises(ValueError, match=r"bar 3.*F##4"):
        s.transpose(Interval("A1"))


def test_transpose_names_the_bar_of_a_line_placed_later():
    s = Score()
    s.part("a").add(line([note("F##4")]), at=5)
    with pytest.raises(ValueError, match=r"bar 5.*F##4"):
        s.transpose(Interval("A1"))


def test_transpose_keeps_hits_rests_marks_sections_and_ramps():
    kit = Kit()
    s = Score()
    part = s.part("drums", kit).add(line([Hit("kick", Q), Rest(Q), BarRest()]))
    part.dynamic(1, 2, "p").hairpin((1, 1), (1, 3), "<")
    s.section("A", 1, 2, repeat=2)
    s.ramp(1, 2, 60)
    moved = s.transpose(Interval("M2"))
    assert moved.part("drums").instrument is kit
    assert [p.event for p in moved.events()] == [p.event for p in s.events()]
    assert moved.part("drums").dynamics == part.dynamics
    assert moved.part("drums").hairpins == part.hairpins
    assert moved.sections == s.sections
    assert moved.ramps == s.ramps


def test_two_parts_on_one_instrument_stay_on_one_after_transpose():
    harp = Harp()
    s = Score()
    s.part("left", harp)
    s.part("right", harp)
    moved = s.transpose(Interval("M2"))
    assert moved.part("left").instrument is moved.part("right").instrument is harp


# Harmony


def test_harmony_names_each_beat_against_the_key_in_force():
    s = Score(key=Key("C major"), meter=Meter("2/4"))
    s.change(2, key=Key("G major"))
    s.part("a").add(line([stack("C4 E4 G4"), stack("G3 B3 D4 F4")], [stack("G3 B3 D4", 2 * Q)]))
    assert s.harmony() == [
        Harmony(1, 1, Chord("C"), Key("C major").roman("I")),
        Harmony(1, 2, Chord("G7"), Key("C major").roman("V7")),
        Harmony(2, 1, Chord("G"), Key("G major").roman("I")),
        Harmony(2, 2, Chord("G"), Key("G major").roman("I")),
    ]


def test_harmony_reads_across_parts_and_notes_held_over_a_beat_or_a_bar():
    s = Score(meter=Meter("2/4"))
    s.part("bass").add(line([note("C3", 3 * Q)], [Rest(Q)]))
    s.part("mid").add(line([note("E4", 2 * Q)], [note("E4", 2 * Q)]))
    s.part("top").add(line([note("G4", 2 * Q)], [note("G4", 2 * Q)]))
    assert [h.chord for h in s.harmony()] == [Chord("C"), Chord("C"), Chord("C"), None]


def test_harmony_lets_the_longest_notes_win_over_a_passing_note():
    s = Score(meter=Meter("1/4"))
    s.part("low").add(line([stack("C4 E4 G4")]))
    s.part("top").add(line([note("A4", E), note("B4", E)]))
    assert s.harmony()[0].chord == Chord("C")


def test_harmony_finds_a_chord_under_a_longer_chord_tone():
    s = Score(meter=Meter("1/4"))
    s.part("top").add(line([note("G5", Q)]))
    s.part("low").add(line([stack("C4 E4 G4", E), Rest(E)]))
    assert s.harmony()[0].chord == Chord("C")


def test_harmony_finds_none_under_a_longer_tone_outside_the_chord():
    s = Score(meter=Meter("1/4"))
    s.part("top").add(line([note("D5", Q)]))
    s.part("low").add(line([stack("C4 E4 G4", E), Rest(E)]))
    assert s.harmony()[0].chord is None


def test_harmony_breaks_a_tie_in_length_toward_the_bass():
    s = Score(meter=Meter("1/4"))
    s.part("a").add(line([stack("C4 E4 G4 D5")]))
    assert s.harmony()[0].chord == Chord("C")


def test_harmony_takes_a_seventh_as_long_as_the_triad():
    s = Score(meter=Meter("1/4"))
    s.part("a").add(line([stack("C3 C4 E4 G4 Bb4")]))
    assert s.harmony()[0].chord == Chord("C7")


def test_harmony_counts_a_doubled_tone_once():
    s = Score(meter=Meter("1/4"))
    s.part("low").add(line([stack("C3 E3 G3")]))
    s.part("high").add(line([stack("C4 E4 G4 Bb4")]))
    assert s.harmony()[0].chord == Chord("C7")


def test_harmony_counts_a_tone_by_its_longest_note_in_the_beat():
    s = Score(meter=Meter("1/4"))
    s.part("low").add(line([stack("C4 E4 G4", E), Rest(E)]))
    s.part("top").add(line([note("Bb4", E), note("Bb4", Fraction(1, 16)), Rest(Fraction(1, 16))]))
    assert s.harmony()[0].chord == Chord("C7")


def test_harmony_takes_the_lowest_copy_of_a_doubled_tone_as_bass():
    s = Score(meter=Meter("1/4"))
    s.part("low").add(line([note("E3")]))
    s.part("high").add(line([stack("C4 E5 G4")]))
    assert s.harmony()[0].chord == Chord("C/E")


def test_harmony_takes_the_bass_from_any_part():
    s = Score(meter=Meter("1/4"))
    s.part("high").add(line([stack("C4 E4 G4")]))
    s.part("low").add(line([note("E3")]))
    assert s.harmony()[0].chord == Chord("C/E")


def test_harmony_counts_only_the_time_a_note_sounds_in_the_beat():
    s = Score(meter=Meter("2/4"))
    s.part("low").add(line([stack("C4 E4 G4"), stack("C4 E4 G4")]))
    s.part("top").add(line([note("D5", Fraction(3, 8)), Rest(E)]))
    assert s.harmony()[1].chord == Chord("C")


def test_harmony_keeps_the_bass_of_an_inversion():
    s = Score(meter=Meter("1/4"))
    s.part("a").add(line([stack("E3 C4 G4")]))
    assert s.harmony()[0] == Harmony(1, 1, Chord("C/E"), Key("C major").roman("I6"))


def test_a_beat_with_no_chord_has_none_in_both():
    s = Score(meter=Meter("3/4"))
    s.part("a").add(line([stack("C4 D4"), Rest(Q), Hit("kick", Q)]))
    assert s.harmony() == [Harmony(1, 1, None, None), Harmony(1, 2, None, None), Harmony(1, 3, None, None)]


def test_a_chord_with_no_numeral_keeps_the_chord():
    s = Score(meter=Meter("1/4"))
    s.part("a").add(line([stack("C4 F4 G4")]))
    assert s.harmony() == [Harmony(1, 1, Chord("Csus4"), None)]


def test_harmony_counts_compound_and_uneven_beats():
    s = Score(meter=Meter("6/8"))
    s.part("a").add(line([stack("C4 E4 G4", Fraction(3, 4))]))
    assert [h.beat for h in s.harmony()] == [1, 2]
    t = Score(meter=Meter("7/8", groups=(2, 2, 3)))
    t.part("a").add(line([stack("C4 E4 G4", Fraction(2, 8)), Rest(Fraction(2, 8)), stack("D4 F4 A4", Fraction(3, 8))]))
    assert [(h.beat, h.chord) for h in t.harmony()] == [(1, Chord("C")), (2, None), (3, Chord("Dm"))]


def test_harmony_numbers_a_pickups_beats_from_the_end_of_the_short_bar():
    s = Score(pickup=Q)
    s.part("a").add(line([stack("G3 B3 D4")], [stack("C4 E4 G4", 1)]))
    harmony = s.harmony()
    assert harmony[0] == Harmony(1, 4, Chord("G"), Key("C major").roman("V"))
    assert [h.bar for h in harmony] == [1, 2, 2, 2, 2]
    assert [h.beat for h in harmony[1:]] == [1, 2, 3, 4]


def test_harmony_of_an_empty_score_is_empty():
    assert Score().harmony() == []
    assert list(Score().events()) == []


def test_thin_and_uneven_parts_read_without_fuss():
    s = Score(meter=Meter("1/4"))
    s.part("silent")
    s.part("short").add(line([stack("C4 E4 G4")]))
    s.part("long").add(line([stack("C4 E4 G4")], [note("D4")]))
    assert s.bars == 2
    assert s.part("silent").measures == []
    assert [h.chord for h in s.harmony()] == [Chord("C"), None]


# Score defaults and exports


def test_score_defaults():
    s = Score()
    assert (s.key, s.meter, s.tempo, s.tuning, s.pickup, s.performance, s.title) == (
        Key("C major"), Meter("4/4"), 120, EqualTemperament(), 0, None, None)


def test_score_is_exported_from_euterpe_and_the_written_note_is_not():
    assert euterpe.Score is euterpe.score.Score
    assert "Score" in euterpe.__all__
    assert not hasattr(euterpe, "Note")
    assert "Note" not in euterpe.__all__
    assert euterpe.score.Note is Note
    assert euterpe.score.Note is not PerformedNote
    assert "Note" in euterpe.score.__all__


def test_tenuto_is_an_articulation_that_changes_nothing():
    performed = PerformedNote(0.0, Pitch("C4"), 1.0, 0.5)
    assert isinstance(Tenuto(), Articulation)
    assert Tenuto().apply(performed) is performed
    assert note("C4", articulations=(Tenuto(), Accent())).articulations == (Tenuto(), Accent())
