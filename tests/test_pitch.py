import euterpe.pitch
import numpy as np
import pytest
from euterpe.instruments import Harp, Note
from euterpe.instruments.core import outside
from euterpe.pitch import A0, A4, A5, B3, Bb2, C4, C8, Cs4, D4, Db4, Ds4, E4, E5, Eb4, F4, Interval, Pitch


def test_a4_is_440():
    assert A4.freq == 440.0 and A4.number == 69 and C4.number == 60


def test_semitone_arithmetic():
    assert A4 + 12 == A5 and A4 + 7 == E5 and A5 - 12 == A4 and E5 - A4 == 7
    assert E5.freq == pytest.approx(659.2551, abs=1e-3)


def test_sharp_and_flat_are_two_spellings_of_one_sound():
    assert Cs4 != Db4 and hash(Cs4) != hash(Db4) and Cs4.sounds_as(Db4) and not Cs4.sounds_as(D4)
    assert Cs4.number == Db4.number and Cs4.freq == Db4.freq
    assert repr(Db4) == "Db4" and repr(Cs4) == "C#4" and repr(Bb2) == "Bb2"


def test_range_and_order():
    assert A0.number == 21 and C8.number == 108 and A0 < C4 < C8
    assert Pitch(60) == C4 and C4 < D4
    assert sorted([Db4, Cs4]) == [Cs4, Db4]
    assert sorted([D4, Db4, Cs4, C4]) == [C4, Cs4, Db4, D4]


CONSTANTS = {
    "A0": 21, "As0": 22, "Bb0": 22, "B0": 23, "C1": 24, "Cs1": 25, "Db1": 25, "D1": 26, "Ds1": 27, "Eb1": 27,
    "E1": 28, "F1": 29, "Fs1": 30, "Gb1": 30, "G1": 31, "Gs1": 32, "Ab1": 32, "A1": 33, "As1": 34, "Bb1": 34,
    "B1": 35, "C2": 36, "Cs2": 37, "Db2": 37, "D2": 38, "Ds2": 39, "Eb2": 39, "E2": 40, "F2": 41, "Fs2": 42,
    "Gb2": 42, "G2": 43, "Gs2": 44, "Ab2": 44, "A2": 45, "As2": 46, "Bb2": 46, "B2": 47, "C3": 48, "Cs3": 49,
    "Db3": 49, "D3": 50, "Ds3": 51, "Eb3": 51, "E3": 52, "F3": 53, "Fs3": 54, "Gb3": 54, "G3": 55, "Gs3": 56,
    "Ab3": 56, "A3": 57, "As3": 58, "Bb3": 58, "B3": 59, "C4": 60, "Cs4": 61, "Db4": 61, "D4": 62, "Ds4": 63,
    "Eb4": 63, "E4": 64, "F4": 65, "Fs4": 66, "Gb4": 66, "G4": 67, "Gs4": 68, "Ab4": 68, "A4": 69, "As4": 70,
    "Bb4": 70, "B4": 71, "C5": 72, "Cs5": 73, "Db5": 73, "D5": 74, "Ds5": 75, "Eb5": 75, "E5": 76, "F5": 77,
    "Fs5": 78, "Gb5": 78, "G5": 79, "Gs5": 80, "Ab5": 80, "A5": 81, "As5": 82, "Bb5": 82, "B5": 83, "C6": 84,
    "Cs6": 85, "Db6": 85, "D6": 86, "Ds6": 87, "Eb6": 87, "E6": 88, "F6": 89, "Fs6": 90, "Gb6": 90, "G6": 91,
    "Gs6": 92, "Ab6": 92, "A6": 93, "As6": 94, "Bb6": 94, "B6": 95, "C7": 96, "Cs7": 97, "Db7": 97, "D7": 98,
    "Ds7": 99, "Eb7": 99, "E7": 100, "F7": 101, "Fs7": 102, "Gb7": 102, "G7": 103, "Gs7": 104, "Ab7": 104,
    "A7": 105, "As7": 106, "Bb7": 106, "B7": 107, "C8": 108,
}


def test_every_constant_keeps_its_number_and_freq():
    found = {name for name, value in vars(euterpe.pitch).items() if isinstance(value, Pitch)}
    assert found == set(CONSTANTS)
    for name, number in CONSTANTS.items():
        pitch = getattr(euterpe.pitch, name)
        assert pitch.number == number, name
        assert pitch.freq == 440 * 2 ** ((number - 69) / 12), name


@pytest.mark.parametrize("text, letter, alter, octave, number", [
    ("C#4", "C", 1, 4, 61), ("Bb4", "B", -1, 4, 70), ("F##4", "F", 2, 4, 67), ("Ebb4", "E", -2, 4, 62),
    ("B#3", "B", 1, 3, 60), ("Cb4", "C", -1, 4, 59), ("C-1", "C", 0, -1, 0), ("A4", "A", 0, 4, 69),
])
def test_text_reads_letter_alter_octave_and_number(text, letter, alter, octave, number):
    p = Pitch(text)
    assert (p.letter, p.alter, p.octave, p.number) == (letter, alter, octave, number)
    assert p == Pitch(letter, alter, octave) and str(p) == repr(p) == text


def test_a_number_spells_with_sharps():
    assert Pitch(61) == Pitch("C#4") and Pitch(61) == Cs4 and Pitch(70) == Pitch("A#4")
    assert Pitch(np.int64(60)) == C4 and type(Pitch(np.int64(60)).number) is int
    assert Db4 + 2 == Ds4 and Eb4 - 2 == Cs4 and Eb4 + 0 == Ds4 and C4 + np.int64(1) == Cs4


def test_pitch_a4_and_pitch_class():
    assert Pitch("A4").freq == 440 and Pitch("Db6").pitch_class == 1 and Pitch("B#3").pitch_class == 0


def test_pretty():
    assert Pitch("C#4").pretty == "C♯4" and Pitch("Cb4").pretty == "C♭4" and A4.pretty == "A4"
    assert Pitch("F##4").pretty == "F♯♯4" and Pitch("Ebb4").pretty == "E♭♭4"


def test_difference_of_pitches_is_semitones():
    assert E5 - A4 == 7 and Cs4 - Db4 == 0 and Pitch("B#3") - C4 == 0


@pytest.mark.parametrize("bad", ["H4", "C", "4", "", "C###4", "Cbbb4", "C#b4", "c4", "C4.5", 60.5])
def test_pitch_names_what_it_cannot_read(bad):
    with pytest.raises(ValueError, match=str(bad).replace(".", r"\.") or "Pitch"):
        Pitch(bad)


@pytest.mark.parametrize("args, named", [(("C", 3, 4), "C###4"), (("C", -3, 4), "Cbbb4"), (("H", 0, 4), "H4")])
def test_pitch_parts_out_of_range_name_the_note(args, named):
    with pytest.raises(ValueError, match=named):
        Pitch(*args)


def test_one_or_two_parts_is_not_a_pitch():
    with pytest.raises(ValueError, match="C"):
        Pitch("C", 1)


def test_altering_past_two_names_the_note():
    with pytest.raises(ValueError, match="F###4"):
        Pitch("F##4") + Interval("A1")


def test_resource_stays_a_number_whatever_the_spelling():
    harp = Harp()
    for pitch in (C4, Cs4, Db4, Pitch(np.int64(60)), C4 + np.int64(1)):
        assert type(harp.resource(Note(0.0, pitch, 0.1))) is int


def test_range_checks_read_the_sound_not_the_spelling():
    assert outside(Cs4, (Db4, E4)) is None and outside(Db4, (C4, Cs4)) is None
    assert outside(C4, (Db4, E4)) == "below the bottom"


@pytest.mark.parametrize("start, interval, end", [
    (C4, "M3", E4), (C4, "A2", Ds4), (C4, "m3", Eb4), (C4, "-m2", B3), (C4, "P8", Pitch("C5")),
    (C4, "M10", Pitch("E5")), (C4, "A1", Cs4), (C4, "-A1", Pitch("Cb4")), (C4, "d1", Pitch("Cb4")),
    (Pitch("B3"), "m2", C4), (Pitch("E4"), "A3", Pitch("G##4")), (Pitch("F#4"), "m2", Pitch("G4")),
])
def test_adding_an_interval_moves_the_letter(start, interval, end):
    assert start + Interval(interval) == end


def test_subtracting_an_interval():
    assert E4 - Interval("M3") == C4 and C4 - Interval("m2") == B3 and C4 - Interval("-M3") == E4


def test_interval_text_and_parts():
    i = Interval("M3")
    assert (i.quality, i.number, i.semitones) == ("M", 3, 4) and str(i) == repr(i) == "M3"
    d = Interval("-P5")
    assert (d.quality, d.number, d.semitones) == ("P", -5, -7) and str(d) == repr(d) == "-P5"
    assert Interval("m", 10) == Interval("m10") and Interval("P", -5) == d
    assert hash(Interval("m", 10)) == hash(Interval("m10"))


@pytest.mark.parametrize("text, semitones", [
    ("P1", 0), ("m2", 1), ("M2", 2), ("m3", 3), ("M3", 4), ("P4", 5), ("A4", 6), ("d5", 6), ("P5", 7), ("m6", 8),
    ("M6", 9), ("d7", 9), ("m7", 10), ("M7", 11), ("P8", 12), ("m9", 13), ("M10", 16), ("P15", 24), ("dd5", 5),
    ("AA4", 7), ("d2", 0), ("dd2", -1), ("A1", 1), ("d1", -1), ("-M3", -4), ("AAAA4", 9),
])
def test_semitones(text, semitones):
    assert Interval(text).semitones == semitones


@pytest.mark.parametrize("bad", ["M5", "-M5", "P3", "m4", "P2", "M1", "M0", "x3", "", "M", "3", "Pd5", "- M3"])
def test_interval_names_what_it_cannot_read(bad):
    with pytest.raises(ValueError, match=bad or "Interval"):
        Interval(bad)


@pytest.mark.parametrize("quality, number", [("M", 5), ("P", 3), ("Q", 3), ("P", 0)])
def test_interval_parts_it_cannot_build(quality, number):
    with pytest.raises(ValueError, match=f"{quality}{number}"):
        Interval(quality, number)


@pytest.mark.parametrize("p, q, interval", [
    (C4, Pitch("E#4"), "A3"), (C4, F4, "P4"), (C4, B3, "-m2"), (C4, C4, "P1"), (C4, Cs4, "A1"),
    (C4, Pitch("Cb4"), "-A1"), (C4, Pitch("E5"), "M10"), (A4, C4, "-M6"), (Cs4, Db4, "d2"),
    (Pitch("B#3"), Pitch("Cb4"), "dd2"), (Pitch("Cbb4"), Pitch("F##4"), "AAAA4"),
    (Pitch("F##4"), Pitch("Cbb4"), "-AAAA4"),
    (Pitch("Fbb4"), Pitch("B##4"), "AAAAA4"), (Pitch("B##4"), Pitch("Fbb5"), "ddddd5"),
])
def test_between_reads_letters_then_semitones(p, q, interval):
    i = Interval.between(p, q)
    assert i == Interval(interval)
    assert i.semitones == q - p and p + i == q


def test_simple():
    assert Interval("M10").simple == Interval("M3") and Interval("-M10").simple == Interval("-M3")
    assert Interval("P8").simple == Interval("P8") and Interval("P15").simple == Interval("P8")
    assert Interval("m9").simple == Interval("m2") and Interval("M3").simple == Interval("M3")


@pytest.mark.parametrize("text, inverted", [
    ("M3", "m6"), ("m6", "M3"), ("A4", "d5"), ("d5", "A4"), ("P1", "P8"), ("P8", "P1"), ("P4", "P5"), ("M2", "m7"),
    ("AA4", "dd5"), ("A1", "d8"), ("A8", "d1"), ("M10", "m6"), ("-M3", "-m6"),
])
def test_inverted(text, inverted):
    assert Interval(text).inverted == Interval(inverted)


@pytest.mark.parametrize("text", ["P1", "m2", "M2", "m3", "M3", "P4", "A4", "d5", "P5", "m6", "M6", "m7", "M7", "P8"])
def test_an_interval_and_its_inversion_fill_an_octave(text):
    i = Interval(text)
    assert i + i.inverted == Interval("P8")


def test_addition_and_negation():
    assert Interval("m3") + Interval("M3") == Interval("P5") and Interval("P5") + Interval("P4") == Interval("P8")
    assert Interval("M3") + Interval("-M3") == Interval("P1") and Interval("M2") + Interval("-M3") == Interval("-M2")
    assert -Interval("M3") == Interval("-M3") and -Interval("-M3") == Interval("M3")
    assert -Interval("P1") == Interval("P1") == Interval("-P1")


@pytest.mark.parametrize("text, kind", [
    ("P1", "perfect"), ("P4", "perfect"), ("P5", "perfect"), ("P8", "perfect"), ("P15", "perfect"), ("-P5", "perfect"),
    ("m3", "imperfect"), ("M3", "imperfect"), ("m6", "imperfect"), ("M6", "imperfect"), ("M10", "imperfect"),
    ("m2", "dissonant"), ("M2", "dissonant"), ("m7", "dissonant"), ("M7", "dissonant"), ("A4", "dissonant"),
    ("d5", "dissonant"), ("A1", "dissonant"), ("A3", "dissonant"), ("M9", "dissonant"),
])
def test_consonance(text, kind):
    assert Interval(text).consonance == kind


@pytest.mark.parametrize("text, pretty", [
    ("M3", "major third"), ("P1", "perfect unison"), ("P8", "perfect octave"), ("m10", "minor tenth"),
    ("-P5", "descending perfect fifth"), ("A4", "augmented fourth"), ("dd5", "doubly diminished fifth"),
    ("AAA4", "3x augmented fourth"), ("P22", "perfect 22nd"),
])
def test_interval_pretty(text, pretty):
    assert Interval(text).pretty == pretty
