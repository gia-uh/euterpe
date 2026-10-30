from fractions import Fraction
from math import log

import numpy as np
import pytest

import euterpe
import euterpe.score
from euterpe import (
    Dynamics,
    EqualTemperament,
    Humanize,
    JustIntonation,
    Key,
    Lengths,
    Meter,
    Performance,
    Pitch,
    Score,
    Swing,
    TempoMap,
    drums,
    melody,
)
from euterpe.instruments import Accent, ElectricPiano, Harp, Kit, Legato, Open, Staccato, Violin
from euterpe.instruments.percussion import STEPS
from euterpe.score import Hit, Line, Note, part_seeds

Q = Fraction(1, 4)
E = Fraction(1, 8)
MF = 0.62
STRESS = 0.05


def score(text, performance=None, part="a", instrument=None, **kwargs):
    s = Score(performance=performance or Performance(), **kwargs)
    s.part(part, instrument).add(melody(text))
    return s


def played(text, performance=None, **kwargs):
    s = score(text, performance, **kwargs)
    return s.performance.notes(s)["a"]


def times(notes):
    return [note.time for note in notes]


def values(notes):
    """What a note says, without its generator, which play sets."""
    return [(n.time, n.pitch, n.duration, n.velocity, n.articulation) for n in notes]


def test_the_defaults():
    assert Score().performance == Performance()
    assert Performance() == Performance(None, Lengths(), Dynamics(), None)
    assert Swing() == Swing(2 / 3, E)
    assert Lengths() == Lengths(0.9, 1.0, 1.0)
    assert Humanize() == Humanize(0.008, 0.04)
    dynamics = Dynamics()
    assert dynamics.levels == {"pp": .25, "p": .38, "mp": .5, "mf": .62, "f": .76, "ff": .9}
    assert (dynamics.stress, dynamics.accent) == (0.05, 1.3)


def test_the_settings_are_hashable_values():
    assert hash(Performance()) == hash(Performance())


def test_the_classes_are_exported_from_euterpe():
    assert {"Dynamics", "Humanize", "Lengths", "Performance", "Swing", "TempoMap"} <= set(euterpe.__all__)
    assert {"Dynamics", "Humanize", "Lengths", "Performance", "Swing", "TempoMap", "part_seeds"} <= set(euterpe.score.__all__)


# The tempo map


def test_four_beats_from_120_to_60_last_4_ln_2():
    s = Score(tempo=120)
    s.ramp(1, 1, 60)
    assert s.tempo_map().seconds(Fraction(1)) == pytest.approx(4 * log(2), abs=1e-9)
    assert s.tempo_map().seconds(Fraction(1)) == pytest.approx(2.7726, abs=1e-4)


def test_a_ramp_in_the_middle_of_the_score_has_the_closed_form():
    s = Score(tempo=90)
    s.ramp(2, 2, 180)
    n = 8
    closed = 60 * n * log(90 / 180) / (90 - 180)
    assert s.tempo_map().seconds(Fraction(3)) - s.tempo_map().seconds(Fraction(1)) == pytest.approx(closed, abs=1e-9)


def test_six_eight_at_60_has_a_2_s_bar():
    s = Score(meter=Meter("6/8"), tempo=60)
    assert s.tempo_map().seconds(Fraction(6, 8)) == pytest.approx(2.0)


@pytest.mark.parametrize("meter, seconds", [("3/4", 3.0), ("2/2", 2.0), ("4/4", 4.0), ("7/8", 7.0)])
def test_a_number_tempo_counts_the_meters_beat(meter, seconds):
    s = Score(meter=Meter(meter), tempo=60)
    assert s.tempo_map().seconds(Meter(meter).bar) == pytest.approx(seconds)


def test_a_ramp_whose_two_ends_are_equal_is_the_formulas_limit():
    s = Score(tempo=120)
    s.ramp(1, 1, 120)
    assert s.tempo_map().seconds(Fraction(1)) == pytest.approx(60 * 4 / 120)


def test_a_ramp_to_a_tempo_at_or_below_0_raises():
    for to in (0, -10):
        with pytest.raises(ValueError):
            Score().ramp(1, 1, to)


def test_tempo_after_a_ramp_holds_until_the_next_change():
    s = Score(tempo=120)
    s.ramp(1, 1, 60)
    s.change(4, tempo=240)
    tempo = s.tempo_map()
    assert tempo.seconds(Fraction(3)) - tempo.seconds(Fraction(2)) == pytest.approx(4.0)  # still 60
    assert tempo.seconds(Fraction(4)) - tempo.seconds(Fraction(3)) == pytest.approx(1.0)  # 240 from bar 4
    assert tempo.seconds(Fraction(7)) - tempo.seconds(Fraction(6)) == pytest.approx(1.0)  # past every bar named


def test_a_meter_change_changes_what_a_number_tempo_counts():
    s = Score(tempo=60)
    s.change(2, meter=Meter("6/8"))
    assert s.tempo_map().seconds(Fraction(1) + Fraction(6, 8)) == pytest.approx(4.0 + 2.0)


@pytest.mark.parametrize("seconds", [0.0, 0.1, 1.0, 2.7, 3.0, 4.0, 9.0, 30.0])
def test_offset_undoes_seconds(seconds):
    s = Score(tempo=120)
    s.ramp(2, 2, 60)
    s.section("A", 1, 3, repeat=2)
    tempo = s.tempo_map()
    assert tempo.seconds(tempo.offset(seconds)) == pytest.approx(seconds, abs=1e-6)


def test_offset_is_exact_on_a_constant_tempo():
    offset = Score(tempo=120).tempo_map().offset(1.0)
    assert isinstance(offset, Fraction) and offset == Fraction(1, 2)


def test_the_tempo_map_refuses_a_time_before_the_start():
    with pytest.raises(ValueError):
        Score().tempo_map().seconds(Fraction(-1, 4))
    with pytest.raises(ValueError):
        Score().tempo_map().offset(-1.0)


def test_the_tempo_map_reads_the_expanded_timeline():
    s = Score(tempo=120)
    s.part("a").add(melody("c4:w | d4:w | e4:w"))
    s.section("A", 1, 2, repeat=2)
    assert isinstance(s.tempo_map(), TempoMap)
    assert s.tempo_map().seconds(Fraction(5)) == pytest.approx(10.0)


def test_a_ramp_in_a_repeated_section_lasts_its_time_on_both_passes():
    s = Score(tempo=120)
    s.part("a").add(melody("c4:w | d4:w"))
    s.ramp(1, 1, 60)
    s.section("A", 1, 1, repeat=2)
    tempo = s.tempo_map()
    assert tempo.seconds(Fraction(1)) == pytest.approx(2.7726, abs=1e-4)
    assert tempo.seconds(Fraction(2)) - tempo.seconds(Fraction(1)) == pytest.approx(2.7726, abs=1e-4)
    notes = s.performance.notes(s)["a"]
    assert times(notes) == pytest.approx([0, 4 * log(2), 8 * log(2)])
    assert [note.pitch for note in notes] == [Pitch("C4"), Pitch("C4"), Pitch("D4")]
    assert s.tempo_map().seconds(Fraction(3)) - tempo.seconds(Fraction(2)) == pytest.approx(4.0)  # 60 held after it


# Swing


def test_swing_sends_a_second_eighth_to_two_thirds_of_the_beat_and_leaves_beats_alone():
    notes = played("c4:e d e f g:q a", Performance(swing=Swing()))
    assert times(notes) == pytest.approx([0, 1 / 3, 0.5, 5 / 6, 1.0, 1.5])


def test_swing_moves_ends_with_positions():
    notes = played("c4:e d", Performance(swing=Swing(), lengths=Lengths(normal=1.0)))
    assert [note.duration for note in notes] == pytest.approx([1 / 3, 1 / 6])


def test_swing_moves_a_position_piecewise_linearly_inside_a_pair():
    swing = Swing(Fraction(3, 4))
    meter = Meter("4/4")
    assert swing.moved(Fraction(0), meter) == 0
    assert swing.moved(E / 2, meter) == Fraction(3, 32)
    assert swing.moved(E, meter) == Fraction(3, 16)
    assert swing.moved(E + E / 2, meter) == Fraction(7, 32)
    assert swing.moved(Q, meter) == Q
    assert swing.moved(Q + E, meter) == Q + Fraction(3, 16)
    assert swing.moved(Fraction(1) + E, meter) == Fraction(1) + Fraction(3, 16)  # past the bar, as past a score's end


def test_swing_needs_a_ratio_inside_the_pair():
    for ratio in (0, 1):
        with pytest.raises(ValueError):
            Swing(ratio)
    with pytest.raises(ValueError):
        Swing(unit=0)
    with pytest.raises(ValueError):
        Swing(unit=0.125)


def test_swing_of_another_unit():
    notes = played("c4:s d e f g:q", Performance(swing=Swing(unit=Fraction(1, 16))))
    assert times(notes) == pytest.approx([0, 1 / 6, 1 / 4, 5 / 12, 1 / 2])


def test_swing_on_a_pickup_eighth_moves_it_as_the_second_of_its_pair():
    s = score("c4:e | d4:q", Performance(swing=Swing()), pickup=E)
    notes = s.performance.notes(s)["a"]
    assert times(notes) == pytest.approx([1 / 12, 0.25])


def test_a_note_ending_on_a_bar_line_ends_at_the_downbeat_in_a_bar_that_cuts_a_pair():
    s = score("c4:e d e | f4:e", Performance(swing=Swing(), lengths=Lengths(normal=1.0)), meter=Meter("3/8"))
    notes = s.performance.notes(s)["a"]
    assert notes[2].time + notes[2].duration == pytest.approx(notes[3].time)


@pytest.mark.parametrize("meter, swing, text", [
    ("3/8", Swing(), "c4:e d e:s. f:t | g4:e d e"),
    ("3/4", Swing(unit=Q), "c4:q d e:e. f:s | g4:q a b"),
    ("3/4", Swing(.75, Q), "c4:q d e:e. f:s | g4:q a b"),
])
def test_a_pair_the_bar_cuts_stays_straight(meter, swing, text):
    s = score(text, Performance(swing=swing), meter=Meter(meter), tempo=60)
    notes = s.performance.notes(s)["a"]
    written = [placed.event.pitches[0] for placed in s.events("a")]
    assert [note.pitch for note in notes] == written
    assert all(note.duration > 0 for note in notes)
    assert all(a.time < b.time for a, b in zip(notes, notes[1:]))
    tempo = s.tempo_map()
    cut = [placed for placed in s.events("a") if placed.bar == 1][2:]  # the third count of the bar on
    assert [note.time for note in notes[2:2 + len(cut)]] == pytest.approx([tempo.seconds(p.offset) for p in cut])
    assert len(Harp().play(notes).voices) == len(notes)


@pytest.mark.parametrize("meter", ["6/8", "12/8"])
def test_swing_leaves_a_compound_beat_alone_and_moves_the_second_eighth_of_each(meter):
    meter = Meter(meter)
    text = " ".join(["c4:e d e"] * meter.beats)
    s = score(text, Performance(swing=Swing()), meter=meter, tempo=60)
    notes = s.performance.notes(s)["a"]
    tempo = s.tempo_map()
    for beat in range(meter.beats):
        first, second, third = notes[3 * beat:3 * beat + 3]
        assert first.time == pytest.approx(tempo.seconds(beat * meter.beat))
        assert second.time == pytest.approx(tempo.seconds(beat * meter.beat + Q * Fraction(2, 3)))
        assert second.time != pytest.approx(tempo.seconds(beat * meter.beat + E))
        assert third.time == pytest.approx(tempo.seconds(beat * meter.beat + Q))


def test_a_beat_no_longer_than_the_pair_lets_the_unit_ask_for_it():
    s = score("c4:e d e f g a b", Performance(swing=Swing()), meter=Meter("7/8"), tempo=60)
    assert s.performance.notes(s)["a"][1].time == pytest.approx(s.tempo_map().seconds(Q * Fraction(2, 3)))
    s = score("c4:q d e f", Performance(swing=Swing(unit=Q)))
    assert times(s.performance.notes(s)["a"]) == pytest.approx([0, 2 / 3, 1, 5 / 3])


def test_swing_keeps_the_start_of_each_uneven_group():
    s = score("c4:e d e f g a b", Performance(swing=Swing()), meter=Meter("7/8", groups=(3, 2, 2)), tempo=60)
    tempo = s.tempo_map()
    starts = times(s.performance.notes(s)["a"])
    assert starts[3] == pytest.approx(tempo.seconds(3 * E))
    assert starts[5] == pytest.approx(tempo.seconds(5 * E))
    assert starts[1] == pytest.approx(tempo.seconds(Q * Fraction(2, 3)))


def test_a_triplet_keeps_its_exact_place_and_swings_by_position():
    straight = played("3[c4:e d e] f4:q")
    assert times(straight) == pytest.approx([0, 1 / 6, 1 / 3, 1 / 2])
    assert [n.duration for n in straight[:3]] == pytest.approx([0.9 / 6] * 3)
    swung = played("3[c4:e d e] f4:q", Performance(swing=Swing()))
    assert times(swung) == pytest.approx([0, 2 / 9, 7 / 18, 1 / 2])


def test_a_tie_inside_a_triplet_merges():
    notes = played("3[c4:e~ c d] e4:q")
    assert [n.pitch for n in notes] == [Pitch("C4"), Pitch("D4"), Pitch("E4")]
    assert notes[0].duration == pytest.approx(0.9 / 3)


def test_swing_goes_first_and_the_tempo_map_after_it():
    s = score("c4:e d", Performance(swing=Swing()), tempo=60)
    assert times(s.performance.notes(s)["a"]) == pytest.approx([0, 2 / 3])


# Lengths and articulations


def test_a_note_sounds_for_its_fraction_of_the_written_length():
    notes = played("c4:q d_ e", Performance(lengths=Lengths(normal=0.5, tenuto=0.8)))
    assert [note.duration for note in notes] == pytest.approx([0.25, 0.4, 0.25])


def test_slur_notes_take_their_length():
    notes = played("( c4:q d ) e", Performance(lengths=Lengths(normal=0.5, slur=0.75)))
    assert [note.duration for note in notes] == pytest.approx([0.375, 0.375, 0.25])


def test_a_staccato_note_lasts_its_fraction_of_the_written_length_once():
    notes = played("c4:q'")
    assert notes[0].duration == pytest.approx(0.5)
    assert isinstance(notes[0].articulation, Staccato)
    assert Harp().play(notes).notes[0].duration == pytest.approx(0.25)


def test_accent_and_tenuto_are_consumed_and_never_sent_on():
    assert [note.articulation for note in played("c4:q> d_ e>_")] == [None, None, None]


def test_a_legato_note_after_the_first_of_a_slur_carries_legato():
    first, second, third, after = played("( c4:q d e ) f")
    assert first.articulation is None
    assert isinstance(second.articulation, Legato) and isinstance(third.articulation, Legato)
    assert after.articulation is None


def test_a_note_carries_one_articulation():
    first, second = played("( c4:q d' )")
    assert isinstance(second.articulation, Legato)
    assert second.duration == pytest.approx(0.5)


def test_another_articulation_reaches_the_instrument():
    open_stroke = Open()
    s = Score()
    s.part("a").add(Line([[Note(Pitch("C4"), Q, articulations=(Accent(), open_stroke))]]))
    assert s.performance.notes(s)["a"][0].articulation is open_stroke


def test_a_tie_merges_into_one_note():
    assert [(n.pitch, n.duration) for n in played("c4:q~ c:e d")] == [
        (Pitch("C4"), pytest.approx(0.75 * 0.9)), (Pitch("D4"), pytest.approx(0.25 * 0.9))]


def test_a_tie_across_bars_is_one_note_and_chains():
    notes = played("c4:w~ | c4:w~ | c4:w d4")
    assert len(notes) == 2
    assert notes[0].duration == pytest.approx(6 * 0.9)


def test_a_tie_to_a_different_pitch_does_not_merge():
    assert len(played("c4:q~ d")) == 2


def test_a_tie_over_a_rest_does_not_merge():
    assert len(played("c4:q~ r c")) == 2


def test_a_stack_ties_pitch_by_pitch():
    notes = played("<c4 e>:q~ <c e g>")
    assert [(n.pitch, n.duration) for n in notes] == [
        (Pitch("C4"), pytest.approx(0.9)), (Pitch("E4"), pytest.approx(0.9)), (Pitch("G4"), pytest.approx(0.45))]


def test_voices_do_not_tie_to_each_other():
    s = Score()
    s.part("a").add(melody("c4:q~")).add(melody("r:q c4"), voice=1)
    assert len(s.performance.notes(s)["a"]) == 2


def test_a_tie_out_of_a_repeats_last_bar_does_not_join_the_first_bar_on_the_second_pass():
    s = Score()
    s.part("a").add(melody("c4:w | c4:w~ | c4:w"))
    s.section("A", 1, 2, repeat=2)
    notes = s.performance.notes(s)["a"]
    assert times(notes) == pytest.approx([0, 2, 4, 6])  # the tie joins only bar 3, on the last pass
    assert [n.duration for n in notes] == pytest.approx([1.8, 1.8, 1.8, 3.6])


def test_repeats_play_out():
    s = Score()
    s.part("a").add(melody("c4:w | d4:w | e4:w"))
    s.section("A", 2, 2, repeat=3)
    assert [n.pitch.letter for n in s.performance.notes(s)["a"]] == list("CDDDE")


# Dynamics


def test_without_a_mark_a_part_plays_mf():
    assert played("c4:q d e f")[0].velocity == pytest.approx(MF + STRESS)
    assert played("c4:q d e f")[2].velocity == pytest.approx(MF)


def test_a_mark_sets_the_level_and_stress_moves_it():
    notes = played("p c4:q d e f")
    assert [n.velocity for n in notes] == pytest.approx([.38 + STRESS, .38 - STRESS, .38, .38 - STRESS])


def test_a_weak_position_is_as_weak_as_the_weakest_beat():
    notes = played("c4:e d e f g a b c")
    assert notes[1].velocity == pytest.approx(MF - STRESS)
    notes = played("c4:e d e f g a", meter=Meter("6/8"))
    assert [n.velocity for n in notes] == pytest.approx([MF + STRESS, MF - STRESS, MF - STRESS, MF, MF - STRESS, MF - STRESS])


def test_a_pickup_is_not_a_downbeat():
    notes = played("c4:q | d4:q", pickup=Q)
    assert notes[0].velocity == pytest.approx(MF - STRESS)
    assert notes[1].velocity == pytest.approx(MF + STRESS)


def test_the_stress_is_a_setting():
    notes = played("c4:q d", Performance(dynamics=Dynamics(stress=0.1)))
    assert [n.velocity for n in notes] == pytest.approx([MF + 0.1, MF - 0.1])


def test_an_accent_multiplies_up_to_1():
    notes = played("c4:q d> ff e> f>", Performance(dynamics=Dynamics(stress=0, accent=1.5)))
    assert [n.velocity for n in notes] == pytest.approx([MF, MF * 1.5, 1.0, 1.0])


def test_a_hairpin_rises_monotonically():
    velocities = [n.velocity for n in played("p < c4:q d e f | g a b c | f! c4", Performance(dynamics=Dynamics(stress=0)))]
    assert velocities == sorted(velocities)
    assert velocities[0] == pytest.approx(.38)
    assert velocities[1] == pytest.approx(.38 + (.76 - .38) / 8)
    assert velocities[-1] == pytest.approx(.76)


def test_a_decrescendo_falls():
    velocities = [n.velocity for n in played("f! > c4:q d e f | p g", Performance(dynamics=Dynamics(stress=0)))]
    assert velocities == sorted(velocities, reverse=True)
    assert (velocities[0], velocities[-1]) == (pytest.approx(.76), pytest.approx(.38))


def test_a_hairpin_with_no_mark_after_it_ends_one_level_on():
    s = Score(performance=Performance(dynamics=Dynamics(stress=0)))
    part = s.part("a").add(melody("p c4:q d e f | g a b c | c d e f"))
    part.hairpin((1, 1), (2, 1), "<")
    velocities = [n.velocity for n in s.performance.notes(s)["a"]]
    assert velocities[:4] == pytest.approx([.38, .38 + .03, .38 + .06, .38 + .09])
    assert velocities[4:] == pytest.approx([.5] * 8)  # the level it reached holds


def test_a_hairpin_at_the_top_level_stays_there():
    notes = played("ff < c4:q d e f", Performance(dynamics=Dynamics(stress=0)))
    assert {n.velocity for n in notes} == {.9}


def test_a_mark_inside_a_hairpin_ends_it_there():
    s = Score(performance=Performance(dynamics=Dynamics(stress=0)))
    part = s.part("a").add(melody("p c4:q d e f | g a b c"))
    part.hairpin((1, 1), (2, 3), "<").dynamic(2, 1, "f")
    velocities = [n.velocity for n in s.performance.notes(s)["a"]]
    assert velocities[:4] == pytest.approx([.38 + (.76 - .38) * i / 4 for i in range(4)])
    assert velocities[4:] == pytest.approx([.76] * 4)


def test_mf_is_only_read_for_a_note_before_any_mark():
    assert played("p c4:q", Performance(dynamics=Dynamics(levels={"p": .3}, stress=0)))[0].velocity == pytest.approx(.3)
    with pytest.raises(ValueError, match="mf"):
        played("c4:q p d", Performance(dynamics=Dynamics(levels={"p": .3})))


def test_a_mark_the_levels_do_not_hold_raises_naming_it():
    s = Score()
    s.part("a").add(melody("c4:q")).dynamic(1, 1, "fff")
    with pytest.raises(ValueError, match="fff"):
        s.performance.notes(s)


def test_velocity_stays_inside_0_and_1():
    notes = played("c4:q d", Performance(dynamics=Dynamics(levels={"mf": 0.0}, stress=0.05)))
    assert notes[1].velocity == 0.0
    notes = played("c4:q d", Performance(dynamics=Dynamics(levels={"mf": 1.0}, stress=0.05)))
    assert notes[0].velocity == 1.0


# Drums


def test_a_hit_becomes_a_stroke_of_the_kits_drum():
    kit = Kit()
    s = Score(performance=Performance(dynamics=Dynamics(stress=0)))
    s.part("drums", kit).add(drums({"kick": "x...", "snare": "..X.", "hihat": "g..o", "tom2": ".x.."}, step="q"))
    notes = s.performance.notes(s)["drums"]
    assert [(n.time, n.resource) for n in notes] == [
        (0.0, kit.kick), (0.0, kit.hihat), (0.5, kit.toms[1]), (1.0, kit.snare), (1.5, kit.hihat)]
    assert [n.velocity for n in notes] == pytest.approx([MF * STEPS[c] for c in "xgxXo"])
    assert isinstance(notes[-1].articulation, Open)
    assert notes[0].articulation is None


def test_a_hit_with_no_accent_is_a_plain_stroke():
    s = Score(performance=Performance(dynamics=Dynamics(stress=0)))
    s.part("drums", Kit()).add(Line([[Hit("kick", Q)]]))
    assert s.performance.notes(s)["drums"][0].velocity == pytest.approx(MF * STEPS["x"])


def test_a_hit_on_a_part_with_no_instrument_yet_still_performs():
    s = Score()
    s.part("drums").add(drums({"kick": "x"}, step="q"))
    assert len(s.performance.notes(s)["drums"]) == 1


def test_a_drum_the_kit_does_not_have_raises_naming_it():
    s = Score()
    s.part("drums", Kit(toms=())).add(drums({"tom1": "x"}, step="q"))
    with pytest.raises(ValueError, match="tom1"):
        s.performance.notes(s)


def test_swing_moves_hits():
    s = Score(performance=Performance(swing=Swing()))
    s.part("drums", Kit()).add(drums({"hihat": "xx"}, step="e"))
    assert times(s.performance.notes(s)["drums"]) == pytest.approx([0, 1 / 3])


# Tuning


def test_equal_temperament_at_440_sends_the_pitch():
    assert played("c4:q")[0].pitch == Pitch("C4")


@pytest.mark.parametrize("tuning", [EqualTemperament(432.0), JustIntonation(Pitch("C4"))])
def test_another_tuning_sends_hertz(tuning):
    pitch = played("e4:q", tuning=tuning)[0].pitch
    assert isinstance(pitch, float) and pitch == pytest.approx(tuning.freq(Pitch("E4")))


# Humanize and seeds


def test_humanize_none_has_exact_times():
    notes = played("c4:q d e f | g a b c")
    assert times(notes) == [i * 0.5 for i in range(8)]


def test_the_same_seed_gives_the_same_notes_and_another_seed_other_ones():
    s = score("c4:s d e f g a b c d e f g a b c d", Performance(humanize=Humanize()))
    same, again, other = s.performance.notes(s, seed=3), s.performance.notes(s, seed=3), s.performance.notes(s, seed=4)
    assert values(same["a"]) == values(again["a"])
    assert times(same["a"]) != times(other["a"])
    assert [n.velocity for n in same["a"]] != [n.velocity for n in other["a"]]


def test_adding_a_part_at_the_end_does_not_change_the_earlier_parts_notes():
    s = score("c4:s d e f g a b c", Performance(humanize=Humanize()))
    before = values(s.performance.notes(s)["a"])
    s.part("b").add(melody("c3:w"))
    assert values(s.performance.notes(s)["a"]) == before


def test_each_part_has_its_own_stream():
    s = Score(performance=Performance(humanize=Humanize()))
    s.part("a").add(melody("c4:s d e f g a b c"))
    s.part("b").add(melody("c4:s d e f g a b c"))
    notes = s.performance.notes(s)
    assert times(notes["a"]) != times(notes["b"])


def test_part_seeds_split_each_parts_stream_in_two():
    seeds = part_seeds(7, 3)
    assert len(seeds) == 3
    for index, (stream, play_seed) in enumerate(seeds):
        expected = np.random.SeedSequence(7).spawn(3)[index].spawn(2)
        assert stream.spawn_key == expected[0].spawn_key
        assert play_seed == int(expected[1].generate_state(1)[0])
    assert [b for _, b in part_seeds(7, 4)[:3]] == [b for _, b in seeds]
    assert len({b for _, b in seeds}) == 3


def test_a_humanized_start_is_clipped_at_3_sd():
    timing = 0.01
    s = score("c4:s d e f g a b c " * 8, Performance(humanize=Humanize(timing=timing, velocity=0)))
    straight = Performance().notes(s)["a"]
    moved = [a.time - b.time for seed in range(50) for a, b in zip(s.performance.notes(s, seed=seed)["a"][1:], straight[1:])]
    assert max(abs(move) for move in moved) == pytest.approx(3 * timing)
    assert np.std(moved) == pytest.approx(timing, rel=0.1)


def test_time_0_clips_an_early_start():
    s = score("c4:q d", Performance(humanize=Humanize(timing=1.0, velocity=0)))
    starts = [s.performance.notes(s, seed=seed)["a"][0].time for seed in range(30)]
    assert min(starts) == 0.0 and max(starts) > 0.0


def test_a_humanized_velocity_stays_inside_0_and_1():
    s = score("c4:s d e f g a b c", Performance(humanize=Humanize(timing=0, velocity=1.0)))
    velocities = [n.velocity for n in s.performance.notes(s)["a"]]
    assert all(0.0 <= v <= 1.0 for v in velocities) and {0.0, 1.0} & set(velocities)


def test_notes_in_one_stack_share_most_of_the_start():
    s = score("<c4 e g>:q <d f a> <e g b> <f a c5> " * 8, Performance(humanize=Humanize(timing=0.02, velocity=0)))
    notes = s.performance.notes(s)["a"]
    straight = Performance().notes(s)["a"]
    moves = [a.time - b.time for a, b in zip(sorted(notes, key=lambda n: (round(n.time * 2), n.pitch.number)),
                                              sorted(straight, key=lambda n: (round(n.time * 2), n.pitch.number)))]
    spreads = [max(moves[i:i + 3]) - min(moves[i:i + 3]) for i in range(3, len(moves), 3)]
    assert max(spreads) < 0.02 * 3
    assert np.mean(spreads) < np.std(moves)
    assert np.mean(spreads) > 0


def test_a_tied_note_draws_once_and_moves_as_one():
    s = score("c4:q~ c4 d", Performance(humanize=Humanize(timing=0.01, velocity=0), lengths=Lengths(normal=1.0)))
    notes = s.performance.notes(s)["a"]
    assert len(notes) == 2
    assert notes[0].duration == pytest.approx(1.0)  # both written notes, not moved apart


# A one-voice instrument


def test_violin_in_sixteenths_under_humanize_has_no_note_starting_before_the_previous_ends():
    s = score("c5:s d e f g a b c6 " * 4, Performance(humanize=Humanize(timing=0.03)), instrument=Violin(), tempo=120)
    for seed in range(5):
        notes = s.performance.notes(s, seed=seed)["a"]
        assert all(a.time + a.duration <= b.time + 1e-9 for a, b in zip(notes, notes[1:]))
        assert len(Violin().play(notes).voices) == len(notes)  # no slur the score did not write


def test_a_legato_note_may_start_before_the_previous_ends():
    s = score("( c5:e d e f ) g", Performance(humanize=Humanize(timing=0.03)), instrument=Violin())
    for seed in range(20):
        notes = s.performance.notes(s, seed=seed)["a"]
        assert len(Violin().play(notes).voices) == 2
    assert any(a.time + a.duration > b.time + 1e-9
               for seed in range(20)
               for a, b in zip(*[iter(s.performance.notes(s, seed=seed)["a"][:4])] * 2))


def test_a_stack_on_one_voice_starts_together_as_it_does_without_humanize():
    s = score("<c5 e5>:q d5", Performance(humanize=Humanize(timing=0.01)), instrument=Violin())
    first, second, third = s.performance.notes(s)["a"]
    assert first.time == second.time
    assert first.duration == pytest.approx(0.45) and second.duration == pytest.approx(0.45)
    assert len(Violin().play([first, second, third]).voices) == 2


def test_a_full_length_one_voice_line_does_not_slur_without_humanize():
    s = score("c5:s_ d_ e_ f_ g_ a_ b_ c6_", instrument=Violin())
    notes = s.performance.notes(s)["a"]
    assert len(Violin().play(notes).voices) == 8


def test_many_voices_keep_their_overlap():
    s = score("c5:s d e f", Performance(humanize=Humanize(timing=0.03), lengths=Lengths(normal=4.0)),
              instrument=ElectricPiano())
    notes = s.performance.notes(s)["a"]
    assert all(n.duration == pytest.approx(0.5) for n in notes)


# Thin scores


def test_a_score_with_no_parts_has_no_notes():
    assert Score().performance.notes(Score()) == {}


def test_a_part_with_no_notes_has_an_empty_list():
    s = Score()
    s.part("a")
    assert s.performance.notes(s) == {"a": []}


def test_a_part_with_only_rests_has_an_empty_list():
    s = score("r:q R")
    assert s.performance.notes(s) == {"a": []}


def test_a_score_keeps_its_keys_untouched():
    s = score("c4:q", key=Key("D major"))
    assert s.performance.notes(s)["a"][0].pitch == Pitch("C4")


def test_a_performance_is_not_tied_to_its_score():
    s = score("c4:e d")
    assert times(Performance(swing=Swing()).notes(s)["a"]) == pytest.approx([0, 1 / 3])
    assert times(s.performance.notes(s)["a"]) == pytest.approx([0, 0.25])
