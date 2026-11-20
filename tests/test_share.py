import numpy as np
import pytest

from euterpe.sound import RATE, LowPass, Saw, Share, Unit, WhiteNoise, render


class Counting(Unit):
    def __init__(self, src):
        self.src, self.pulled = src, 0

    def block(self, n):
        self.pulled += n
        return self.src.block(n)


def test_taps_read_the_same_samples():
    s = Share(WhiteNoise(seed=3))
    assert np.abs(render(s.tap() - s.tap(), 1.0)).max() == 0.0


def test_a_share_pulls_its_source_once():
    c = Counting(WhiteNoise(seed=3))
    s = Share(c)
    render(s.tap() + s.tap() + s.tap(), 1.0)
    assert c.pulled == RATE


def test_a_unit_used_twice_without_share_still_raises():
    w = WhiteNoise(seed=3)
    with pytest.raises(ValueError, match="used twice"):
        render(w + w, 0.1)


def test_a_source_shared_and_also_used_directly_raises():
    w = WhiteNoise(seed=3)
    s = Share(w)
    with pytest.raises(ValueError, match="used twice"):
        render(s.tap() + w, 0.1)


def test_taps_render_alike_in_any_block_size():
    def g():
        s = Share(Saw(110.0))
        return LowPass(s.tap(), 800.0) + s.tap() * 0.3

    np.testing.assert_array_equal(render(g(), 1.0, block=256), render(g(), 1.0, block=1024))


def test_reset_starts_the_source_over():
    s = Share(WhiteNoise(seed=9))
    u = s.tap() + s.tap()
    np.testing.assert_array_equal(render(u, 0.5), render(u, 0.5))


def test_a_tap_matches_its_source_alone():
    a = render(Share(Saw(220.0)).tap(), 0.5)
    np.testing.assert_array_equal(a, render(Saw(220.0), 0.5))
