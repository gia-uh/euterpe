import numpy as np
import pytest

from euterpe.sound.core import Const, Unit, render
from euterpe.sound.env import Segments
from euterpe.sound.noise import WhiteNoise
from euterpe.sound.osc import Sine
from euterpe.sound.shape import BitCrush, Compressor, Gate, HardClip, Limiter, Saturator, SoftClip, Tanh
from tests.helpers import band_db


def test_more_drive_more_harmonics():
    soft = render(Tanh(Sine(200.0), drive=1.5), 1.0)
    hard = render(Tanh(Sine(200.0), drive=20.0), 1.0)
    assert band_db(hard, 590, 610) > band_db(soft, 590, 610) + 10
    assert np.abs(hard).max() < 1.0


@pytest.mark.parametrize("shaper", [Tanh, SoftClip, HardClip])
def test_shaper_is_odd_and_below_full_scale(shaper):
    x = render(shaper(Sine(200.0), drive=8.0), 1.0)
    assert np.abs(x).max() < 1.0
    assert band_db(x, 390, 410) < -80   # a symmetric curve adds odd harmonics only
    assert band_db(x, 590, 610) > -40


@pytest.mark.parametrize("shaper", [Tanh, SoftClip, HardClip, Saturator])
def test_a_drive_of_zero_or_below_stays_finite(shaper):
    x = render(shaper(Sine(200.0), drive=Sine(1.0) * 2.0), 1.0)
    assert np.all(np.isfinite(x)) and np.abs(x).max() < 1.0


def test_saturator_adds_even_harmonics():
    assert band_db(render(Saturator(Sine(200.0)), 1.0), 390, 410) > -40


@pytest.mark.parametrize("drive, bias", [(2.0, 0.1), (1.0, 0.1), (4.0, 0.2), (10.0, 0.5), (30.0, 1.0)])
def test_saturator_puts_a_full_scale_sine_at_minus_1_dbfs(drive, bias):
    x = render(Saturator(Sine(220.0), drive=drive, bias=bias), 2.0)[48_000:]
    assert abs(20 * np.log10(np.abs(x).max()) + 1.0) < 0.5


def test_saturator_keeps_silence_silent():
    assert np.abs(render(Saturator(Const(0.0), drive=10.0, bias=0.5), 0.1)).max() == 0.0


def test_saturator_has_no_dc():
    x = render(Saturator(Sine(200.0), drive=10.0, bias=0.5), 2.0)
    assert abs(x[48_000:].mean()) < 1e-3


def test_compressor_reduces_a_loud_sine_by_the_ratio():
    x = render(Compressor(Sine(440.0) * 1.0, threshold=-20.0, ratio=4.0, attack=0.001), 1.0)
    rms_db = 20 * np.log10(np.sqrt(np.mean(x[24_000:] ** 2)))
    assert abs(rms_db - (-20 + (-3 + 20) / 4)) < 1.0   # a full-scale sine is -3 dB RMS


def test_compressor_leaves_a_quiet_sine_alone_and_adds_makeup():
    x = render(Compressor(Sine(440.0) * 0.01, threshold=-20.0, makeup=6.0), 1.0)
    assert abs(np.abs(x[24_000:]).max() - 0.01 * 10 ** (6 / 20)) < 1e-3


def _step():
    return Sine(1000.0) * Segments([(0.0, 0.05), (0.5, 0.05), (0.5, 1.0), (1.0, 1.0)])


def _db_after_step(x, ms):
    """RMS in dB over the 5 ms that start ms milliseconds after the step at 0.5 s."""
    start = 24_000 + ms * 48
    return 20 * np.log10(np.sqrt(np.mean(x[start : start + 240] ** 2)))


def test_compressor_attack_sets_how_fast_the_gain_comes_down():
    target = -20 + (-3 + 20) / 4
    fast = render(Compressor(_step(), threshold=-20.0, ratio=4.0, attack=0.002), 1.0)
    slow = render(Compressor(_step(), threshold=-20.0, ratio=4.0, attack=0.05), 1.0)
    assert abs(_db_after_step(fast, 20) - target) < 1.0
    assert _db_after_step(slow, 20) - target > 3.0


def test_gate_opens_within_3_ms():
    tone = Sine(1000.0) * Segments([(0.0, 0.0), (0.1, 0.0), (0.1, 0.5), (0.3, 0.5)])
    x = render(Gate(tone, threshold=-40.0, release=0.2), 0.3)
    assert np.abs(x[4_800 + 144 : 4_800 + 192]).max() > 0.9 * 0.5


def test_limiter_never_passes_its_ceiling():
    x = render(Limiter(Sine(440.0) * 4.0, ceiling=-1.0), 1.0)
    assert 20 * np.log10(np.abs(x).max()) <= -1.0 + 0.01


def test_limiter_ceiling_must_be_a_number():
    with pytest.raises(TypeError):
        Limiter(Sine(440.0), ceiling=Sine(2.0) * 20 - 20)


def test_limiter_delays_by_its_lookahead():
    x = render(Limiter(Sine(440.0) * 0.1), 0.1)
    y = render(Sine(440.0) * 0.1, 0.1)
    assert np.allclose(x[240:], y[:-240], atol=1e-6) and np.abs(x[:240]).max() == 0.0


def test_gate_silences_quiet_noise_and_passes_a_tone():
    quiet = render(Gate(WhiteNoise(seed=1) * 0.001, threshold=-50.0), 1.0)
    loud = render(Gate(Sine(440.0) * 0.5, threshold=-50.0), 1.0)
    assert np.abs(quiet[24_000:]).max() < 1e-5
    assert abs(np.abs(loud[24_000:]).max() - 0.5) < 1e-3


@pytest.mark.parametrize(
    "make",
    [
        lambda: SoftClip(Sine(200.0), drive=Sine(1.0) * 4 + 5),
        lambda: Saturator(Sine(200.0), drive=Sine(1.0) + 3),
        lambda: Compressor(Sine(110.0) * (Sine(2.0) * 0.5 + 0.5), threshold=-24.0, attack=0.003),
        lambda: Limiter(Sine(110.0) * (Sine(2.0) * 2 + 2.5), release=0.02),
        lambda: Gate(Sine(110.0) * Sine(1.5), threshold=-20.0),
    ],
)
def test_block_size_does_not_change_the_samples(make):
    assert np.array_equal(render(make(), 1.0), render(make(), 1.0, block=37))


class Stereo(Unit):
    """A 220 Hz sine on the left and a quieter 330 Hz sine on the right."""

    channels = 2

    def __init__(self):
        self.left, self.right = Sine(220.0), Sine(330.0)

    def inputs(self):
        return [self.left, self.right]

    def block(self, n):
        return np.stack([self.left.block(n), self.right.block(n) * 0.25], axis=1)


@pytest.mark.parametrize(
    "make",
    [lambda s: Tanh(s, drive=4.0), Saturator, Compressor, Limiter, Gate],
)
def test_stereo_in_stereo_out(make):
    x = render(make(Stereo()), 0.2)
    assert x.shape == (9_600, 2) and np.abs(x[:, 1]).max() > 0.0


def test_bitcrush_has_few_levels():
    assert len(np.unique(render(BitCrush(Sine(440.0), bits=3), 0.1))) <= 8


def test_bitcrush_downsample_holds_each_sample():
    x = render(BitCrush(Sine(440.0), bits=16, downsample=4), 0.01)
    assert np.array_equal(x[0::4], x[3::4]) and not np.array_equal(x[0::4], x[4::4])


def test_bitcrush_block_size_does_not_change_the_samples():
    f = lambda: BitCrush(Sine(440.0), bits=Sine(1.0) * 4 + 8, downsample=Sine(2.0) * 3 + 5)
    assert np.array_equal(render(f(), 0.5), render(f(), 0.5, block=37))


def test_bitcrush_keeps_silence_silent():
    for bits in range(1, 17):
        assert np.abs(render(BitCrush(Const(0.0), bits=bits), 0.01)).max() == 0.0, bits
