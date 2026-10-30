from fractions import Fraction
from pathlib import Path

import mido
import pytest

import euterpe.instruments as instruments
from euterpe import Key, Meter, Score, drums, melody
from euterpe.instruments import (
    BrassSection,
    Celesta,
    Clarinet,
    ElectricPiano,
    Flute,
    Harp,
    Instrument,
    Kit,
    Organ,
    PizzicatoStrings,
    Staccato,
    StringSection,
    Tenuto,
    Timpani,
    Violin,
)
from euterpe.pitch import A3, C4, E4, Pitch
from euterpe.score import Dynamics, Hit, Humanize, Lengths, Line, Note, Performance, Rest, Swing, Tuplet
from euterpe.score.midi import _quantity
from euterpe.theory import JustIntonation


def _read(score: Score, tmp_path: Path, performed: bool = False) -> mido.MidiFile:
    return mido.MidiFile(score.to_midi(tmp_path / "score.mid", performed=performed), charset="utf8")


def _timed(track) -> list[tuple[int, mido.Message]]:
    """Each message of a track with its absolute tick."""
    at, timed = 0, []
    for message in track:
        at += message.time
        timed.append((at, message))
    return timed


def _metas(midi: mido.MidiFile, kind: str) -> list[tuple[int, mido.MetaMessage]]:
    return [(at, message) for at, message in _timed(midi.tracks[0]) if message.type == kind]


def _tempos(midi: mido.MidiFile) -> list[tuple[int, int]]:
    return [(at, message.tempo) for at, message in _metas(midi, "set_tempo")]


def _notes(track) -> list[tuple[int, int, int, int, int]]:
    """Each note of a track as (start, end, number, velocity, channel), in the order of their starts. Fails on a note
    started twice or stopped without a start."""
    opened, notes = {}, []
    for at, message in _timed(track):
        if message.type == "note_on" and message.velocity > 0:
            assert (message.note, message.channel) not in opened
            opened[message.note, message.channel] = at, message.velocity
        elif message.type in ("note_on", "note_off"):
            start, velocity = opened.pop((message.note, message.channel))
            notes.append((start, at, message.note, velocity, message.channel))
    assert not opened
    return sorted(notes)


def _score(text: str = "c4:q d4 e4 f4", **options) -> Score:
    s = Score(**options)
    s.part("a").add(melody(text))
    return s


def _starts(track) -> list[int]:
    return [note[0] for note in _notes(track)]


def _third() -> Note:
    return Note((C4,), Fraction(1, 12), tuplet=Tuplet(3, 2))


@pytest.mark.parametrize("value, data", [
    (0, "00"), (0x40, "40"), (0x7F, "7F"), (0x80, "8100"), (0x2000, "C000"), (0x1FFFFF, "FFFF7F"), (0x200000, "81808000"),
])
def test_variable_length_quantities_are_the_specification_s_examples(value, data):
    assert _quantity(value) == bytes.fromhex(data)


def test_to_midi_writes_the_file_and_returns_its_path(tmp_path):
    path = _score().to_midi(tmp_path / "s.mid")
    assert path == tmp_path / "s.mid"
    assert path.read_bytes()[:4] == b"MThd"
    assert _score().to_midi(str(tmp_path / "t.mid")) == tmp_path / "t.mid"


def test_format_1_at_480_ticks_per_quarter_with_one_track_per_part(tmp_path):
    s = _score()
    s.part("b").add(melody("e4:w"))
    midi = _read(s, tmp_path)
    assert (midi.type, midi.ticks_per_beat, len(midi.tracks)) == (1, 480, 3)
    assert [track.name for track in midi.tracks[1:]] == ["a", "b"]
    assert _notes(midi.tracks[2])[0][2] == 64


def test_track_0_holds_the_meta_events_and_no_notes(tmp_path):
    midi = _read(_score(), tmp_path)
    assert all(message.is_meta for message in midi.tracks[0])
    assert all(not message.is_meta or message.type in ("track_name", "end_of_track") for message in midi.tracks[1])


def test_the_title_names_track_0_and_a_name_keeps_its_letters(tmp_path):
    s = _score(title="Coração")
    s.part("Canción").add(melody("c4:w"))
    midi = _read(s, tmp_path)
    assert midi.tracks[0].name == "Coração"
    assert midi.tracks[2].name == "Canción"


def test_no_parts_raises(tmp_path):
    with pytest.raises(ValueError, match="no parts"):
        Score().to_midi(tmp_path / "s.mid")


def test_tempo_time_and_key_signature(tmp_path):
    midi = _read(_score("c4:q d4 e4", key=Key("D major"), meter=Meter("3/4"), tempo=90), tmp_path)
    assert _tempos(midi) == [(0, 666667)]
    (at, time), = _metas(midi, "time_signature")
    assert (at, time.numerator, time.denominator, time.clocks_per_click) == (0, 3, 4, 24)
    (at, key), = _metas(midi, "key_signature")
    assert (at, key.key) == (0, "D")


def test_six_eight_at_60_writes_the_quarter_s_tempo(tmp_path):
    midi = _read(_score("c4:e d4 e4 f4 g4 a4", meter=Meter("6/8"), tempo=60), tmp_path)
    assert _tempos(midi) == [(0, 666667)]
    (_, time), = _metas(midi, "time_signature")
    assert (time.numerator, time.denominator, time.clocks_per_click) == (6, 8, 36)


@pytest.mark.parametrize("key, written", [
    (Key("D# major"), "Eb"),  # nine sharps
    (Key("Fb major"), "E"),  # eight flats
    (Key("C# major"), "C#"),  # seven sharps fit
    (Key("Cb major"), "Cb"),
    (Key("A minor"), "Am"),
    (Key("A# minor"), "A#m"),
    (Key("D", "dorian"), "C"),  # SMF has no modes, so the signature with the major flag
    (Key("A", "aeolian"), "Am"),
])
def test_key_signature_fits_the_range_smf_holds(tmp_path, key, written):
    (_, message), = _metas(_read(_score(key=key), tmp_path), "key_signature")
    assert message.key == written


def test_changes_write_their_events_at_their_bars(tmp_path):
    s = _score("c4:w | c4:w | c4:q c4 c4")
    s.change(2, key=Key("G major"), tempo=60)
    s.change(3, meter=Meter("3/4"))
    midi = _read(s, tmp_path)
    assert _tempos(midi) == [(0, 500000), (1920, 1000000)]
    assert [(at, m.key) for at, m in _metas(midi, "key_signature")] == [(0, "C"), (1920, "G")]
    assert [(at, m.numerator) for at, m in _metas(midi, "time_signature")] == [(0, 4), (3840, 3)]


def test_a_meter_change_moves_the_quarter_s_tempo_with_its_beat(tmp_path):
    s = _score("c4:w | c4:e c4 c4 c4 c4 c4", tempo=60)
    s.change(2, meter=Meter("6/8"))
    assert _tempos(_read(s, tmp_path)) == [(0, 1000000), (1920, 666667)]


def test_a_triplet_s_ticks(tmp_path):
    s = Score()
    s.part("a").add(Line([[_third(), _third(), _third(), Rest(Fraction(3, 4))]]))
    assert _starts(_read(s, tmp_path).tracks[1]) == [0, 160, 320]


def test_a_tie_is_one_note(tmp_path):
    s = Score()
    half = Fraction(1, 2)
    s.part("a").add(Line([[Note((C4,), half, tie=True), Note((C4,), half, tie=True)], [Note((C4,), half)]]))
    assert [note[:3] for note in _notes(_read(s, tmp_path).tracks[1])] == [(0, 2592, 60)]


def test_the_sounding_length_follows_lengths_and_articulations(tmp_path):
    s = Score(performance=Performance(lengths=Lengths(normal=0.5, tenuto=0.75, slur=1.0)))
    quarter = Fraction(1, 4)
    s.part("a").add(Line([[Note((C4,), quarter), Note((C4,), quarter, articulations=(Tenuto(),)),
                           Note((C4,), quarter, slur="start"), Note((C4,), quarter, articulations=(Staccato(0.25),))]]))
    lengths = [end - start for start, end, *_ in _notes(_read(s, tmp_path).tracks[1])]
    assert lengths == [240, 360, 480, 120]


def test_velocity_comes_from_the_dynamics(tmp_path):
    s = Score()
    s.part("a").add(melody("c4:q d4 e4 f4")).dynamic(1, 1, "f")
    assert _notes(_read(s, tmp_path).tracks[1])[0][3] == round((0.76 + 0.05) * 127)


def test_a_hairpin_moves_the_velocities(tmp_path):
    s = Score(performance=Performance(dynamics=Dynamics(stress=0)))
    s.part("a").add(melody("c4:q c4 c4 c4")).dynamic(1, 1, "p").hairpin((1, 1), (2, 1), "<").dynamic(2, 1, "f")
    velocities = [note[3] for note in _notes(_read(s, tmp_path).tracks[1])]
    assert velocities == sorted(velocities) and velocities[0] < velocities[-1]


def test_velocity_is_at_least_1(tmp_path):
    s = _score(performance=Performance(dynamics=Dynamics(levels={"mf": 0.0}, stress=0.0)))
    assert {note[3] for note in _notes(_read(s, tmp_path).tracks[1])} == {1}


def test_the_notated_file_has_no_swing_or_humanization(tmp_path):
    played = Performance(swing=Swing(2 / 3), humanize=Humanize(timing=0.02, velocity=0.1))
    a, b = _score("c4:e d4 e4 f4"), _score("c4:e d4 e4 f4", performance=played)
    assert _read(a, tmp_path).tracks[1:] == _read(b, tmp_path).tracks[1:]


def test_a_note_repeated_at_one_tick_writes_its_off_before_its_on(tmp_path):
    s = _score("c4:q c4", performance=Performance(lengths=Lengths(normal=1.0)))
    midi = _read(s, tmp_path)
    at_480 = [message.type for at, message in _timed(midi.tracks[1]) if at == 480 and message.type.startswith("note")]
    assert at_480 == ["note_off", "note_on"]
    assert [note[:2] for note in _notes(midi.tracks[1])] == [(0, 480), (480, 960)]


def test_a_note_held_over_its_own_next_start_stops_there(tmp_path):
    s = Score()
    part = s.part("a")
    part.add(Line([[Note((C4,), Fraction(1, 2))]]), voice=0)
    part.add(Line([[Rest(Fraction(1, 4)), Note((C4,), Fraction(1, 2))]]), voice=1)
    assert [note[:2] for note in _notes(_read(s, tmp_path).tracks[1])] == [(0, 480), (480, 1344)]


def test_a_unison_at_one_tick_is_one_note(tmp_path):
    s = Score()
    part = s.part("a")
    part.add(Line([[Note((C4,), Fraction(1, 4))]]), voice=0)
    part.add(Line([[Note((C4,), Fraction(1, 2))]]), voice=1)
    assert [note[:2] for note in _notes(_read(s, tmp_path).tracks[1])] == [(0, 864)]


def test_a_ramp_writes_a_tempo_event_per_sixteenth_that_keeps_the_seconds(tmp_path):
    s = _score("c4:w | c4:w | c4:w", tempo=120)
    s.ramp(2, 1, 60)
    midi = _read(s, tmp_path)
    tempos = _tempos(midi)
    ramp = [tempo for at, tempo in tempos if 1920 <= at < 3840]
    assert [at for at, _ in tempos] == [0, *range(1920, 3840, 120), 3840]
    assert ramp == sorted(ramp) and 500000 < ramp[0] < ramp[-1] < 1000000
    assert tempos[-1][1] == 1000000
    assert midi.length == pytest.approx(s.tempo_map().seconds(Fraction(3)), abs=1e-3)


def test_a_ramp_in_a_repeated_section_writes_both_passes(tmp_path):
    s = _score("c4:w", tempo=120)
    s.ramp(1, 1, 60)
    s.section("A", 1, 1, repeat=2)
    midi = _read(s, tmp_path)
    tempos = _tempos(midi)
    assert [at for at, _ in tempos] == [*range(0, 1920, 120), *range(1920, 3840, 120)]
    assert [tempo for _, tempo in tempos[:16]] == [tempo for _, tempo in tempos[16:]]


def test_both_passes_of_a_repeat_are_written(tmp_path):
    s = _score("c4:q d4 e4 f4 | g4:w | c5:w")
    s.section("A", 1, 2, repeat=2)
    midi = _read(s, tmp_path)
    assert [note[2] for note in _notes(midi.tracks[1])] == [60, 62, 64, 65, 67, 60, 62, 64, 65, 67, 72]
    assert _starts(midi.tracks[1])[5] == 3840
    assert _starts(midi.tracks[1])[-1] == 7680


def test_a_tie_out_of_a_repeat_s_last_bar_does_not_join_its_first_bar(tmp_path):
    s = Score()
    s.part("a").add(Line([[Note((C4,), Fraction(1))], [Note((C4,), Fraction(1), tie=True)], [Note((C4,), Fraction(1))]]))
    s.section("A", 1, 2, repeat=2)
    midi = _read(s, tmp_path)
    assert [note[0] for note in _notes(midi.tracks[1])] == [0, 1920, 3840, 5760]
    assert [note[1] - note[0] for note in _notes(midi.tracks[1])] == [1728, 1728, 1728, 3456]


def test_a_key_change_inside_a_repeat_is_written_again_each_pass(tmp_path):
    s = _score("c4:w | c4:w")
    s.change(2, key=Key("G major"))
    s.section("A", 1, 2, repeat=2)
    assert [(at, m.key) for at, m in _metas(_read(s, tmp_path), "key_signature")] == [
        (0, "C"), (1920, "G"), (3840, "C"), (5760, "G")]


def test_a_pickup_writes_its_short_bar_so_that_the_bars_line_up(tmp_path):
    s = Score(pickup=Fraction(1, 4))
    s.part("a").add(Line([[Note((C4,), Fraction(1, 4))], [Note((C4,), Fraction(1))]]))
    midi = _read(s, tmp_path)
    assert [(at, m.numerator, m.denominator) for at, m in _metas(midi, "time_signature")] == [(0, 1, 4), (480, 4, 4)]
    assert _starts(midi.tracks[1]) == [0, 480]


def test_a_pickup_no_signature_can_write_keeps_the_meter(tmp_path):
    s = Score(pickup=Fraction(1, 12))
    s.part("a").add(Line([[Note((C4,), Fraction(1, 12))], [Note((C4,), Fraction(1))]]))
    midi = _read(s, tmp_path)
    assert [(at, m.numerator, m.denominator) for at, m in _metas(midi, "time_signature")] == [(0, 4, 4)]
    assert _starts(midi.tracks[1]) == [0, 160]


def test_a_kit_is_on_channel_10_with_general_midi_notes(tmp_path):
    s = Score()
    s.part("drums", Kit()).add(drums({"kick": "x...", "snare": ".x..", "hihat": "..xo", "crash": "x...", "ride": ".x..",
                                      "tom1": "..x.", "tom2": "...x", "tom3": "x..."}))
    notes = _notes(_read(s, tmp_path).tracks[1])
    assert {note[4] for note in notes} == {9}
    assert sorted(note[2] for note in notes) == [36, 38, 42, 45, 46, 47, 49, 50, 51]


def test_a_part_with_hits_and_no_instrument_is_on_channel_10(tmp_path):
    s = Score()
    s.part("drums").add(drums({"kick": "x...", "hihat": "..o."}))
    notes = _notes(_read(s, tmp_path).tracks[1])
    assert [(note[2], note[4]) for note in notes] == [(36, 9), (46, 9)]


def _hit_notes(kit: Kit, name: str, tmp_path: Path) -> list[int]:
    s = Score()
    s.part("drums", kit).add(Line([[Hit(name, Fraction(1, 4))]]))
    return [note[2] for note in _notes(_read(s, tmp_path).tracks[1])]


def test_a_kit_with_a_shared_drum_writes_each_hit_by_the_name_used(tmp_path):
    tom, cymbal, hat = instruments.Tom(100.0), instruments.Crash(), instruments.HiHat()
    assert _hit_notes(Kit(toms=(tom, tom, tom)), "tom1", tmp_path) == [50]
    assert _hit_notes(Kit(toms=(tom, tom, tom, tom)), "tom1", tmp_path) == [50]
    assert _hit_notes(Kit(crash=cymbal, ride=cymbal), "crash", tmp_path) == [49]
    assert _hit_notes(Kit(crash=cymbal, ride=cymbal), "ride", tmp_path) == [51]
    assert _hit_notes(Kit(hihat=hat, crash=hat), "hihat", tmp_path) == [42]


def test_a_drum_without_a_general_midi_note_raises(tmp_path):
    s = Score()
    toms = tuple(instruments.Tom(tune) for tune in (200.0, 150.0, 100.0, 75.0))
    s.part("drums", Kit(toms=toms)).add(Line([[Hit("tom4", Fraction(1, 4))]]))
    with pytest.raises(ValueError, match="tom4"):
        s.to_midi(tmp_path / "s.mid")


def test_each_pitched_part_has_a_channel_that_skips_10_and_past_fifteen_they_share(tmp_path):
    s = Score()
    for number in range(17):
        s.part(f"p{number}").add(melody("c4:w"))
    midi = _read(s, tmp_path)
    assert [_notes(track)[0][4] for track in midi.tracks[1:]] == [*range(9), *range(10, 16), 0, 1]


def test_a_kit_takes_no_pitched_channel(tmp_path):
    s = _score()
    s.part("drums", Kit()).add(drums({"kick": "x..."}))
    s.part("b").add(melody("c4:w"))
    midi = _read(s, tmp_path)
    assert [_notes(track)[0][4] for track in midi.tracks[1:]] == [0, 9, 1]


def test_a_program_change_comes_from_the_instrument(tmp_path):
    s = Score()
    s.part("harp", Harp()).add(melody("c4:w"))
    s.part("none").add(melody("c4:w"))
    midi = _read(s, tmp_path)
    programs = [[(at, m.program, m.channel) for at, m in _timed(track) if m.type == "program_change"]
                for track in midi.tracks[1:]]
    assert programs == [[(0, 46, 0)], [(0, 0, 1)]]


def test_gm_program_defaults_to_0():
    assert Instrument.gm_program == 0
    assert Kit.gm_program == 0  # the standard kit, on channel 10


@pytest.mark.parametrize("make, program", [
    (Harp, 46), (StringSection, 48), (Violin, 40), (ElectricPiano, 4), (Organ, 16), (Celesta, 8), (Clarinet, 71),
    (Flute, 73), (BrassSection, 61), (PizzicatoStrings, 45), (Timpani, 47),
])
def test_the_presets_the_arrangements_play_have_their_program(make, program):
    assert make.gm_program == program


def test_every_preset_sets_a_program():
    bases = {"Instrument", "Kit", "Plucked", "PluckedString", "Fretted", "Electric", "Bowed", "Blown", "Patch", "Barred",
             "Struck", "Cymbal"}
    presets = [value for name, value in vars(instruments).items()
               if isinstance(value, type) and issubclass(value, Instrument) and name not in bases]
    assert len(presets) > 20
    for preset in presets:
        assert 1 <= preset.gm_program <= 127, preset.__name__


def test_a_tuned_score_writes_the_nearest_key(tmp_path):
    s = Score(tuning=JustIntonation(C4))
    s.part("a").add(Line([[Note((E4,), Fraction(1, 4)), Note((A3,), Fraction(1, 4))]]))
    assert [note[2] for note in _notes(_read(s, tmp_path).tracks[1])] == [64, 57]


def test_a_note_outside_midi_s_range_raises_naming_the_part(tmp_path):
    s = Score()
    s.part("high").add(Line([[Note((Pitch(130),), Fraction(1, 4))]]))
    with pytest.raises(ValueError, match="high"):
        s.to_midi(tmp_path / "s.mid")


def test_a_tempo_a_tempo_event_cannot_hold_raises_unless_performed(tmp_path):
    s = _score("c4:w", tempo=2)
    with pytest.raises(ValueError, match="slower"):
        s.to_midi(tmp_path / "s.mid")
    assert _tempos(_read(s, tmp_path, performed=True)) == [(0, 500000)]


def test_the_file_lasts_until_the_last_bar_ends(tmp_path):
    midi = _read(_score("c4:q r:q r:h | r:w"), tmp_path)
    assert midi.length == pytest.approx(4.0)
    assert all(_timed(track)[-1][0] == 3840 for track in midi.tracks)


def test_the_file_lasts_until_a_note_off_past_the_last_bar(tmp_path):
    s = Score(tempo=240)
    s.part("drums", Kit()).add(drums({"kick": "...............x"}))
    for performed, off in ((False, 1992), (True, 996)):
        midi = _read(s, tmp_path, performed=performed)
        assert _notes(midi.tracks[1])[0][1] == off
        assert all(_timed(track)[-1][0] == off for track in midi.tracks)


def test_a_long_delta_time_reads_back(tmp_path):
    s = Score()
    s.part("a").add(Line([*[[Rest(Fraction(1))]] * 40, [Note((C4,), Fraction(1, 4))]]))
    assert _starts(_read(s, tmp_path).tracks[1]) == [76800]


def test_performed_has_one_tempo_of_120_and_notes_at_their_seconds(tmp_path):
    s = _score("c4:q d4 e4 f4", tempo=60, performance=Performance(lengths=Lengths(normal=0.5)))
    midi = _read(s, tmp_path, performed=True)
    assert _tempos(midi) == [(0, 500000)]
    assert [note[:2] for note in _notes(midi.tracks[1])] == [(0, 480), (960, 1440), (1920, 2400), (2880, 3360)]
    assert midi.length == pytest.approx(4.0)


def test_performed_ignores_a_ramp_s_tempo_events_but_keeps_its_seconds(tmp_path):
    s = _score("c4:w | c4:w | c4:w")
    s.ramp(2, 1, 60)
    midi = _read(s, tmp_path, performed=True)
    assert _tempos(midi) == [(0, 500000)]
    assert _starts(midi.tracks[1])[2] == round(s.tempo_map().seconds(Fraction(2)) * 960)


def test_performed_has_one_time_and_key_signature(tmp_path):
    s = _score("c4:w | c4:q c4 c4", meter=Meter("4/4"), key=Key("F major"))
    s.change(2, meter=Meter("3/4"), key=Key("G major"))
    midi = _read(s, tmp_path, performed=True)
    assert [(at, m.numerator) for at, m in _metas(midi, "time_signature")] == [(0, 4)]
    assert [(at, m.key) for at, m in _metas(midi, "key_signature")] == [(0, "F")]


def test_swing_moves_the_performed_notes(tmp_path):
    s = _score("c4:e d4 e4 f4", tempo=60, performance=Performance(swing=Swing(2 / 3)))
    assert _starts(_read(s, tmp_path, performed=True).tracks[1]) == [0, 640, 960, 1600]
    assert _starts(_read(s, tmp_path).tracks[1]) == [0, 240, 480, 720]


def test_performed_humanization_is_seeded(tmp_path):
    s = _score("c4:q d4 e4 f4", performance=Performance(humanize=Humanize()))
    first = s.to_midi(tmp_path / "a.mid", performed=True).read_bytes()
    second = s.to_midi(tmp_path / "b.mid", performed=True).read_bytes()
    assert first == second
    plain = _score("c4:q d4 e4 f4").to_midi(tmp_path / "c.mid", performed=True).read_bytes()
    assert first != plain


def test_a_performed_note_on_top_of_its_repeat_stops_at_the_next_start(tmp_path):
    s = _score("c4:q c4 c4 c4", performance=Performance(lengths=Lengths(normal=1.0), humanize=Humanize(0.02, 0.0)))
    notes = _notes(_read(s, tmp_path, performed=True).tracks[1])
    assert all(end <= following[0] for (_, end, *_), following in zip(notes, notes[1:]))
