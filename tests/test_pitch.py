import euterpe.pitch
import pytest
from euterpe.pitch import A0, A4, A5, Bb2, C4, C8, Cs4, Db4, E5, Pitch


def test_a4_is_440():
    assert A4.freq == 440.0 and A4.number == 69 and C4.number == 60


def test_semitone_arithmetic():
    assert A4 + 12 == A5 and A4 + 7 == E5 and A5 - 12 == A4 and E5 - A4 == 7
    assert E5.freq == pytest.approx(659.2551, abs=1e-3)


def test_sharp_and_flat_name_one_pitch():
    assert Cs4 == Db4 and hash(Cs4) == hash(Db4) and repr(Db4) == "Cs4" and repr(Bb2) == "As2"


def test_range_and_order():
    assert A0.number == 21 and C8.number == 108 and A0 < C4 < C8
    assert Pitch(60) == C4


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
