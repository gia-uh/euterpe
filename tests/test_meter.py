from fractions import Fraction

import pytest

from euterpe import Meter


def test_six_eight_has_two_beats_of_three_eighths():
    meter = Meter("6/8")
    assert meter.beats == 2
    assert meter.beat == Fraction(3, 8)
    assert meter.bar == Fraction(3, 4)
    assert meter.groups == (3, 3)
    assert meter.compound is True


def test_four_four_counts_one_beat_per_numerator():
    meter = Meter("4/4")
    assert (meter.beats, meter.beat, meter.bar) == (4, Fraction(1, 4), Fraction(1))
    assert meter.groups == (1, 1, 1, 1)
    assert meter.compound is False


def test_a_bar_keeps_its_written_numbers():
    assert (Meter("6/8").numerator, Meter("6/8").denominator) == (6, 8)


def test_three_eight_is_not_compound():
    assert Meter("3/8").compound is False
    assert Meter("3/8").beats == 3


@pytest.mark.parametrize("text", ["6/8", "9/8", "12/8", "6/4"])
def test_compound_is_a_numerator_divisible_by_three_and_above_it(text):
    assert Meter(text).compound is True


def test_two_two_beats_in_halves():
    assert Meter("2/2").beat == Fraction(1, 2)


def test_unequal_groups_beat_in_the_denominators_note():
    meter = Meter("7/8", groups=(2, 2, 3))
    assert meter.beats == 3
    assert meter.beat == Fraction(1, 8)
    assert meter.groups == (2, 2, 3)


def test_equal_groups_beat_in_the_groups_length():
    meter = Meter("4/4", groups=(2, 2))
    assert (meter.beats, meter.beat) == (2, Fraction(1, 2))


def test_seven_eight_without_groups_counts_each_eighth():
    assert Meter("7/8").beats == 7


def test_strength_of_four_four():
    meter = Meter("4/4")
    assert [meter.strength(Fraction(n, 4)) for n in range(4)] == [0, 2, 1, 2]
    assert meter.strength(Fraction(1, 8)) == 3
    assert meter.strength(Fraction(1, 16)) == 4


def test_strength_ranks_downbeat_over_third_beat_over_second():
    meter = Meter("4/4")
    assert meter.strength(0) < meter.strength(Fraction(1, 2)) < meter.strength(Fraction(1, 4))


def test_strength_of_six_eight():
    meter = Meter("6/8")
    assert [meter.strength(Fraction(n, 8)) for n in range(6)] == [0, 2, 2, 1, 2, 2]
    assert meter.strength(Fraction(3, 8)) < meter.strength(Fraction(1, 8))
    assert meter.strength(Fraction(1, 16)) == 3


def test_strength_of_three_four_and_seven_eight():
    assert [Meter("3/4").strength(Fraction(n, 4)) for n in range(3)] == [0, 1, 1]
    assert Meter("3/4").strength(Fraction(1, 8)) == 2
    seven = Meter("7/8", groups=(2, 2, 3))
    assert [seven.strength(Fraction(n, 8)) for n in range(7)] == [0, 2, 1, 2, 1, 2, 2]


def test_a_triplet_is_as_weak_as_the_halving_past_it():
    meter = Meter("4/4")
    assert meter.strength(Fraction(1, 12)) == meter.strength(Fraction(1, 16))


def test_an_offset_outside_the_bar_wraps_so_a_pickup_counts_from_the_end():
    meter = Meter("4/4")
    assert meter.strength(1) == 0
    assert meter.strength(Fraction(-1, 4)) == meter.strength(Fraction(3, 4))


@pytest.mark.parametrize("text", ["4", "4/", "x/4", "0/4", "4/0", "4/3", "", "4/4/4"])
def test_an_unreadable_meter_is_named(text):
    with pytest.raises(ValueError, match=repr(text)):
        Meter(text)


@pytest.mark.parametrize("groups", [(2, 2), (2, 2, 2), (7, 0), (8, -1)])
def test_groups_must_fill_the_bar(groups):
    with pytest.raises(ValueError, match="7/8"):
        Meter("7/8", groups=groups)


def test_a_meter_is_a_frozen_hashable_value():
    assert Meter("6/8") == Meter("6/8", groups=(3, 3))
    assert Meter("6/8") != Meter("3/4")
    assert hash(Meter("6/8")) == hash(Meter("6/8", groups=[3, 3]))
    with pytest.raises(AttributeError):
        Meter("6/8").groups = (6,)
