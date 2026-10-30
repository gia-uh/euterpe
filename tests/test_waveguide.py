import numpy as np
import pytest

from euterpe.sound.core import RATE, render
from euterpe.sound.env import Segments
from euterpe.sound.osc import Sine
from euterpe.sound.waveguide import Bore, Bow, Reed
from tests.helpers import _power, peak_hz


def cents(a, b):
    return 1200 * np.log2(a / b)


def harmonic_db(x, f0, k):
    """The energy within a fifth of f0 around harmonic k, in dB."""
    freqs, power = _power(x)
    return float(10 * np.log10(power[np.abs(freqs - k * f0) < 0.2 * f0].sum() + 1e-30))


def settled(x, after=0.2):
    return x[round(after * RATE):]


def test_bow_holds_its_pitch():
    x = settled(render(Bow(440.0), 0.5))
    assert abs(cents(peak_hz(x), 440.0)) < 5


def test_bow_sounds_every_harmonic_but_the_one_with_a_node_at_the_bow():
    x = settled(render(Bow(440.0, position=0.125), 0.5))
    h = {k: harmonic_db(x, 440.0, k) for k in range(1, 10)}
    assert all(h[1] - h[k] < 20 for k in range(1, 7))
    assert h[7] - h[8] >= 10 and h[9] - h[8] >= 10


def test_bow_too_light_loses_the_fundamental():
    full = harmonic_db(settled(render(Bow(440.0), 0.5)), 440.0, 1)
    light = harmonic_db(settled(render(Bow(440.0, force=0.05), 0.5)), 440.0, 1)
    assert full - light >= 10


def test_bow_at_rest_lets_the_string_ring_down():
    speed = Segments([(0.0, 0.5), (0.2, 0.5), (0.2, 0.0)])
    x = render(Bow(440.0, speed=speed), 0.5)
    rms = lambda a, b: np.sqrt(np.mean(x[round(a * RATE):round(b * RATE)] ** 2))  # noqa: E731
    assert 20 * np.log10(rms(0.45, 0.5) / rms(0.15, 0.2)) < -20


def test_bow_follows_a_moving_freq_without_a_click():
    freq = Segments([(0.0, 440.0), (0.25, 440.0), (0.25, 493.88)])
    x = render(Bow(freq), 0.5)
    assert abs(cents(peak_hz(x[round(0.1 * RATE):round(0.25 * RATE)]), 440.0)) < 5
    assert abs(cents(peak_hz(x[round(0.32 * RATE):]), 493.88)) < 5
    steady = np.abs(np.diff(x[round(0.1 * RATE):round(0.25 * RATE)])).max()
    assert np.abs(np.diff(x[round(0.24 * RATE):round(0.3 * RATE)])).max() < 1.5 * steady


@pytest.mark.parametrize("name", ["position", "damping", "brightness"])
def test_bow_loop_parameters_take_numbers_only(name):
    with pytest.raises(TypeError, match=name):
        Bow(440.0, **{name: Sine(1.0)})


def test_bore_with_a_reed_sounds_the_odd_harmonics():
    x = settled(render(Bore(147.0), 0.5))
    h = {k: harmonic_db(x, 147.0, k) for k in range(1, 5)}
    assert h[1] - h[2] >= 10 and h[3] - h[2] >= 10 and h[3] - h[4] >= 10
    assert abs(cents(peak_hz(x), 147.0)) < 5


def test_bore_below_the_threshold_is_only_breath():
    rms = lambda p: np.sqrt(np.mean(settled(render(Bore(147.0, pressure=p), 0.5)) ** 2))  # noqa: E731
    assert 20 * np.log10(rms(0.1) / rms(0.5)) < -20


@pytest.mark.parametrize("kw", [{"damping": Sine(1.0)}, {"bell": Sine(1.0)}, {"mouth": Sine(1.0)}])
def test_bore_loop_parameters_take_numbers_or_data_only(kw):
    with pytest.raises(TypeError, match=next(iter(kw))):
        Bore(147.0, **kw)


def test_reed_is_frozen_data():
    with pytest.raises(AttributeError):
        Reed().stiffness = 0.2  # type: ignore[misc]


@pytest.mark.parametrize("make", [
    lambda seed: Bow(Sine(6.0) * 20 + 440, force=Sine(3.0) * 0.1 + 0.5, seed=seed),
    lambda seed: Bore(Sine(6.0) * 10 + 220, pressure=Sine(3.0) * 0.1 + 0.6, seed=seed),
])
def test_waveguides_are_deterministic_in_any_block_size(make):
    whole = render(make(3), 0.05)
    assert np.array_equal(whole, render(make(3), 0.05, block=1))
    assert np.array_equal(whole, render(make(3), 0.05, block=37))
    assert not np.array_equal(whole, render(make(4), 0.05))


@pytest.mark.parametrize("unit", [Bow(196.0), Bore(147.0), Bow(880.0, force=1.0, speed=1.0), Bore(880.0, pressure=1.0)])
def test_waveguides_stay_finite_and_below_full_scale(unit):
    x = render(unit, 0.3)
    assert np.all(np.isfinite(x)) and np.abs(x).max() < 1.0
