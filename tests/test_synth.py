import numpy as np
import pytest

from euterpe.sound.core import render
from euterpe.sound.noise import WhiteNoise
from euterpe.sound.synth import FM, Additive, Modal, Pluck
from tests.helpers import band_db, peak_hz


def cents(a, b):
    return 1200 * np.log2(a / b)


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

    # partial 2 crosses 24 000 Hz six times a second, so a mask set per block would show here
    unit = Additive(Sine(3.0) * 4_000 + 10_000, [(1, 0.5), (2, 0.25)])
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


@pytest.mark.parametrize("amp", [np.nan, np.inf])
def test_additive_refuses_an_amplitude_that_is_not_finite(amp):
    with pytest.raises(ValueError, match="amplitude"):
        Additive(200.0, [(1, 1.0), (2, amp)])


def test_additive_refuses_a_frequency_out_of_range():
    with pytest.raises(ValueError, match="freq"):
        Additive(-5.0, [(1, 1.0)])


def test_a_pluck_is_in_tune_and_decays():
    x = render(Pluck(220.0, seed=1), 2.0)
    assert abs(cents(peak_hz(x[:48_000]), 220.0)) < 5
    assert np.abs(x[-4_800:]).max() < 0.25 * np.abs(x[:4_800]).max()


@pytest.mark.parametrize("freq", [82.41, 329.63, 1_046.5, 3_000.0])
def test_a_pluck_is_in_tune_across_the_range(freq):
    x = render(Pluck(freq, damping=0.999, brightness=0.1, seed=2), 1.0)  # dark: the fundamental is loudest
    assert abs(cents(peak_hz(x), freq)) < 5


def test_pluck_damping_out_of_range_is_refused():
    with pytest.raises(ValueError, match="damping"):
        Pluck(220.0, damping=1.2)


def test_pluck_refuses_a_moving_parameter():
    from euterpe.sound.osc import Sine

    with pytest.raises(TypeError, match="freq"):
        Pluck(Sine(1.0) * 10 + 220)


def test_a_pluck_is_the_same_in_any_block_size_and_by_seed():
    unit = Pluck(196.0, brightness=0.3, position=0.2, seed=4)
    whole = render(unit, 0.5)
    assert np.array_equal(whole, render(unit, 0.5, block=37))
    assert np.array_equal(whole, render(unit, 0.5, block=1))
    assert not np.array_equal(whole, render(Pluck(196.0, brightness=0.3, position=0.2, seed=5), 0.5))


def test_more_damping_rings_longer():
    short, long = render(Pluck(220.0, damping=0.98, seed=1), 1.0), render(Pluck(220.0, damping=0.999, seed=1), 1.0)
    assert np.abs(long[-4_800:]).max() > 10 * np.abs(short[-4_800:]).max()


def test_a_darker_pluck_has_less_energy_up_high():
    dark, bright = render(Pluck(220.0, brightness=0.1, seed=1), 0.5), render(Pluck(220.0, brightness=0.9, seed=1), 0.5)
    assert band_db(bright, 4_000, 8_000) - band_db(bright, 200, 240) > band_db(dark, 4_000, 8_000) - band_db(dark, 200, 240) + 10


def test_plucking_in_the_middle_removes_the_even_harmonics():
    x = render(Pluck(220.0, damping=0.999, brightness=1.0, position=0.5, seed=1), 0.5)
    assert band_db(x, 430, 450) < band_db(x, 650, 670) - 15


def test_a_pluck_stays_below_full_scale_with_no_offset():
    x = render(Pluck(110.0, brightness=1.0, seed=3), 2.0)
    assert np.abs(x).max() <= 1.0
    assert abs(float(x.mean())) < 1e-3


def test_fm_index_zero_is_a_sine_and_index_up_adds_sidebands():
    plain, rich = render(FM(440.0, index=0.0), 1.0), render(FM(440.0, ratio=1.0, index=3.0), 1.0)
    assert band_db(plain, 870, 890) < -60 + band_db(plain, 430, 450)
    assert band_db(rich, 870, 890) > band_db(plain, 870, 890) + 30


def test_fm_sidebands_sit_at_the_carrier_plus_and_minus_the_modulator():
    x = render(FM(1_000.0, ratio=0.3, index=1.0), 1.0)
    for f in (700, 1_300, 400, 1_600):
        assert band_db(x, f - 10, f + 10) > band_db(x, f + 140, f + 160) + 30


def test_fm_with_feedback_adds_harmonics_and_is_the_same_in_any_block_size():
    plain = render(FM(220.0, index=1.0, feedback=0.0), 0.5)
    fed = render(FM(220.0, index=1.0, feedback=1.0), 0.5)
    assert band_db(fed, 1_090, 1_110) > band_db(plain, 1_090, 1_110) + 10
    unit = FM(220.0, index=1.0, feedback=1.0)
    assert np.array_equal(render(unit, 0.2), render(unit, 0.2, block=37))


def test_fm_with_a_moving_index_is_the_same_in_any_block_size():
    from euterpe.sound.env import ADSR

    unit = FM(330.0, ratio=2.0, index=ADSR(attack=0.0, decay=0.3, sustain=0.0, gate=1.0) * 8)
    assert np.array_equal(render(unit, 0.3), render(unit, 0.3, block=37))


def test_fm_at_or_above_nyquist_is_silent():
    assert not render(FM(24_000.0, index=2.0), 0.01).any()


def test_fm_index_out_of_range_is_refused():
    with pytest.raises(ValueError, match="index"):
        FM(440.0, index=25.0)


def test_modal_rings_at_its_modes():
    x = render(Modal([500.0, 1_370.0], [1.0, 0.5], [1.0, 0.5]), 2.0)
    assert band_db(x, 1_360, 1_380) - band_db(x, 900, 920) > 20


def test_a_mode_falls_60_db_in_its_decay_time():
    x = render(Modal([1_000.0], [0.5], [1.0]), 0.6)
    start, later = np.abs(x[:480]).max(), np.abs(x[23_760:24_240]).max()  # around 0 s and 0.5 s
    assert abs(20 * np.log10(later / start) + 60) < 1.5


def test_modal_takes_an_excitation_and_is_the_same_in_any_block_size():
    from euterpe.sound.env import ADSR

    def unit():
        return Modal([300.0, 810.0], [0.8, 0.3], [1.0, 0.4], excite=WhiteNoise(seed=1) * ADSR(attack=0.0, decay=0.01, sustain=0.0, gate=0.01))

    x = render(unit(), 0.5)
    assert np.array_equal(x, render(unit(), 0.5, block=37))
    assert abs(peak_hz(x) - 300.0) < 2


def test_modal_drops_modes_at_or_above_nyquist():
    x = render(Modal([1_000.0, 30_000.0], [1.0, 1.0], [1.0, 1.0]), 0.5)
    assert band_db(x, 17_000, 19_000) < -100


def test_modal_refuses_lists_of_different_lengths():
    with pytest.raises(ValueError, match="same length"):
        Modal([500.0, 700.0], [1.0], [1.0, 0.5])


def test_modal_refuses_a_decay_of_zero_or_below():
    with pytest.raises(ValueError, match="decay"):
        Modal([500.0], [0.0], [1.0])


def test_brightness_and_position_do_not_change_the_energy_of_the_burst():
    def energy(**kw):
        x = render(Pluck(220.0, seed=1, **kw), 200 / 48_000)  # the burst, before its first trip
        return 10 * np.log10((x.astype(np.float64) ** 2).mean())

    levels = [energy(brightness=b) for b in (0.0, 0.5, 1.0)] + [energy(position=p) for p in (0.1, 0.5)]
    assert max(levels) - min(levels) < 1.5
