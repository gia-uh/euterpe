"""Synthesis from models of a sound."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from euterpe.sound.core import RATE, Param, Unit

_ONE = 1 << 32  # one cycle of phase in the fixed-point accumulators


class Additive(Unit):
    """A sum of sines: each partial (ratio, amplitude) is a sine at ratio * freq with that
    amplitude, so the spectrum is one line per partial and nothing else.

    Integer ratios give harmonics, and the sound has the pitch of freq; other ratios give
    inharmonic partials, as in bells. A negative amplitude turns that sine upside down. A partial
    at or above RATE / 2 is silent for the samples where it is there, so nothing folds back.

    The sum is not normalised: its peak can pass 1 (a saw built from its harmonics reaches 1.17),
    so the caller sets the gain.
    """

    params = (Param("freq", "Hz", 0.01, 24_000.0, "log", 440.0),)

    def __init__(self, freq: float | Unit, partials: Sequence[tuple[float, float]]):
        ratios = np.array([float(r) for r, _ in partials], np.float64)
        amps = np.array([float(a) for _, a in partials], np.float64)
        bad = ~(np.isfinite(ratios) & (ratios > 0))
        if np.any(bad):
            raise ValueError(f"Additive partial ratio must be finite and > 0, got {ratios[bad][0]}")
        if not np.all(np.isfinite(amps)):
            raise ValueError(f"Additive partial amplitude must be finite, got {amps[~np.isfinite(amps)][0]}")
        self.ratios, self.amps = ratios, amps
        self._set_params(freq=freq)
        self.reset()

    def reset(self) -> None:
        super().reset()
        self._acc = np.zeros(len(self.ratios), np.int64)

    def block(self, n: int) -> np.ndarray:
        freq = self._param("freq", n).astype(np.float64)
        partial_hz = freq[:, None] * self.ratios[None, :]  # (n, partials)
        inc = np.round(partial_hz / RATE * _ONE).astype(np.int64)
        acc = self._acc + np.cumsum(inc, axis=0)
        if n:
            self._acc = acc[-1] % _ONE
        t = ((acc - inc) % _ONE) / _ONE
        waves = np.sin(2 * np.pi * t) * np.where(partial_hz < RATE / 2, self.amps, 0.0)
        return waves.sum(axis=1).astype(np.float32)
