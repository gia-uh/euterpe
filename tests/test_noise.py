import numpy as np

from euterpe.sound.core import render
from euterpe.sound.noise import WhiteNoise


def test_noise_is_reproducible_by_seed():
    assert np.array_equal(render(WhiteNoise(seed=3), 0.1), render(WhiteNoise(seed=3), 0.1))
    assert not np.array_equal(render(WhiteNoise(seed=3), 0.1), render(WhiteNoise(seed=4), 0.1))


def test_block_size_does_not_change_noise():
    assert np.array_equal(render(WhiteNoise(seed=5), 0.1), render(WhiteNoise(seed=5), 0.1, block=77))
