"""Waveshapers and dynamics.

A waveshaper bends each sample through a fixed curve, so it adds harmonics. A dynamics unit
measures its source's level and changes its gain with it: compressor, limiter and gate.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal import lfilter

from euterpe.sound.core import RATE, Param, Unit
from euterpe.sound.filters import _as_frames as _frames
from euterpe.sound.filters import _out

_CEILING = 10 ** (-1 / 20)  # where a shaper puts a full-scale input: -1 dBFS
_DRIVE = ("", 1.0, 100.0, "log")
_TIME = ("s", 0.0001, 5.0, "log")
_HOLD_ONE = 1 << 16  # one held sample in the downsampling accumulator


class BitCrush(Unit):
    """Fewer levels and fewer samples: the sound of early digital hardware.

    bits sets the number of levels: 2 ** bits - 1 of them, spread evenly over [-1, 1]
    and including 0, as in a signed integer without its most negative value (3 levels
    at 1 and 2 bits). Silence stays silent. Rounding to the levels adds an error that
    spreads over the whole spectrum, about 6 dB quieter per bit.
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
        # levels -half/half .. half/half: an odd count, so 0 is one of them
        half = np.maximum(np.round(2.0 ** (self._param("bits", n) - 1.0)) - 1.0, 1.0)
        if x.ndim == 2:
            half = half[:, None]
        q = (np.round(np.clip(x, -1.0, 1.0) * half) / half).astype(np.float32)
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


def _cubic(u: np.ndarray) -> np.ndarray:
    u = np.clip(u, -1.0, 1.0)
    return u - u**3 / 3


_CURVES = {"tanh": np.tanh, "soft": _cubic, "hard": lambda u: np.clip(u, -1.0, 1.0)}


class Shaper(Unit):
    """A waveshaper: each sample becomes curve(drive * x / 2), scaled so a full-scale input
    comes out at -1 dBFS (0.891). At drive 2 a full-scale input reaches u = 1, where the soft
    and hard curves stop rising; at drive 1, tanh and soft bend only the top of the wave a
    little. hard is a straight line up to u = 1, so from drive 1 to 2 it only scales the wave by
    0.891 and adds nothing to the spectrum; it starts to clip above drive 2.

    The curves are odd (the negative half mirrors the positive one), so they add odd harmonics
    only: 3, 5, 7 times each input frequency. tanh bends smoothly; soft is the cubic
    u - u^3 / 3, flat beyond |u| = 1; hard clips at |u| = 1, the harshest, with harmonics that
    fall slowest. More drive pushes more of the wave into the bend, so the harmonics get louder.
    A sum of frequencies also gives sums and differences of them (intermodulation).
    """

    params = (Param("drive", *_DRIVE, default=1.0),)

    def __init__(self, src: Unit, kind: Literal["tanh", "soft", "hard"], drive: float | Unit = 1.0):
        if kind not in _CURVES:
            raise ValueError(f"Shaper kind must be one of {', '.join(_CURVES)}, got {kind!r}")
        self.src, self.kind = src, kind
        self.channels = src.channels
        self._set_params(drive=drive)

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def block(self, n: int) -> np.ndarray:
        x = _frames(self.src.block(n))
        d = self._param("drive", n).astype(np.float64)[:, None] / 2
        f = _CURVES[self.kind]
        return _out(_CEILING * f(d * x) / f(d), self.channels)


class Saturator(Unit):
    """A tube-like saturator: tanh(drive * (x + bias)), with the bias taken out again.

    The bias shifts the wave before the curve, so the two halves bend differently: the curve is
    no longer odd, and even harmonics (2, 4, 6 times each frequency) join the odd ones, the
    warmer sound of tube amplifiers. The lopsided wave also has a component at 0 Hz, which a
    highpass at 10 Hz removes. The output is scaled so a full-scale sine, once that offset is
    gone, peaks at -1 dBFS (0.891).
    """

    params = (Param("drive", *_DRIVE, default=2.0), Param("bias", "", 0.0, 1.0, default=0.1))

    def __init__(self, src: Unit, drive: float | Unit = 2.0, bias: float | Unit = 0.1):
        self.src = src
        self.channels = src.channels
        self._set_params(drive=drive, bias=bias)
        self._p = np.exp(-2 * np.pi * 10.0 / RATE)
        self.reset()

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def reset(self) -> None:
        super().reset()
        self._zi = np.zeros((1, self.channels))

    def block(self, n: int) -> np.ndarray:
        x = _frames(self.src.block(n))
        d = self._param("drive", n).astype(np.float64)[:, None]
        b = self._param("bias", n).astype(np.float64)[:, None]
        rest = np.tanh(d * b)
        # a full-scale sine through the curve: its offset (its mean over a cycle), which the
        # highpass removes, and its peak on either side of that offset
        offset = np.tanh(d * (_CYCLE + b)).mean(axis=1, keepdims=True)
        scale = np.maximum(np.tanh(d * (1 + b)) - offset, offset - np.tanh(d * (b - 1)))
        y = (np.tanh(d * (x + b)) - rest) / scale
        p = self._p  # one-pole highpass at 10 Hz: y[n] = p * (y[n-1] + x[n] - x[n-1])
        y, self._zi = lfilter([p, -p], [1.0, -p], y, axis=0, zi=self._zi)
        return _out(_CEILING * y, self.channels)


_CYCLE = np.sin(2 * np.pi * np.arange(256) / 256)  # one cycle of a sine, for Saturator's level


_RMS_TIME = 0.01  # the level detector averages the squared signal over about 10 ms


class _Dynamics(Unit):
    """A unit that measures its source's level in dB (an RMS over about 10 ms, the louder
    channel of a stereo source) and multiplies the source by a gain computed from it."""

    def __init__(self, src: Unit, **values):
        self.src = src
        self.channels = src.channels
        self._set_params(**values)
        self._k = np.exp(-1.0 / (_RMS_TIME * RATE))
        self.reset()

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def reset(self) -> None:
        super().reset()
        self._ms = np.zeros(1)
        self._g = self._rest

    def _level_db(self, x: np.ndarray) -> np.ndarray:
        power = (x**2).max(axis=1)
        ms, self._ms = lfilter([1 - self._k], [1.0, -self._k], power, zi=self._ms)
        return 10 * np.log10(ms + 1e-20)

    def _smooth(self, target: np.ndarray, attack: np.ndarray, release: np.ndarray, falling_is_attack: bool) -> np.ndarray:
        """One-pole smoothing of a gain toward target, with the attack time constant while it
        moves one way and the release time constant while it moves back."""
        ka = np.exp(-1.0 / np.maximum(attack * RATE, 1e-12)).tolist()
        kr = np.exp(-1.0 / np.maximum(release * RATE, 1e-12)).tolist()
        out = np.empty(len(target))
        g = self._g
        for i, t in enumerate(target.tolist()):
            k = ka[i] if (t < g) == falling_is_attack else kr[i]
            g = t + k * (g - t)
            out[i] = g
        self._g = g
        return out


class Compressor(_Dynamics):
    """A feed-forward compressor: above threshold dB, each dB more of input gives 1 / ratio dB
    more of output; makeup dB of gain is added at the end.

    The gain follows the level with time constants attack (when it must come down) and release
    (when it goes back up), so loud passages come down and the sound's range of levels shrinks.
    A steady sound keeps its spectrum. The gain moves with the level, so a fast attack or
    release on a low note adds a little distortion, and a fast release makes the tail of each
    note swell (pumping).
    """

    params = (
        Param("threshold", "dB", -80.0, 0.0, default=-18.0),
        Param("ratio", "", 1.0, 100.0, "log", default=4.0),
        Param("attack", *_TIME, default=0.01),
        Param("release", *_TIME, default=0.1),
        Param("makeup", "dB", 0.0, 40.0, default=0.0),
    )
    _rest = 0.0  # gain reduction in dB before the first sample

    def __init__(
        self,
        src: Unit,
        threshold: float | Unit = -18.0,
        ratio: float | Unit = 4.0,
        attack: float | Unit = 0.01,
        release: float | Unit = 0.1,
        makeup: float | Unit = 0.0,
    ):
        super().__init__(src, threshold=threshold, ratio=ratio, attack=attack, release=release, makeup=makeup)

    def block(self, n: int) -> np.ndarray:
        x = _frames(self.src.block(n))
        thr, ratio, attack, release, makeup = (self._param(p.name, n).astype(np.float64) for p in self.params)
        over = np.maximum(self._level_db(x) - thr, 0.0)
        cut = self._smooth(-over * (1 - 1 / ratio), attack, release, falling_is_attack=True)
        return _out(x * (10 ** ((cut + makeup) / 20))[:, None], self.channels)


_LOOKAHEAD = round(0.005 * RATE)  # 240 samples


class Limiter(Unit):
    """A lookahead limiter: no sample of the output passes ceiling dBFS.

    The output is the source delayed by 5 ms (240 samples). In those 5 ms the gain ramps down
    ahead of each peak, so a peak is caught without a jump in the gain; it then returns to 1 with
    time constant release. Peaks are flattened and the rest is left alone, so a limiter changes
    the spectrum little unless it works hard; then it adds distortion as a shaper does.
    ceiling is a number: the gain must start falling 5 ms before a sample leaves, so a ceiling
    that moved in those 5 ms could not be kept.
    """

    params = (Param("ceiling", "dB", -40.0, 0.0, default=-1.0), Param("release", *_TIME, default=0.05))

    def __init__(self, src: Unit, ceiling: float = -1.0, release: float | Unit = 0.05):
        if isinstance(ceiling, Unit):
            raise TypeError("Limiter.ceiling must be a number, not a Unit")
        self.src = src
        self.channels = src.channels
        self._set_params(ceiling=ceiling, release=release)
        self.reset()

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def reset(self) -> None:
        super().reset()
        self._x = np.zeros((_LOOKAHEAD, self.channels))  # the last 240 inputs, oldest first
        self._need = np.ones(2 * _LOOKAHEAD)  # the last 480 gains needed, oldest first
        self._held = np.ones(_LOOKAHEAD)  # the last 240 released gains
        self._g = 1.0

    def block(self, n: int) -> np.ndarray:
        x = np.concatenate([self._x, _frames(self.src.block(n))])
        ceiling = 10 ** (self._values["ceiling"] / 20)
        kr = np.exp(-1.0 / (self._param("release", n).astype(np.float64) * RATE)).tolist()
        peak = np.abs(x[_LOOKAHEAD:]).max(axis=1)
        need = np.concatenate([self._need, np.minimum(1.0, ceiling / np.maximum(peak, 1e-20))])
        # the lowest gain needed by any sample within 240 of the one now leaving the delay
        low = sliding_window_view(need[_LOOKAHEAD:], _LOOKAHEAD + 1).min(axis=1)
        held = np.empty(n)
        g = self._g
        for i, t in enumerate(low.tolist()):
            g = t if t < g else t + kr[i] * (g - t)
            held[i] = g
        self._g = g
        # averaging 240 gains, each at most the gain the delayed sample needs, ramps it smoothly
        held = np.concatenate([self._held, held])
        gain = sliding_window_view(held[1:], _LOOKAHEAD).mean(axis=1)
        self._x, self._need, self._held = x[-_LOOKAHEAD:], need[-2 * _LOOKAHEAD :], held[-_LOOKAHEAD:]
        return _out(x[:n] * gain[:, None], self.channels)


class Gate(_Dynamics):
    """A noise gate: passes its source while its level is above threshold dB and fades it to
    silence, with time constant release, once the level falls below.

    It opens in about 1 ms. The quiet noise between notes is removed and the notes are left as
    they were: a steady sound above the threshold keeps its spectrum, and the closing fade only
    shortens the tail. A fast release cuts the soft end of a note, which shortens its decay.
    """

    params = (Param("threshold", "dB", -100.0, 0.0, default=-50.0), Param("release", *_TIME, default=0.05))
    _rest = 0.0  # closed before the first sample

    def __init__(self, src: Unit, threshold: float | Unit = -50.0, release: float | Unit = 0.05):
        super().__init__(src, threshold=threshold, release=release)

    def block(self, n: int) -> np.ndarray:
        x = _frames(self.src.block(n))
        open_ = (self._level_db(x) > self._param("threshold", n)).astype(np.float64)
        attack = np.full(n, 0.001)
        g = self._smooth(open_, attack, self._param("release", n).astype(np.float64), falling_is_attack=False)
        return _out(x * g[:, None], self.channels)
