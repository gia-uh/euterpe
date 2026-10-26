import numpy as np

from euterpe.sound.core import Const, render
from euterpe.sound.osc import Saw, Sine, Square, Triangle
from tests.helpers import band_db, peak_hz


def test_a_sine_peaks_at_its_frequency():
    assert abs(peak_hz(render(Sine(440.0), 2.0)) - 440.0) < 0.5


def test_a_saw_has_harmonics_and_little_aliasing():
    x = render(Saw(4_000.0), 1.0)
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / 48_000)
    harmonic = np.min(np.abs(freqs[:, None] - 4_000.0 * np.arange(1, 7)), axis=1) < 30
    assert spectrum[~harmonic].sum() / spectrum.sum() < 0.01


def test_square_duty_changes_the_mean():
    assert abs(render(Square(100.0, duty=0.25), 1.0).mean() + 0.5) < 0.02


def test_triangle_has_only_odd_harmonics():
    x = render(Triangle(1_000.0), 1.0)
    assert band_db(x, 2_950, 3_050) - band_db(x, 1_950, 2_050) > 30


def test_above_nyquist_is_silence():
    assert np.abs(render(Saw(Const(30_000.0)), 0.1)).max() == 0.0
    for unit in (Square(Const(30_000.0), duty=0.3), Sine(Const(30_000.0), phase=0.25), Triangle(Const(30_000.0))):
        assert np.abs(render(unit, 0.1)).max() == 0.0, type(unit).__name__


def test_block_size_does_not_change_a_modulated_oscillator():
    for make in (lambda: Saw(Sine(3.0) * 200 + 440), lambda: Triangle(Sine(5.0) * 100 + 300)):
        assert np.array_equal(render(make(), 0.5), render(make(), 0.5, block=37))


def _off_harmonic_share(x, f):
    """The share of x's energy that is neither DC nor at harmonics 1-7 of f."""
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / 48_000)
    keep = (np.min(np.abs(freqs[:, None] - f * np.arange(0, 8)), axis=1) < 20)
    return spectrum[~keep].sum() / spectrum.sum()


def test_a_square_has_little_aliasing():
    assert _off_harmonic_share(render(Square(3_300.0, duty=0.3), 1.0), 3_300.0) < 0.005


def test_a_triangle_has_little_aliasing():
    # a naive triangle already leaves only 3e-4 here (harmonics fall as 1/k²); polyBLAMP, 9e-6
    assert _off_harmonic_share(render(Triangle(3_300.0), 1.0), 3_300.0) < 5e-5


def test_a_slow_triangle_reaches_full_scale():
    for f in (1.0, 0.1):
        assert abs(render(Triangle(f), 1.5 / f).max() - 1.0) < 0.02, f   # the top of the first ramp


def test_a_saw_without_antialias_is_the_direct_ramp_and_aliases():
    x = render(Saw(1_000.0, antialias=False), 1.0)
    t = (np.arange(len(x)) * 1_000.0 / 48_000) % 1.0
    assert np.allclose(np.sin(np.pi * x), np.sin(np.pi * (2 * t - 1)), atol=1e-3)   # -1 and 1 meet at the wrap
    big = render(Saw(4_000.0, antialias=False), 1.0)
    spectrum = np.abs(np.fft.rfft(big * np.hanning(len(big)))) ** 2
    freqs = np.fft.rfftfreq(len(big), 1 / 48_000)
    harmonic = np.min(np.abs(freqs[:, None] - 4_000.0 * np.arange(1, 7)), axis=1) < 30
    assert spectrum[~harmonic].sum() / spectrum.sum() > 0.01
