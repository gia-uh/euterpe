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


def test_bitcrush_keeps_silence_silent():
    from euterpe.sound.core import Const

    for bits in range(1, 17):
        assert np.abs(render(BitCrush(Const(0.0), bits=bits), 0.01)).max() == 0.0, bits
