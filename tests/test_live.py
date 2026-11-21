import numpy as np

from euterpe.sound import Live, LowPass, WhiteNoise, render


def test_live_ramps_to_each_new_value():
    vals = iter([1.0, 1.0])
    u = Live(lambda: next(vals), start=0.0)
    np.testing.assert_allclose(u.block(4), [0.25, 0.5, 0.75, 1.0])
    np.testing.assert_allclose(u.block(2), [1.0, 1.0])


def test_live_is_continuous_across_blocks():
    vals = iter([2.0, 4.0])
    u = Live(lambda: next(vals), start=0.0)
    a, b = u.block(8), u.block(8)
    assert a[-1] == 2.0 and abs((b[0] - a[-1]) - (4.0 - 2.0) / 8) < 1e-6


def test_live_reset_returns_to_start():
    u = Live(lambda: 5.0, start=1.0)
    u.block(4)
    u.reset()
    assert u.last == 1.0
    assert u.block(1)[0] == 5.0 and u.last == 5.0


def test_live_is_mono_float32_and_never_ends():
    u = Live(lambda: 0.5)
    x = u.block(16)
    assert x.dtype == np.float32 and x.shape == (16,) and u.duration is None and u.inputs() == []


def test_a_steady_live_moves_a_filter_like_a_number():
    a = render(LowPass(WhiteNoise(seed=1), Live(lambda: 500.0, start=500.0)), 0.5)
    b = render(LowPass(WhiteNoise(seed=1), 500.0), 0.5)
    np.testing.assert_allclose(a, b, atol=1e-6)
