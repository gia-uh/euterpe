"""Filters: units that change the level of each frequency in their source.

Every filter here is linear: a sine in gives a sine out at the same frequency, louder or quieter
and shifted in time. A stereo source is filtered per channel.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.signal import lfilter

from euterpe.sound.core import LN60, RATE, Param, Unit, _after

_GRID = 64  # a modulated cutoff or q is read once per this many samples, counted from the start
_CUTOFF = ("Hz", 10.0, 23_000.0, "log")


class _Section:
    """One IIR filter with its state, per channel, run by scipy's lfilter."""

    def __init__(self, channels: int, order: int):
        self.channels, self.order = channels, order
        self.reset()

    def reset(self) -> None:
        self.zi = np.zeros((self.order, self.channels))

    def run(self, b: np.ndarray, a: np.ndarray, x: np.ndarray) -> np.ndarray:
        """Filter x, shape (n, channels), with coefficients b and a, carrying the state on."""
        y, self.zi = lfilter(b, a, x, axis=0, zi=self.zi)
        return y


def _as_frames(x: np.ndarray) -> np.ndarray:
    return x.astype(np.float64).reshape(len(x), -1)


def _out(y: np.ndarray, channels: int) -> np.ndarray:
    return (y if channels == 2 else y[:, 0]).astype(np.float32)


class _Filter(Unit):
    """A source run through one IIR section whose coefficients come from the parameters.

    Constant parameters give one set of coefficients. A modulated one is read every _GRID
    samples from the start of the render, and the coefficients are recomputed there.
    """

    def __init__(self, src: Unit, **values):
        self.src = src
        self.channels = src.channels
        self._set_params(**values)
        self._section = _Section(self.channels, 2)
        self._moving = any(isinstance(v, Unit) for v in self._values.values())
        if not self._moving:
            self._ba = self._coeffs(*self._values.values())
        self.reset()

    def _coeffs(self, *values: float) -> tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def reset(self) -> None:
        super().reset()
        if hasattr(self, "_section"):
            self._section.reset()
        self._done = 0

    def block(self, n: int) -> np.ndarray:
        x = _as_frames(self.src.block(n))
        if not self._moving:
            self._done += n
            return _out(self._section.run(*self._ba, x), self.channels)
        values = [self._param(p.name, n).astype(np.float64) for p in self.params]
        first = (-self._done) % _GRID
        cuts = [0, *range(first, n, _GRID), n]
        y = np.empty_like(x)
        for lo, hi in zip(cuts, cuts[1:]):
            if lo == hi:
                continue
            if (self._done + lo) % _GRID == 0:
                self._ba = self._coeffs(*(v[lo] for v in values))
            y[lo:hi] = self._section.run(*self._ba, x[lo:hi])
        self._done += n
        return _out(y, self.channels)


_KINDS = ("lowpass", "highpass", "bandpass", "notch")


def _rbj(kind: str, cutoff: float, q: float) -> tuple[np.ndarray, np.ndarray]:
    """Biquad coefficients from R. Bristow-Johnson's Audio EQ Cookbook."""
    w = 2 * np.pi * cutoff / RATE
    cos, alpha = np.cos(w), np.sin(w) / (2 * q)
    if kind == "lowpass":
        b = [(1 - cos) / 2, 1 - cos, (1 - cos) / 2]
    elif kind == "highpass":
        b = [(1 + cos) / 2, -(1 + cos), (1 + cos) / 2]
    elif kind == "bandpass":
        b = [alpha, 0.0, -alpha]
    else:
        b = [1.0, -2 * cos, 1.0]
    a = np.array([1 + alpha, -2 * cos, 1 - alpha])
    return np.array(b) / a[0], a / a[0]


class Biquad(_Filter):
    """A two-pole, two-zero filter: lowpass, highpass, bandpass or notch around cutoff Hz.

    lowpass keeps frequencies below cutoff and cuts those above by 12 dB per octave; highpass
    does the reverse. bandpass keeps a band around cutoff, about cutoff / q Hz wide, at 0 dB in
    its centre, and falls 6 dB per octave on each side. notch removes that band and keeps the
    rest. In lowpass and highpass a q above 0.707 adds a peak at the cutoff, q times the level
    (+20 log10 q dB): the filter resonates there.
    """

    params = (Param("cutoff", *_CUTOFF, default=1_000.0), Param("q", "", 0.1, 40.0, "log", default=0.707))

    @property
    def duration(self) -> float | None:
        """The source's plus the ringing of the resonance: 60 dB at q / (pi cutoff) per time constant."""
        tail = LN60 * self._fixed("q", 40.0) / (np.pi * self._fixed("cutoff", 20.0))
        return _after(self.src.duration, float(tail))

    def response(self, **kw):
        """This filter's gain over frequency, as a view."""
        from euterpe.view import response

        return response(self, **kw)

    def __init__(
        self,
        src: Unit,
        kind: Literal["lowpass", "highpass", "bandpass", "notch"],
        cutoff: float | Unit = 1000.0,
        q: float | Unit = 0.707,
    ):
        if kind not in _KINDS:
            raise ValueError(f"Biquad kind must be one of {', '.join(_KINDS)}, got {kind!r}")
        self.kind = kind
        super().__init__(src, cutoff=cutoff, q=q)

    def _coeffs(self, cutoff: float, q: float) -> tuple[np.ndarray, np.ndarray]:
        return _rbj(self.kind, cutoff, q)


class OnePole(_Filter):
    """The simplest filter: one pole, a gentle slope of 6 dB per octave beyond cutoff Hz.

    lowpass keeps what is below cutoff and is 3 dB down at it; highpass keeps what is above.
    Each output sample of the lowpass moves a fixed fraction of the way from the last output
    to the new input. A highpass at a few Hz removes a DC offset (a component at 0 Hz).
    """

    params = (Param("cutoff", *_CUTOFF, default=1_000.0),)

    @property
    def duration(self) -> float | None:
        """The source's plus 60 dB of the pole's time constant, 1 / (2 pi cutoff)."""
        return _after(self.src.duration, float(LN60 / (2 * np.pi * self._fixed("cutoff", 20.0))))

    def response(self, **kw):
        """This filter's gain over frequency, as a view."""
        from euterpe.view import response

        return response(self, **kw)

    def __init__(self, src: Unit, cutoff: float | Unit, kind: Literal["lowpass", "highpass"] = "lowpass"):
        if kind not in ("lowpass", "highpass"):
            raise ValueError(f"OnePole kind must be lowpass or highpass, got {kind!r}")
        self.kind = kind
        super().__init__(src, cutoff=cutoff)

    def _coeffs(self, cutoff: float) -> tuple[np.ndarray, np.ndarray]:
        p = np.exp(-2 * np.pi * cutoff / RATE)
        b = [1 - p, 0.0, 0.0] if self.kind == "lowpass" else [p, -p, 0.0]
        return np.array(b), np.array([1.0, -p, 0.0])


class _Delayed(Unit):
    """A filter built on a delay line of round(delay * RATE) samples, run in chunks no longer
    than the delay so each chunk is computed from samples already in the line. Its delay and
    gain are numbers: a moving delay is a chorus or a flanger, not a comb."""

    @property
    def duration(self) -> float | None:
        """The source's plus the echoes until the feedback has brought them down 60 dB."""
        g = abs(self.g)
        # the feedback also builds the level up, by up to 1 / (1 - |g|), before it decays
        trips = (LN60 + np.log(1 / (1 - g))) / -np.log(g) if 0 < g < 1 else 1.0
        return _after(self.src.duration, float(self._values["delay"] * (trips + 1)))

    def __init__(self, src: Unit, delay: float, gain: float):
        self.src = src
        self.channels = src.channels
        gain_name = self.params[1].name
        for name, v in (("delay", delay), (gain_name, gain)):
            if isinstance(v, Unit):
                raise TypeError(f"{type(self).__name__}.{name} must be a number, not a Unit")
        self._set_params(**{"delay": delay, gain_name: gain})
        self.d = max(1, round(self._values["delay"] * RATE))
        self.g = self._values[gain_name]
        self.reset()

    def inputs(self) -> list[Unit]:
        return [self.src]

    def reset(self) -> None:
        super().reset()
        self._xs = np.zeros((self.d, self.channels))  # the last d inputs, oldest first
        self._ys = np.zeros((self.d, self.channels))  # the last d outputs

    def _chunk(self, x: np.ndarray, xd: np.ndarray, yd: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def block(self, n: int) -> np.ndarray:
        x = _as_frames(self.src.block(n))
        y = np.empty_like(x)
        for lo in range(0, n, self.d):
            xc = x[lo : lo + self.d]
            k = len(xc)
            y[lo : lo + k] = self._chunk(xc, self._xs[:k], self._ys[:k])
            self._xs = np.concatenate([self._xs[k:], xc])
            self._ys = np.concatenate([self._ys[k:], y[lo : lo + k]])
        return _out(y, self.channels)


class Comb(_Delayed):
    """A feedback comb filter: the output fed back into itself delay seconds later, scaled by
    feedback, y[n] = x[n] + feedback * y[n - D].

    With a positive feedback the spectrum gets peaks at every multiple of 1 / delay Hz and dips
    halfway between them; a negative feedback puts the peaks at the odd multiples of
    1 / (2 delay). A peak is 1 / (1 - |feedback|) times the input, a dip 1 / (1 + |feedback|),
    so feedback 0.9 makes the peaks 25.6 dB above the dips and 20 dB above the input.
    """

    params = (Param("delay", "s", 1 / RATE, 2.0, "log"), Param("feedback", "", -0.999, 0.999))

    def __init__(self, src: Unit, delay: float, feedback: float):
        super().__init__(src, delay, feedback)

    def _chunk(self, x, xd, yd):
        return x + self.g * yd


class Allpass(_Delayed):
    """A Schroeder allpass filter: y[n] = -gain * x[n] + x[n - D] + gain * y[n - D].

    Every frequency keeps its level, so the spectrum's magnitude does not change; what changes
    is the time each frequency takes to come out, which smears a click into a short ring. Chains
    of them are the diffusers inside reverbs.
    """

    params = (Param("delay", "s", 1 / RATE, 2.0, "log"), Param("gain", "", -0.999, 0.999))

    def __init__(self, src: Unit, delay: float, gain: float):
        super().__init__(src, delay, gain)

    def _chunk(self, x, xd, yd):
        return -self.g * x + xd + self.g * yd


# Formant frequencies (Hz) of five vowels of an adult male voice, rounded from the averages of
# G. E. Peterson and H. L. Barney, "Control methods used in a study of the vowels" (1952).
_VOWELS = {
    "a": (730.0, 1_090.0, 2_440.0),
    "e": (530.0, 1_840.0, 2_480.0),
    "i": (270.0, 2_290.0, 3_010.0),
    "o": (570.0, 840.0, 2_410.0),
    "u": (300.0, 870.0, 2_240.0),
}
_FORMANT_Q = 8.0
_FORMANT_GAINS = (1.0, 0.5, 0.25)


class Formant(Unit):
    """Three band-passes in parallel at the formants of a vowel: the bands a vocal tract makes
    louder, which tell one vowel from another.

    The frequencies (Hz) are those of an adult male voice: a 730, 1090, 2440; e 530, 1840, 2480;
    i 270, 2290, 3010; o 570, 840, 2410; u 300, 870, 2240. Each band has q 8, so it is f / 8 Hz
    wide, and the three are mixed at 1, 0.5 and 0.25 (0, -6 and -12 dB). Everything outside the
    bands is cut, so a source with a rich spectrum (a saw, noise) is needed to hear the vowel.
    """

    @property
    def duration(self) -> float | None:
        """The source's plus the ringing of the lowest, longest-ringing formant band."""
        f = min(min(v) for v in _VOWELS.values())
        return _after(self.src.duration, float(LN60 * _FORMANT_Q / (np.pi * f)))

    def response(self, **kw):
        """This filter's gain over frequency, as a view."""
        from euterpe.view import response

        return response(self, **kw)

    def __init__(self, src: Unit, vowel: Literal["a", "e", "i", "o", "u"]):
        if vowel not in _VOWELS:
            raise ValueError(f"Formant vowel must be one of {', '.join(_VOWELS)}, got {vowel!r}")
        self.src, self.vowel = src, vowel
        self.channels = src.channels
        self._bands = [(_rbj("bandpass", f, _FORMANT_Q), g) for f, g in zip(_VOWELS[vowel], _FORMANT_GAINS)]
        self._sections = [_Section(self.channels, 2) for _ in self._bands]

    def inputs(self) -> list[Unit]:
        return [self.src]

    def reset(self) -> None:
        super().reset()
        for s in self._sections:
            s.reset()

    def block(self, n: int) -> np.ndarray:
        x = _as_frames(self.src.block(n))
        y = sum(g * s.run(b, a, x) for ((b, a), g), s in zip(self._bands, self._sections))
        return _out(y, self.channels)
