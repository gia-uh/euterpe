"""Share: one unit read by several units of a graph."""

from __future__ import annotations

import numpy as np

from euterpe.sound.core import Unit


class Share:
    """One unit that several units of a graph read, computed once. A unit keeps state, so it
    may appear only once in a graph; a Share holds it and hands out taps, each a unit that
    reads the same samples from its own position. The source is pulled once per sample
    however many taps read it.

    A share does nothing to the spectrum: each tap gives exactly its source's samples. It
    keeps the samples some tap has not read yet, so a tap that is never read holds them all.
    """

    def __init__(self, src: Unit):
        self.src = src
        self.taps: list[Tap] = []
        self._buf = np.zeros((0, 2) if src.channels == 2 else 0, np.float32)
        self._base = 0  # the sample index of _buf[0]

    def tap(self) -> Tap:
        """A new reader of the source, starting where the source starts."""
        t = Tap(self)
        self.taps.append(t)
        return t

    def reset(self) -> None:
        """Start the source over for every tap."""
        self.src.reset()
        self._buf = self._buf[:0]
        self._base = 0
        for t in self.taps:
            t.pos = 0

    def _read(self, tap: Tap, n: int) -> np.ndarray:
        end = self._base + len(self._buf)
        if tap.pos + n > end:
            self._buf = np.concatenate([self._buf, self.src.block(tap.pos + n - end)])
        lo = tap.pos - self._base
        out = self._buf[lo:lo + n].copy()
        tap.pos += n
        keep = min(t.pos for t in self.taps) - self._base
        if keep > 0:
            self._buf = self._buf[keep:]
            self._base += keep
        return out


class Tap(Unit):
    """One reader of a Share: its source's samples, from this tap's own position."""

    def __init__(self, share: Share):
        self._share = share
        self.channels = share.src.channels
        self.pos = 0

    def inputs(self) -> list[Unit]:
        return []

    def reset(self) -> None:
        self._share.reset()

    @property
    def duration(self) -> float | None:
        return self._share.src.duration

    def block(self, n: int) -> np.ndarray:
        return self._share._read(self, n)
