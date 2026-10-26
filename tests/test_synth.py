import numpy as np
import pytest

from euterpe.sound.core import render
from euterpe.sound.synth import Additive
from tests.helpers import band_db


def test_additive_puts_energy_where_the_partials_are():
    x = render(Additive(200.0, [(1, 1.0), (3, 0.5)]), 1.0)
    assert band_db(x, 590, 610) - band_db(x, 390, 410) > 30


def test_additive_drops_partials_at_or_above_nyquist():
    x = render(Additive(10_000.0, [(1, 1.0), (2.4, 1.0), (3, 1.0)]), 1.0)
    assert band_db(x, 9_990, 10_010) > -0.1
    # 24 000 and 30 000 Hz would fold to 24 000 and 18 000 Hz
    assert band_db(x, 17_000, 24_000) < -100


def test_additive_drops_a_modulated_partial_only_while_it_is_above_nyquist():
    from euterpe.sound.osc import Square

    freq = Square(1.0) * 4_000 + 10_000  # 14 000 Hz for half a second, then 6 000 Hz
    x = render(Additive(freq, [(1, 1.0), (2, 1.0)]), 1.0)
    first, second = x[:24_000], x[24_000:]
    assert band_db(first, 13_990, 14_010) > -0.1
    assert band_db(second, 11_990, 12_010) > -3.5


def test_additive_matches_the_saw_fourier_series():
    from euterpe.sound.osc import Saw

    partials = [(k, -2 / (np.pi * k)) for k in range(1, 110)]  # every harmonic below 24 kHz
    built, saw = render(Additive(220.0, partials), 0.1), render(Saw(220.0), 0.1)
    assert np.abs(built - saw)[200:-200].mean() < 0.02


def test_additive_is_the_same_in_any_block_size():
    unit = Additive(331.0, [(1, 0.5), (2.01, 0.25), (5.3, 0.1)])
    assert np.array_equal(render(unit, 0.5), render(unit, 0.5, block=37))


def test_additive_with_a_modulated_freq_is_the_same_in_any_block_size():
    from euterpe.sound.osc import Sine

    unit = Additive(Sine(3.0) * 300 + 500, [(1, 0.5), (2.01, 0.25), (5.3, 0.1)])
    whole = render(unit, 0.5)
    assert np.array_equal(whole, render(unit, 0.5, block=1))
    assert np.array_equal(whole, render(unit, 0.5, block=37))


def test_additive_refuses_a_partial_with_ratio_zero_or_below():
    with pytest.raises(ValueError, match="ratio"):
        Additive(200.0, [(1, 1.0), (0, 0.5)])


@pytest.mark.parametrize("ratio", [np.nan, np.inf])
def test_additive_refuses_a_ratio_that_is_not_finite(ratio):
    with pytest.raises(ValueError, match="ratio"):
        Additive(200.0, [(1, 1.0), (ratio, 0.5)])


def test_additive_refuses_a_frequency_out_of_range():
    with pytest.raises(ValueError, match="freq"):
        Additive(-5.0, [(1, 1.0)])
