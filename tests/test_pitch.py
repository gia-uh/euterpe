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
