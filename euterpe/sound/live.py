"""Live: a value the program sets while the graph plays."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from euterpe.sound.core import Unit


class Live(Unit):
    """A value read from the program once per block, such as an engine's rpm from a game's
    physics. Each block ramps in a straight line from the last value read to the new one, so a
    parameter it moves never jumps.

    A value that stands still is a single line at 0 Hz, like Const. A moving value is a ramp
    that bends once per block, which adds the faint harmonics of a staircase of slopes at the
    block rate. Because the program decides the value when the block is asked for, the samples
    of a moving Live depend on the block size: the rule that any block size gives the same
    samples holds only while the value stands still.

    read: called once per block, returns the new value. start: the value before the first block.
    """

    channels = 1

    def __init__(self, read: Callable[[], float], start: float = 0.0):
        self.read = read
        self.start = float(start)
        self.last = self.start

    def inputs(self) -> list[Unit]:
        return []

    def reset(self) -> None:
        self.last = self.start

    def block(self, n: int) -> np.ndarray:
        v = float(self.read())
        out = self.last + (v - self.last) * (np.arange(1, n + 1) / n)
        self.last = v
        return out.astype(np.float32)
