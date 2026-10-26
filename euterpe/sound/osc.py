"""Band-limited oscillators: sine, saw, square and triangle.

The phase is a 32-bit fixed-point accumulator carried across blocks, so the
samples are the same in any block size. Saw and square jump once or twice per
cycle; a jump has energy at every frequency, and the part above half the sample
rate would fold back as aliasing. polyBLEP (a polynomial band-limited step)
replaces the two samples around each jump with a smoothed step, which removes
most of that energy. Samples whose frequency is at or above RATE / 2 are zero.
"""

from __future__ import annotations

import numpy as np

from euterpe.sound.core import RATE, Param, Unit

_ONE = 1 << 32  # one cycle of phase in the fixed-point accumulator
_FREQ = Param("freq", "Hz", 0.01, 24_000.0, "log", 440.0)


def _blep(t: np.ndarray, dt: np.ndarray) -> np.ndarray:
    """The polyBLEP residual for a unit step at phase 0, sampled at phase t with increment dt."""
    out = np.zeros_like(t)
    dt = np.maximum(dt, 1e-12)
    a = t < dt
    x = t[a] / dt[a]
    out[a] = x + x - x * x - 1.0
    b = t > 1.0 - dt
    x = (t[b] - 1.0) / dt[b]
    out[b] = x * x + x + x + 1.0
    return out


def _blamp(t: np.ndarray, dt: np.ndarray) -> np.ndarray:
    """The polyBLAMP residual for a unit change of slope (per sample) at phase 0: the
    integral of the polyBLEP residual, (1 - u)³ / 6 after the corner, (1 + u)³ / 6 before."""
    out = np.zeros_like(t)
    dt = np.maximum(dt, 1e-12)
    a = t < dt
    out[a] = (1.0 - t[a] / dt[a]) ** 3 / 6.0
    b = t > 1.0 - dt
    out[b] = (1.0 + (t[b] - 1.0) / dt[b]) ** 3 / 6.0
    return out


class _Oscillator(Unit):
    channels = 1

    def reset(self) -> None:
        super().reset()
        self._acc = 0

    def _phase(self, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Phase in cycles [0, 1) and increment per sample for the next n samples, and a mask
        of the samples at or above Nyquist."""
        freq = self._param("freq", n).astype(np.float64)
        inc = np.round(freq / RATE * _ONE).astype(np.int64)
        acc = self._acc + np.cumsum(inc)
        self._acc = int(acc[-1] % _ONE) if n else self._acc
        t = ((acc - inc) % _ONE) / _ONE
        return t, inc / _ONE, freq >= RATE / 2

    def _naive(self, t: np.ndarray, dt: np.ndarray, n: int) -> np.ndarray:
        raise NotImplementedError

    def block(self, n: int) -> np.ndarray:
        t, dt, above = self._phase(n)
        out = self._naive(t, dt, n)
        out[above] = 0.0
        return out.astype(np.float32)


class Sine(_Oscillator):
    """A sine wave: all its energy sits at one frequency, freq.

    phase offsets the wave by a fraction of a cycle; modulating it is phase modulation.
    """

    params = (_FREQ, Param("phase", "cycles", 0.0, 1.0, default=0.0))

    def __init__(self, freq: float | Unit = 440.0, phase: float | Unit = 0.0):
        self._set_params(freq=freq, phase=phase)
        self.reset()

    def _naive(self, t, dt, n):
        return np.sin(2 * np.pi * (t + self._param("phase", n)))


class Saw(_Oscillator):
    """A sawtooth rising from -1 to 1 once per cycle: every harmonic k of freq, at amplitude 1/k
    (6 dB lower per octave). Band-limited with polyBLEP.

    With antialias=False the ramp is computed directly, with no correction at the drop: every
    harmonic above 24 000 Hz folds back to a lower, out-of-tune frequency. Useful to hear aliasing,
    and for deliberately harsh, lo-fi tones.
    """

    params = (_FREQ,)

    def __init__(self, freq: float | Unit = 440.0, *, antialias: bool = True):
        self.antialias = antialias
        self._set_params(freq=freq)
        self.reset()

    def _naive(self, t, dt, n):
        ramp = 2.0 * t - 1.0
        return ramp - _blep(t, dt) if self.antialias else ramp


class Square(_Oscillator):
    """A pulse wave, 1 for the first duty fraction of each cycle and -1 for the rest.

    At duty 0.5 it holds only the odd harmonics of freq, at amplitude 1/k. Other duties add
    even harmonics and move the mean to 2 * duty - 1. Band-limited with polyBLEP.
    """

    params = (_FREQ, Param("duty", "", 0.01, 0.99, default=0.5))

    def __init__(self, freq: float | Unit = 440.0, duty: float | Unit = 0.5):
        self._set_params(freq=freq, duty=duty)
        self.reset()

    def _naive(self, t, dt, n):
        duty = self._param("duty", n).astype(np.float64)
        return _square(t, dt, duty)


def _square(t, dt, duty):
    out = np.where(t < duty, 1.0, -1.0)
    return out + _blep(t, dt) - _blep((t - duty) % 1.0, dt)


class Triangle(_Oscillator):
    """A triangle wave: only the odd harmonics of freq, at amplitude 1/k² (12 dB lower per
    octave), so it sounds softer than a square.

    It rises from -1 to 1 in the first half of each cycle and falls back in the second.
    The two corners are rounded with polyBLAMP (the integral of polyBLEP), which removes
    most of the energy that would fold back. Slow triangles, as LFOs, reach ±1 exactly;
    higher up the rounding lowers the peak (0.98 at 440 Hz, 0.94 at 2 kHz, 0.78 at 8 kHz), as it must
    for a wave with no component above 24 kHz.
    """

    params = (_FREQ,)

    def __init__(self, freq: float | Unit = 440.0):
        self._set_params(freq=freq)
        self.reset()

    def _naive(self, t, dt, n):
        out = np.where(t < 0.5, 4.0 * t - 1.0, 3.0 - 4.0 * t)
        # the slope changes by +8 per cycle at the bottom (phase 0), by -8 at the top (0.5)
        return out + 8.0 * dt * (_blamp(t, dt) - _blamp((t - 0.5) % 1.0, dt))
