import numpy as np
import pytest

from euterpe.sound.core import BLOCK, RATE, Const, Mix, Unit, _signal, render


class Ramp(Unit):
    """Test unit: 0, 1, 2, … so block boundaries are visible."""
    channels = 1

    def __init__(self, step=1.0):
        self.step = step
        self.reset()

    def reset(self):
        self.i = 0

    def block(self, n):
        out = (np.arange(self.i, self.i + n) * _signal(self.step, n)).astype(np.float32)
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


def test_a_parameter_may_be_a_unit_and_is_an_input():
    step = Const(50.0)
    r = Ramp(step=step)
    assert r.inputs() == [step]
    assert render(r, 10 / RATE)[1] == 50.0


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


def test_subtraction_and_negation_with_units_and_numbers():
    ramp = render(Ramp(), 0.01)
    assert np.array_equal(render(Ramp() - 1.0, 0.01), ramp - 1)
    assert np.array_equal(render(1.0 - Ramp(), 0.01), 1 - ramp)
    assert np.array_equal(render(-Ramp(), 0.01), -ramp)
    assert np.array_equal(render(Ramp() - Ramp(step=2.0), 0.01), ramp - 2 * ramp)


def test_subtraction_renders_the_same_in_any_block_size():
    def make():
        return 1.0 - (Ramp() - Ramp(step=0.5)) * 0.25 - -Ramp()

    assert np.array_equal(render(make(), 0.5, block=BLOCK), render(make(), 0.5, block=37))
