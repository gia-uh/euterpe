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
from scipy.signal import lfilter

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
    """

    params = (_FREQ,)

    def __init__(self, freq: float | Unit = 440.0):
        self._set_params(freq=freq)
        self.reset()

    def _naive(self, t, dt, n):
        return 2.0 * t - 1.0 - _blep(t, dt)


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

    It is the integral of the band-limited square, scaled so the ideal wave spans -1 to 1.
    The integrator leaks slightly (pole 0.9995) so no offset can build up. Its peak is
    below 1 at both ends of the range: 0.97 at 20 Hz, where the leak flattens each ramp,
    0.99 from 100 Hz to 440 Hz, 0.92 at 2 kHz and 0.67 at 8 kHz, where band-limiting
    rounds the corners (a triangle with no harmonic above 24 kHz cannot reach 1 there).
    """

    params = (_FREQ,)
    _POLE = 0.9995

    def __init__(self, freq: float | Unit = 440.0):
        self._set_params(freq=freq)
        self.reset()

    def reset(self) -> None:
        super().reset()
        self._zi = np.array([-self._POLE])  # start at -1, at the bottom of the ramp

    def _naive(self, t, dt, n):
        slope = 4.0 * dt * _square(t, dt, np.full(n, 0.5))
        slope[dt >= 0.5] = 0.0
        out, self._zi = lfilter([1.0], [1.0, -self._POLE], slope, zi=self._zi)
        return out
