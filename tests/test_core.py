import numpy as np
import pytest

from euterpe.sound.core import BLOCK, RATE, Const, Mix, Param, Unit, render


class Ramp(Unit):
    """Test unit: 0, 1, 2, … so block boundaries are visible."""
    params = (Param("step", "", 0.0, 10.0, default=1.0),)
    channels = 1

    def __init__(self, step=1.0):
        self._set_params(step=step)
        self.reset()

    def reset(self):
        self.i = 0

    def block(self, n):
        out = (np.arange(self.i, self.i + n) * self._param("step", n)).astype(np.float32)
        self.i += n
        return out


def test_render_length_and_type():
    x = render(Ramp(), 1.0)
    assert x.shape == (RATE,) and x.dtype == np.float32


def test_block_size_does_not_change_the_samples():
    assert np.array_equal(render(Ramp(), 0.5, block=BLOCK), render(Ramp(), 0.5, block=37))


def test_zero_seconds_is_empty_and_negative_is_refused():
    assert render(Ramp(), 0).shape == (0,)
    with pytest.raises(ValueError):
        render(Ramp(), -1)


def test_a_constant_out_of_range_is_refused_with_its_name():
    with pytest.raises(ValueError, match=r"Ramp\.step=11\.0 outside \[0\.0, 10\.0\]"):
        Ramp(step=11.0)


def test_modulation_is_clipped_to_the_range():
    assert render(Ramp(step=Const(50.0)), 10 / RATE)[1] == 10.0


def test_mono_plus_stereo_is_stereo():
    class Two(Ramp):
        channels = 2
        def block(self, n):
            return np.zeros((n, 2), np.float32)
    x = render(Mix(Ramp(), Two()), 4 / RATE)
    assert x.shape == (4, 2) and np.array_equal(x[:, 0], x[:, 1])


def test_a_unit_used_twice_is_refused():
    r = Ramp()
    with pytest.raises(ValueError, match=r"Ramp is used twice"):
        render(r + r * 0.5, 0.01)
