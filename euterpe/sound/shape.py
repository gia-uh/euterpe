"""Waveshapers and dynamics."""

from __future__ import annotations

import numpy as np

from euterpe.sound.core import Param, Unit

_HOLD_ONE = 1 << 16  # one held sample in the downsampling accumulator


class BitCrush(Unit):
    """Fewer levels and fewer samples: the sound of early digital hardware.

    bits sets the number of levels, 2 ** bits spread evenly over [-1, 1]. Rounding to
    them adds an error that spreads over the whole spectrum, about 6 dB quieter per bit.
    downsample holds each sample for that many samples, which lowers the effective
    sample rate to RATE / downsample: components above half of it fold back as
    aliasing, and images of the signal appear around multiples of it.
    """

    params = (
        Param("bits", "bits", 1.0, 16.0, default=8.0),
        Param("downsample", "samples", 1.0, 64.0, default=1.0),
    )

    def __init__(self, src: Unit, bits: float | Unit = 8, downsample: float | Unit = 1):
        self.src = src
        self.channels = src.channels
        self._set_params(bits=bits, downsample=downsample)
        self.reset()

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def reset(self) -> None:
        super().reset()
        self._acc = _HOLD_ONE - 1  # so the first sample is taken
        self._held = np.zeros(self.channels, np.float32) if self.channels == 2 else np.float32(0.0)

    def block(self, n: int) -> np.ndarray:
        x = self.src.block(n)
        steps = np.maximum(np.round(2.0 ** self._param("bits", n)), 2.0) - 1.0
        if x.ndim == 2:
            steps = steps[:, None]
        q = (np.round((np.clip(x, -1.0, 1.0) + 1.0) / 2.0 * steps) / steps * 2.0 - 1.0).astype(np.float32)
        if n == 0:
            return q
        inc = np.round(_HOLD_ONE / self._param("downsample", n).astype(np.float64)).astype(np.int64)
        acc = self._acc + np.cumsum(inc)
        prev = np.concatenate(([self._acc], acc[:-1]))
        take = acc // _HOLD_ONE > prev // _HOLD_ONE
        self._acc = int(acc[-1] % _HOLD_ONE)
        last = np.maximum.accumulate(np.where(take, np.arange(n), -1))
        out = np.where((last >= 0)[:, None] if q.ndim == 2 else last >= 0, q[np.maximum(last, 0)], self._held)
        self._held = out[-1].copy()
        return out.astype(np.float32)
