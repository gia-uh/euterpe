import numpy as np
import pytest

from euterpe.sound.core import render
from euterpe.sound.env import Segments
from euterpe.sound.filters import (
    Allpass,
    BandPass,
    Comb,
    Formant,
    HighPass,
    LowPass,
    Notch,
    OnePoleHighPass,
    OnePoleLowPass,
)
from euterpe.sound.osc import Saw, Sine
from euterpe.sound.noise import WhiteNoise
from tests.helpers import band_db


def gain_db(f, filt):
    dry = render(Sine(f), 1.0)[4_800:]
    wet = render(filt(Sine(f)), 1.0)[4_800:]
    return 20 * np.log10(np.abs(wet).max() / np.abs(dry).max())


def test_lowpass_passes_low_and_cuts_two_octaves_up_by_24_db():
    lp = lambda s: LowPass(s, cutoff=1_000.0)
    assert abs(gain_db(100.0, lp)) < 0.5 and gain_db(4_000.0, lp) < -22


def test_highpass_mirrors_it():
    hp = lambda s: HighPass(s, cutoff=1_000.0)
    assert abs(gain_db(10_000.0, hp)) < 0.5 and gain_db(250.0, hp) < -22


def test_a_comb_resonates_at_multiples_of_one_over_its_delay():
    x = render(Comb(WhiteNoise(seed=1), delay=0.001, feedback=0.9), 4.0)
    assert band_db(x, 990, 1_010) - band_db(x, 1_490, 1_510) > 15


def test_block_size_does_not_change_a_modulated_filter():
    f = lambda: LowPass(WhiteNoise(seed=2), cutoff=Sine(2.0) * 500 + 1_000)
    assert np.array_equal(render(f(), 0.5), render(f(), 0.5, block=100))


def test_formant_vowels_differ():
    a = render(Formant(WhiteNoise(seed=1), "a"), 2.0)
    i = render(Formant(WhiteNoise(seed=1), "i"), 2.0)
    assert band_db(i, 2_200, 2_400) - band_db(a, 2_200, 2_400) > 6


# Beyond the plan's tests.


def test_bandpass_keeps_its_centre_and_notch_removes_it():
    bp = lambda s: BandPass(s, cutoff=1_000.0, q=5.0)
    notch = lambda s: Notch(s, cutoff=1_000.0, q=5.0)
    assert abs(gain_db(1_000.0, bp)) < 0.5 and gain_db(4_000.0, bp) < -20
    assert gain_db(1_000.0, notch) < -30 and abs(gain_db(4_000.0, notch)) < 0.5


def test_q_raises_a_peak_at_the_cutoff():
    assert gain_db(1_000.0, lambda s: LowPass(s, cutoff=1_000.0, q=8.0)) > 17


def test_one_pole_is_3_db_down_at_its_cutoff_and_falls_6_db_per_octave():
    lp = lambda s: OnePoleLowPass(s, 500.0)
    hp = lambda s: OnePoleHighPass(s, 500.0)
    assert abs(gain_db(500.0, lp) + 3) < 0.3
    assert abs(gain_db(4_000.0, lp) - gain_db(8_000.0, lp) - 6) < 1.0
    assert abs(gain_db(10_000.0, hp)) < 0.5 and gain_db(50.0, hp) < -18


def test_one_pole_highpass_removes_a_dc_offset():
    x = render(OnePoleHighPass(Saw(110.0) + 0.5, 20.0), 2.0)
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

    y = render(LowPass(Stereo(100.0)), 0.2)
    assert y.shape == (9_600, 2) and np.abs(y[:, 1]).max() == 0 and np.abs(y[:, 0]).max() > 0.9


def test_bad_arguments_are_refused():
    with pytest.raises(ValueError, match="feedback"):
        Comb(Sine(), 0.01, 1.0)
    with pytest.raises(ValueError, match="vowel"):
        Formant(Sine(), "y")


def test_a_modulated_cutoff_moves():
    x = render(LowPass(WhiteNoise(seed=1), cutoff=Segments([(0.0, 200.0), (1.0, 8_000.0)])), 1.0)
    assert band_db(x[-9_600:], 4_000, 24_000) - band_db(x[:9_600], 4_000, 24_000) > 20


@pytest.mark.parametrize("cutoff, q", [(-100.0, 0.707), (30_000.0, 0.707), (1_000.0, 0.0), (1_000.0, -2.0)])
def test_a_cutoff_or_q_where_the_poles_would_escape_is_clipped(cutoff, q):
    x = render(LowPass(WhiteNoise(seed=1), cutoff=cutoff, q=q), 0.5)
    assert np.all(np.isfinite(x)) and np.abs(x).max() < 10


def test_a_negative_one_pole_cutoff_stays_stable():
    x = render(OnePoleLowPass(WhiteNoise(seed=1), Sine(1.0) * 1_000.0), 1.0)
    assert np.all(np.isfinite(x)) and np.abs(x).max() <= 1.0


def test_comb_and_allpass_take_numbers_only():
    with pytest.raises(TypeError, match="Comb.feedback must be a number, not a Unit"):
        Comb(Sine(), 0.01, Sine(1.0))
    with pytest.raises(TypeError, match="Allpass.delay must be a number, not a Unit"):
        Allpass(Sine(), Sine(1.0) * 0.001 + 0.002, 0.5)


def _gain_db(make, hz):
    """The level a filter gives a sine at hz, in dB against the sine itself, after it settles."""
    x = render(Sine(hz) * 0.5, 0.5)[RATE_HALF:]
    y = render(make(Sine(hz) * 0.5), 0.5)[RATE_HALF:]
    return 20 * np.log10(np.sqrt(np.mean(y.astype(np.float64) ** 2)) / np.sqrt(np.mean(x.astype(np.float64) ** 2)))


RATE_HALF = 12_000  # skip the first quarter second, while the filter settles


def test_peak_reaches_its_gain_at_cutoff():
    from euterpe.sound.filters import Peak

    assert abs(_gain_db(lambda s: Peak(s, 1000.0, gain=6.0), 1000.0) - 6.0) < 0.5
    assert abs(_gain_db(lambda s: Peak(s, 1000.0, gain=6.0), 100.0)) < 0.5
    assert abs(_gain_db(lambda s: Peak(s, 1000.0, gain=6.0), 10_000.0)) < 0.5


def test_shelves_lift_their_side():
    from euterpe.sound.filters import HighShelf, LowShelf

    assert abs(_gain_db(lambda s: LowShelf(s, 200.0, gain=6.0), 30.0) - 6.0) < 0.5
    assert abs(_gain_db(lambda s: LowShelf(s, 200.0, gain=6.0), 5000.0)) < 0.5
    assert abs(_gain_db(lambda s: HighShelf(s, 3000.0, gain=-6.0), 15_000.0) + 6.0) < 0.5
    assert abs(_gain_db(lambda s: HighShelf(s, 3000.0, gain=-6.0), 100.0)) < 0.5


def test_zero_gain_is_identity():
    from euterpe.sound.filters import HighShelf, LowShelf, Peak

    x = render(Saw(220.0) * 0.5, 0.2)
    for f in (Peak, LowShelf, HighShelf):
        assert np.max(np.abs(render(f(Saw(220.0) * 0.5, 800.0, gain=0.0), 0.2) - x)) < 1e-5


def test_a_moving_gain_renders():
    from euterpe.sound.filters import Peak

    y = render(Peak(Saw(110.0) * 0.5, 800.0, gain=Segments([(0.0, -12.0), (0.5, 12.0)])), 0.5)
    assert np.all(np.isfinite(y))


def test_ladder_falls_24_db_per_octave_above_its_cutoff():
    from euterpe.sound.filters import Ladder

    lad = lambda s: Ladder(s, 500.0)
    slope = _gain_db(lad, 4_000.0) - _gain_db(lad, 2_000.0)
    assert abs(slope + 24.0) < 2.0


def test_ladder_resonance_raises_a_peak_near_the_cutoff():
    from euterpe.sound.filters import Ladder

    lad = lambda s: Ladder(s, 1_000.0, resonance=0.9)
    peak = max(_gain_db(lad, f) for f in (800.0, 900.0, 1_000.0, 1_100.0))
    assert peak - _gain_db(lad, 100.0) > 10.0


def test_ladder_stays_stable_low_and_swept():
    from euterpe.sound.filters import Ladder

    low = render(Ladder(Saw(55.0) * 0.5, 40.0, resonance=0.99), 2.0)
    swept = render(Ladder(Saw(110.0) * 0.5, Sine(3.0) * 2_000 + 2_100, resonance=1.0), 2.0)
    for y in (low, swept):
        assert np.all(np.isfinite(y)) and np.abs(y).max() < 20


def test_ladder_does_not_depend_on_the_block_size():
    from euterpe.sound.filters import Ladder

    f = lambda: Ladder(Saw(110.0) * 0.5, Sine(2.0) * 800 + 1_000, resonance=0.8)
    assert np.array_equal(render(f(), 0.5), render(f(), 0.5, block=100))
