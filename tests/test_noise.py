import numpy as np
import pytest

from euterpe.sound.core import render
from euterpe.sound.noise import BrownNoise, LFSRNoise, PinkNoise, Wavetable, WhiteNoise
from tests.helpers import band_db, peak_hz


def test_noise_is_reproducible_by_seed():
    assert np.array_equal(render(WhiteNoise(seed=3), 0.1), render(WhiteNoise(seed=3), 0.1))
    assert not np.array_equal(render(WhiteNoise(seed=3), 0.1), render(WhiteNoise(seed=4), 0.1))


def test_block_size_does_not_change_noise():
    assert np.array_equal(render(WhiteNoise(seed=5), 0.1), render(WhiteNoise(seed=5), 0.1, block=77))


@pytest.mark.parametrize(
    "make",
    [
        lambda: PinkNoise(seed=2),
        lambda: BrownNoise(seed=2),
        lambda: LFSRNoise(rate=7_000.0, seed=3),
        lambda: Wavetable([0.0, 0.5, 1.0, -1.0], 331.0),
    ],
)
def test_block_size_does_not_change_the_other_sources(make):
    assert np.array_equal(render(make(), 0.3), render(make(), 0.3, block=37))
    assert np.array_equal(render(make(), 0.3), render(make(), 0.3, block=1))


def test_pink_noise_falls_3_db_per_octave():
    x = render(PinkNoise(seed=1), 10.0)
    per_octave = (band_db(x, 500, 600) - band_db(x, 4_000, 4_100)) / 3   # equal widths, three octaves apart
    assert abs(per_octave - 3.0) < 1.0


def test_brown_noise_falls_6_db_per_octave():
    x = render(BrownNoise(seed=1), 10.0)
    per_octave = (band_db(x, 500, 600) - band_db(x, 4_000, 4_100)) / 3
    assert abs(per_octave - 6.0) < 1.0


@pytest.mark.parametrize("unit", [PinkNoise, BrownNoise])
def test_coloured_noise_stays_within_full_scale_and_is_reproducible(unit):
    x = render(unit(seed=4), 10.0)
    assert np.abs(x).max() <= 1.0
    assert np.abs(x.mean()) < 0.1
    assert np.array_equal(x[:4800], render(unit(seed=4), 0.1))
    assert not np.array_equal(x[:4800], render(unit(seed=5), 0.1))


def test_lfsr_periods():
    long = render(LFSRNoise(rate=48_000.0), 1.0)
    short = render(LFSRNoise(rate=48_000.0, short=True), 0.01)
    assert np.array_equal(long[:100], long[32_767:32_867])
    assert np.array_equal(short[:50], short[127:177])


@pytest.mark.parametrize("short, period", [(False, 32_767), (True, 127)])
def test_lfsr_has_no_shorter_period(short, period):
    # a maximal-length sequence of +1 and -1 matches itself at no shift but 0: its circular
    # autocorrelation is -1 at every other shift, so it cannot repeat any sooner
    x = render(LFSRNoise(rate=48_000.0, short=short), period / 48_000).astype(np.float64)
    corr = np.rint(np.fft.irfft(np.abs(np.fft.rfft(x)) ** 2, n=period))
    assert corr[0] == period
    assert np.all(corr[1:] == -1)


def test_lfsr_noise_is_two_levels_held_for_one_step():
    x = render(LFSRNoise(rate=4_800.0), 0.1)
    assert set(np.unique(x)) == {-1.0, 1.0}
    steps = x.reshape(-1, 10)
    assert np.all(steps == steps[:, :1])


def test_lfsr_rate_out_of_range_is_refused():
    with pytest.raises(ValueError, match="rate"):
        LFSRNoise(rate=0.0)


def test_lfsr_seed_zero_is_refused():
    with pytest.raises(ValueError, match="seed"):
        LFSRNoise(rate=1_000.0, seed=0)


def test_a_wavetable_plays_at_its_frequency():
    assert abs(peak_hz(render(Wavetable(np.sin(np.linspace(0, 2 * np.pi, 32, endpoint=False)), 220.0), 2.0)) - 220.0) < 0.5


def test_a_wavetable_steps_through_its_table():
    x = render(Wavetable([0.0, 0.25, 0.5, 0.75], 12_000.0), 0.001)
    assert np.array_equal(x[:8], np.array([0.0, 0.25, 0.5, 0.75] * 2, np.float32))


def test_a_wavetable_is_silent_at_or_above_nyquist():
    assert not render(Wavetable([1.0, -1.0], 24_000.0), 0.01).any()


def test_an_empty_wavetable_is_refused():
    with pytest.raises(ValueError, match="table"):
        Wavetable([], 220.0)
