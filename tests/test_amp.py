import numpy as np

from euterpe.sound.core import RATE, render
from euterpe.sound.env import Segments
from euterpe.sound.osc import Saw, Sine
from euterpe.sound.noise import WhiteNoise


def _spectrum(x):
    x = x.astype(np.float64)[RATE // 4:]
    mag = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return np.fft.rfftfreq(len(x), 1 / RATE), mag


def _at(f, mag, hz):
    return mag[np.argmin(np.abs(f - hz))]


def _db(a, b):
    return 20 * np.log10(a / b)


def test_low_gain_is_nearly_clean():
    from euterpe.sound import Amp

    f, mag = _spectrum(render(Amp(Sine(220.0) * 0.5, gain=0.05), 1.25))
    for k in range(2, 11):
        assert _db(_at(f, mag, 220.0 * k), _at(f, mag, 220.0)) < -50


def test_more_gain_more_third_harmonic():
    from euterpe.sound import Amp

    def third(g):
        f, mag = _spectrum(render(Amp(Sine(220.0) * 0.5, gain=g), 1.25))
        return _db(_at(f, mag, 660.0), _at(f, mag, 220.0))

    assert third(20.0) > third(2.0) + 6


def _on_series(x, base):
    """The share of the spectrum above 20 Hz within 3 Hz of a multiple of base."""
    f, mag = _spectrum(x)
    keep = f > 20
    near = np.abs(f - base * np.round(f / base)) <= 3.0
    return (mag[keep & near] ** 2).sum() / (mag[keep] ** 2).sum()


def test_fifths_land_on_the_harmonic_series():
    from euterpe.pitch import A2, C3, E3
    from euterpe.sound import Amp

    a, e, cs = A2.freq, E3.freq, (C3 + 1).freq
    fifth = render(Amp(Sine(a) * 0.4 + Sine(e) * 0.4, gain=20.0), 1.25)
    third = render(Amp(Sine(a) * 0.4 + Sine(cs) * 0.4, gain=20.0), 1.25)
    assert _on_series(fifth, a / 2) > _on_series(third, a / 2) + 0.2


def test_gain_and_tone_may_move():
    from euterpe.sound import Amp

    y = render(Amp(Saw(110.0) * 0.5, gain=Segments([(0.0, 1.0), (0.5, 30.0)]),
                   treble=Segments([(0.0, -6.0), (0.5, 6.0)])), 0.5)
    assert np.all(np.isfinite(y)) and np.abs(y).max() > 0.1


def test_cabinet_cuts_fizz_and_rumble():
    from euterpe.sound import Cabinet

    def level(hz):
        y = render(Cabinet(Sine(hz) * 0.5), 0.5)[RATE // 4:].astype(np.float64)
        return np.sqrt(np.mean(y ** 2))

    assert _db(level(10_000.0), level(2000.0)) <= -24
    assert level(40.0) < level(120.0)


def test_amp_and_cabinet_render_the_same_in_any_block_size():
    from euterpe.sound import Amp, Cabinet

    def make():
        return Cabinet(Amp(WhiteNoise(seed=3) * 0.3, gain=12.0, mid=3.0), size=1.4)

    a = render(make(), 0.3)
    b = render(make(), 0.3, block=97)
    assert np.array_equal(a, b)


def test_a_cabinet_draws_its_response():
    from euterpe.sound import Cabinet
    from euterpe.sound.core import Const

    assert Cabinet(Const(0.0)).response(caption="A guitar cabinet").svg()
