"""Noise sources: signals with no pitch, drawn from a seeded random generator."""

from __future__ import annotations

import numpy as np

from euterpe.sound.core import Unit, rng


class WhiteNoise(Unit):
    """Independent random samples, uniform between -1 and 1. Its spectrum is flat: on average
    every frequency band of the same width in Hz holds the same energy, up to 24 000 Hz.

    The same seed gives the same samples, in any block size.
    """

    def __init__(self, seed: int):
        self.seed = int(seed)
        self.reset()

    def reset(self) -> None:
        self._rng = rng(self.seed)

    def block(self, n: int) -> np.ndarray:
        return self._rng.uniform(-1.0, 1.0, n).astype(np.float32)
