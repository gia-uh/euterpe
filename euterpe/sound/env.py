"""Envelopes: signals that change slowly, used as a gain or to move another unit's parameter.

An envelope's value is a function of the time since the render started. Each unit counts the
samples it has produced, so the samples are the same in any block size.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from euterpe.sound.core import RATE, Param, Unit

_TIME = ("s", 0.0, 30.0, "log")
_BOW = 6.0  # curve = 1 bends a segment like exp(-6 p): 95 % of the way after half its time


def _bend(p: np.ndarray, curve: np.ndarray) -> np.ndarray:
    """The fraction of the way a segment has gone at progress p in [0, 1]: p itself when curve
    is 0, faster at first when curve > 0 (like a capacitor charging), slower when curve < 0."""
    k = _BOW * curve
    flat = np.abs(k) < 1e-6
    k = np.where(flat, 1.0, k)
    bent = -np.expm1(-k * p) / -np.expm1(-k)
    return np.where(flat, p, bent)


class ADSR(Unit):
    """An attack-decay-sustain-release envelope for one note, from 0 up to 1 and back to 0.

    It rises from 0 to 1 in attack seconds, falls to sustain in decay seconds and stays there
    until gate seconds (the time the key is held), then falls to 0 in release seconds. If the
    gate ends before the sustain is reached, the release starts from the level at that moment.
    curve bends every segment: 0 is a straight line, positive moves fast first and slows down,
    as an exponential does, negative the reverse.

    Used as a gain it shapes a sound's loudness over time; multiplying a tone by it spreads each
    of the tone's lines into a band about as wide as 1 / (the shortest segment), so a fast attack
    adds a click, a broad burst of frequencies, and a slow one adds almost nothing.
    """

    params = (
        Param("attack", *_TIME, default=0.01),
        Param("decay", *_TIME, default=0.1),
        Param("sustain", "", 0.0, 1.0, default=0.7),
        Param("release", *_TIME, default=0.3),
        Param("gate", "s", 0.0, 3600.0, default=1.0),
        Param("curve", "", -1.0, 1.0, default=0.0),
    )

    def __init__(
        self,
        attack: float | Unit = 0.01,
        decay: float | Unit = 0.1,
        sustain: float | Unit = 0.7,
        release: float | Unit = 0.3,
        gate: float | Unit = 1.0,
        curve: float | Unit = 0.0,
    ):
        self._set_params(attack=attack, decay=decay, sustain=sustain, release=release, gate=gate, curve=curve)
        self.reset()

    def reset(self) -> None:
        super().reset()
        self._done = 0

    def _held(self, t, a, d, s, c):
        """The level t seconds in while the key is held."""
        rise = _bend(np.clip(t / np.maximum(a, 1e-12), 0.0, 1.0), c)
        fall = 1.0 + (s - 1.0) * _bend(np.clip((t - a) / np.maximum(d, 1e-12), 0.0, 1.0), c)
        return np.where(t < a, rise, np.where(t < a + d, fall, s))

    def block(self, n: int) -> np.ndarray:
        a, d, s, r, g, c = (self._param(p.name, n).astype(np.float64) for p in self.params)
        t = (self._done + np.arange(n)) / RATE
        self._done += n
        held = self._held(t, a, d, s, c)
        start = self._held(g, a, d, s, c)
        p = np.clip((t - g) / np.maximum(r, 1e-12), 0.0, 1.0)
        released = np.where(t - g < r, start * (1.0 - _bend(p, c)), 0.0)
        return np.where(t < g, held, released).astype(np.float32)


class Segments(Unit):
    """An envelope through (time, level) points, a straight line between each pair. Before the
    first point it holds the first level, after the last point the last level.

    Like ADSR, as a gain it spreads each line of a tone's spectrum by about 1 / (the shortest
    segment's duration); a sudden step spreads it over every frequency.
    """

    def __init__(self, points: Sequence[tuple[float, float]]):
        if not points:
            raise ValueError("Segments needs at least one (time, level) point")
        times = np.array([float(t) for t, _ in points], np.float64)
        levels = np.array([float(v) for _, v in points], np.float64)
        if not (np.all(np.isfinite(times)) and np.all(np.isfinite(levels))):
            raise ValueError("Segments points must be finite")
        if np.any(np.diff(times) < 0):
            raise ValueError(f"Segments times must not decrease, got {times.tolist()}")
        self.times, self.levels = times, levels
        self.reset()

    def reset(self) -> None:
        self._done = 0

    def block(self, n: int) -> np.ndarray:
        t = (self._done + np.arange(n)) / RATE
        self._done += n
        return np.interp(t, self.times, self.levels).astype(np.float32)


class EnvelopeFollower(Unit):
    """The amplitude of its source over time: the peak of |src|, rising toward a louder peak in
    about attack seconds and falling toward a quieter one in about release seconds.

    The output keeps the slow changes of the source's level (its envelope) and drops its tone:
    what is left is a low-frequency signal, with a ripple at the source's frequencies that is
    smaller the longer release is. A stereo source is followed on its louder side.
    """

    params = (Param("attack", *_TIME, default=0.005), Param("release", *_TIME, default=0.1))

    def __init__(self, src: Unit, attack: float | Unit = 0.005, release: float | Unit = 0.1):
        self.src = src
        self._set_params(attack=attack, release=release)
        self.reset()

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def reset(self) -> None:
        super().reset()
        self._level = 0.0

    def block(self, n: int) -> np.ndarray:
        x = np.abs(self.src.block(n).astype(np.float64))
        if x.ndim == 2:
            x = x.max(axis=1)
        # one-pole smoothing: each sample moves the level a fraction (1 - k) of the way to |x|
        rise = np.exp(-1.0 / np.maximum(self._param("attack", n) * RATE, 1e-12))
        fall = np.exp(-1.0 / np.maximum(self._param("release", n) * RATE, 1e-12))
        out = np.empty(n, np.float64)
        y = self._level
        for i, (v, ka, kr) in enumerate(zip(x.tolist(), rise.tolist(), fall.tolist())):
            k = ka if v > y else kr
            y = v + k * (y - v)
            out[i] = y
        self._level = y
        return out.astype(np.float32)
