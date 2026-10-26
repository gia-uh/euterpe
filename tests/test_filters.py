import numpy as np
import pytest

from euterpe.sound.core import render
from euterpe.sound.filters import Biquad, Comb, Formant
from euterpe.sound.osc import Sine
from euterpe.sound.noise import WhiteNoise
from tests.helpers import band_db


def gain_db(f, filt):
    dry = render(Sine(f), 1.0)[4_800:]
    wet = render(filt(Sine(f)), 1.0)[4_800:]
    return 20 * np.log10(np.abs(wet).max() / np.abs(dry).max())


def test_lowpass_passes_low_and_cuts_two_octaves_up_by_24_db():
    lp = lambda s: Biquad(s, "lowpass", cutoff=1_000.0)
    assert abs(gain_db(100.0, lp)) < 0.5 and gain_db(4_000.0, lp) < -22


def test_highpass_mirrors_it():
    hp = lambda s: Biquad(s, "highpass", cutoff=1_000.0)
    assert abs(gain_db(10_000.0, hp)) < 0.5 and gain_db(250.0, hp) < -22


def test_a_comb_resonates_at_multiples_of_one_over_its_delay():
    x = render(Comb(WhiteNoise(seed=1), delay=0.001, feedback=0.9), 4.0)
    assert band_db(x, 990, 1_010) - band_db(x, 1_490, 1_510) > 15


def test_block_size_does_not_change_a_modulated_filter():
    f = lambda: Biquad(WhiteNoise(seed=2), "lowpass", cutoff=Sine(2.0) * 500 + 1_000)
    assert np.array_equal(render(f(), 0.5), render(f(), 0.5, block=100))


def test_formant_vowels_differ():
    a = render(Formant(WhiteNoise(seed=1), "a"), 2.0)
    i = render(Formant(WhiteNoise(seed=1), "i"), 2.0)
    assert band_db(i, 2_200, 2_400) - band_db(a, 2_200, 2_400) > 6


# Beyond the plan's tests.

from euterpe.sound.filters import Allpass, OnePole  # noqa: E402
from euterpe.sound.osc import Saw  # noqa: E402


def test_bandpass_keeps_its_centre_and_notch_removes_it():
    bp = lambda s: Biquad(s, "bandpass", cutoff=1_000.0, q=5.0)
    notch = lambda s: Biquad(s, "notch", cutoff=1_000.0, q=5.0)
    assert abs(gain_db(1_000.0, bp)) < 0.5 and gain_db(4_000.0, bp) < -20
    assert gain_db(1_000.0, notch) < -30 and abs(gain_db(4_000.0, notch)) < 0.5


def test_q_raises_a_peak_at_the_cutoff():
    assert gain_db(1_000.0, lambda s: Biquad(s, "lowpass", cutoff=1_000.0, q=8.0)) > 17


def test_one_pole_is_3_db_down_at_its_cutoff_and_falls_6_db_per_octave():
    lp = lambda s: OnePole(s, 500.0)
    hp = lambda s: OnePole(s, 500.0, kind="highpass")
    assert abs(gain_db(500.0, lp) + 3) < 0.3
    assert abs(gain_db(4_000.0, lp) - gain_db(8_000.0, lp) - 6) < 1.0
    assert abs(gain_db(10_000.0, hp)) < 0.5 and gain_db(50.0, hp) < -18


def test_one_pole_highpass_removes_a_dc_offset():
    x = render(OnePole(Saw(110.0) + 0.5, 20.0, kind="highpass"), 2.0)
    assert abs(x[48_000:].mean()) < 1e-3


def test_an_allpass_keeps_every_level():
    for f in (200.0, 1_000.0, 5_000.0):
        assert abs(gain_db(f, lambda s: Allpass(s, delay=0.003, gain=0.7))) < 0.1


def test_comb_and_allpass_do_not_depend_on_the_block_size():
    for f in (lambda: Comb(WhiteNoise(seed=3), 0.002, 0.8), lambda: Allpass(WhiteNoise(seed=3), 0.0021, 0.5)):
        assert np.array_equal(render(f(), 0.3), render(f(), 0.3, block=37))


def test_a_stereo_source_is_filtered_per_channel():
    class Stereo(Sine):
        channels = 2

        def block(self, n):
            x = super().block(n)
            return np.stack([x, np.zeros_like(x)], axis=1)

    y = render(Biquad(Stereo(100.0), "lowpass"), 0.2)
    assert y.shape == (9_600, 2) and np.abs(y[:, 1]).max() == 0 and np.abs(y[:, 0]).max() > 0.9


def test_bad_arguments_are_refused():
    with pytest.raises(ValueError, match="kind"):
        Biquad(Sine(), "shelf")
    with pytest.raises(ValueError, match="q"):
        Biquad(Sine(), "lowpass", q=0.0)
    with pytest.raises(ValueError, match="feedback"):
        Comb(Sine(), 0.01, 1.0)
    with pytest.raises(ValueError, match="vowel"):
        Formant(Sine(), "y")
