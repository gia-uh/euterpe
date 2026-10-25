import numpy as np

from euterpe.sound.core import render
from euterpe.sound.osc import Sine
from euterpe.sound.shape import BitCrush


def test_bitcrush_has_few_levels():
    assert len(np.unique(render(BitCrush(Sine(440.0), bits=3), 0.1))) <= 8


def test_bitcrush_downsample_holds_each_sample():
    x = render(BitCrush(Sine(440.0), bits=16, downsample=4), 0.01)
    assert np.array_equal(x[0::4], x[3::4]) and not np.array_equal(x[0::4], x[4::4])


def test_bitcrush_block_size_does_not_change_the_samples():
    f = lambda: BitCrush(Sine(440.0), bits=Sine(1.0) * 4 + 8, downsample=Sine(2.0) * 3 + 5)
    assert np.array_equal(render(f(), 0.5), render(f(), 0.5, block=37))
