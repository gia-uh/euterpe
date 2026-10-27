import numpy as np
import pytest
from euterpe.sound import Body, Segments, Sine
from euterpe.sound.core import RATE, render
from tests.helpers import peak_hz


def click():
    return Segments([(0.0, 1.0), (1 / RATE, 0.0)])


def test_dry_only_is_the_source():
    a = render(Body(Sine(220.0), [200.0], [0.1], [0.0], dry=1.0), 0.2)
    assert np.allclose(a, render(Sine(220.0), 0.2), atol=1e-6)


def test_a_mode_rings_at_its_frequency():
    x = render(Body(click(), [200.0], [0.5], [1.0], dry=0.0), 0.5)
    assert peak_hz(x) == pytest.approx(200.0, abs=2.0)


def test_a_mode_decays_in_its_time():
    x = np.abs(render(Body(click(), [200.0], [0.3], [1.0], dry=0.0), 0.4))
    assert x[int(0.33 * RATE):].max() < 2e-3 * x[: RATE // 100].max()


def test_duration_adds_the_slowest_decay():
    assert Body(click(), [200.0, 400.0], [0.3, 0.5], [1.0, 1.0]).duration == pytest.approx(0.5, abs=1e-3)
    assert Body(Sine(220.0), [200.0], [0.3], [1.0]).duration is None


def test_a_mode_has_its_gain_at_its_frequency_and_none_at_dc():
    tone = render(Body(Sine(200.0), [200.0], [0.3], [1.0], dry=0.0), 2.0)[RATE:]
    assert np.abs(tone).max() == pytest.approx(1.0, abs=0.02)
    from euterpe.sound import Const
    assert np.abs(render(Body(Const(1.0), [100.0], [0.3], [1.0], dry=0.0), 2.0)[RATE:]).max() < 1e-3
