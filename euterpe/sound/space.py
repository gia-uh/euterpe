"""Delay, modulation effects and space.

Delay and the moving delays (chorus, flanger) add copies of the source later in time. A phaser
shifts the phase of each frequency by a moving amount. The reverbs add thousands of echoes, as
a room does. Pan and Width place a sound between two speakers.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import hadamard
from scipy.fft import irfft, next_fast_len, rfft
from scipy.signal import lfilter

from euterpe.sound.core import RATE, Param, Unit, rng
from euterpe.sound.osc import Sine

_RATE = ("Hz", 0.01, 20.0, "log")
_MIX = Param("mix", "", 0.0, 1.0, default=0.5)
_GRID = 64  # a phaser's sweep is read once per this many samples, counted from the start


def _frames(x: np.ndarray) -> np.ndarray:
    return x.astype(np.float64).reshape(len(x), -1)


def _out(y: np.ndarray, channels: int) -> np.ndarray:
    return (y if channels == 2 else y[:, 0]).astype(np.float32)


def _p64(unit: Unit, name: str, n: int) -> np.ndarray:
    """A parameter's next n values in float64; a constant keeps its exact value."""
    v = unit._values[name]
    return unit._param(name, n).astype(np.float64) if isinstance(v, Unit) else np.full(n, v)


def _numbers(unit: str, **values) -> None:
    for name, v in values.items():
        if isinstance(v, Unit):
            raise TypeError(f"{unit}.{name} must be a number, not a Unit")


class _Moving(Unit):
    """A delay line whose length may change every sample, read with linear interpolation.

    Each written sample is the input plus feedback times the delayed one, and the output is
    (1 - mix) * input + mix * delayed. It runs in chunks shorter than the shortest delay in
    them, so every read comes from samples already written.
    """

    _lfo: Unit | None = None

    def __init__(self, src: Unit, longest: float, **values):
        self.src = src
        self.channels = src.channels
        self._set_params(**values)
        self._cap = int(np.ceil(longest * RATE)) + 2
        self.reset()

    def inputs(self) -> list[Unit]:
        own = [v for k, v in self._values.items() if isinstance(v, Unit) and k != "rate"]
        return [self.src, *([self._lfo] if self._lfo else []), *own]

    def reset(self) -> None:
        super().reset()
        self._ring = np.zeros((self._cap, self.channels))
        self._done = 0

    def _delay(self, n: int) -> np.ndarray:
        """The delay, in samples, for each of the next n samples."""
        raise NotImplementedError

    def _feedback(self, n: int) -> np.ndarray:
        return np.zeros(n)

    def block(self, n: int) -> np.ndarray:
        x = _frames(self.src.block(n))
        d = self._delay(n)
        fb = self._feedback(n)[:, None]
        mix = _p64(self, "mix", n)[:, None]
        wet = np.empty_like(x)
        i = 0
        while i < n:
            size = n - i
            size = max(1, min(size, int(np.floor(d[i : i + size].min())) - 1))
            now = self._done + i + np.arange(size)
            at = now - d[i : i + size]
            k = np.floor(at).astype(np.int64)
            frac = (at - k)[:, None]
            w = (1 - frac) * self._ring[k % self._cap] + frac * self._ring[(k + 1) % self._cap]
            wet[i : i + size] = w
            self._ring[now % self._cap] = x[i : i + size] + fb[i : i + size] * w
            i += size
        self._done += n
        return _out((1 - mix) * x + mix * wet, self.channels)


class Delay(_Moving):
    """An echo: the source again time seconds later, and with feedback, again and again, each
    repeat feedback times the one before.

    Adding a copy delayed by T seconds makes a comb in the spectrum: peaks at multiples of 1 / T
    Hz and dips between them. With T above about 50 ms the ear hears a separate echo instead of
    a change of tone. A moving time bends the pitch of the echoes, like a tape machine.
    """

    params = (
        Param("time", "s", 0.001, 4.0, "log", default=0.25),
        Param("feedback", "", -0.99, 0.99, default=0.3),
        Param("mix", "", 0.0, 1.0, default=0.3),
    )

    def __init__(
        self, src: Unit, time: float | Unit = 0.25, feedback: float | Unit = 0.3, mix: float | Unit = 0.3
    ):
        longest = self.params[0].hi if isinstance(time, Unit) else float(time)
        super().__init__(src, longest, time=time, feedback=feedback, mix=mix)

    def _delay(self, n: int) -> np.ndarray:
        return _p64(self, "time", n) * RATE

    def _feedback(self, n: int) -> np.ndarray:
        return _p64(self, "feedback", n)


class Chorus(_Moving):
    """The source mixed with a copy delayed by 20 ms, plus or minus depth seconds, the delay
    swinging rate times a second.

    The moving delay raises and lowers the copy's pitch a little, so the two sound like two
    players slightly out of tune: the comb of a 20 ms delay (peaks every 50 Hz) moves, and the
    tone thickens without a heard echo.
    """

    params = (Param("rate", *_RATE, default=0.8), Param("depth", "s", 0.0, 0.01, default=0.003), _MIX)

    def __init__(self, src: Unit, rate: float | Unit = 0.8, depth: float | Unit = 0.003, mix: float | Unit = 0.5):
        self._lfo = Sine(rate)
        super().__init__(src, 0.03, rate=rate, depth=depth, mix=mix)

    def _delay(self, n: int) -> np.ndarray:
        lfo = self._lfo.block(n).astype(np.float64)
        return (0.02 + _p64(self, "depth", n) * lfo) * RATE


class Flanger(_Moving):
    """The source mixed with a copy delayed by 0.5 ms to 0.5 ms + depth seconds, the delay
    sweeping rate times a second, part of the output fed back.

    A delay of T seconds puts peaks at multiples of 1 / T Hz: at 0.5 ms every 2000 Hz, at
    2.5 ms every 400 Hz. Sweeping T slides the whole comb up and down the spectrum, the
    "jet plane" sweep. feedback deepens the peaks; a negative one moves them to the odd
    multiples of 1 / (2T).
    """

    params = (
        Param("rate", *_RATE, default=0.3),
        Param("depth", "s", 0.0, 0.01, default=0.002),
        Param("feedback", "", -0.95, 0.95, default=0.5),
        _MIX,
    )

    def __init__(
        self,
        src: Unit,
        rate: float | Unit = 0.3,
        depth: float | Unit = 0.002,
        feedback: float | Unit = 0.5,
        mix: float | Unit = 0.5,
    ):
        self._lfo = Sine(rate)
        super().__init__(src, 0.011, rate=rate, depth=depth, feedback=feedback, mix=mix)

    def _delay(self, n: int) -> np.ndarray:
        lfo = self._lfo.block(n).astype(np.float64)
        return (0.0005 + _p64(self, "depth", n) * (lfo + 1) / 2) * RATE

    def _feedback(self, n: int) -> np.ndarray:
        return _p64(self, "feedback", n)


class Phaser(Unit):
    """The source mixed with itself through a chain of stages first-order allpass filters, whose
    turning frequency sweeps from 200 Hz to 2000 Hz and back rate times a second.

    Each allpass keeps every level and delays the phase, by 90 degrees at its turning frequency.
    Where the chain's delay is 180 degrees (or 540, ...) the copy cancels the source: stages / 2
    notches, which move with the sweep. Unlike a flanger's comb, the notches are few and not
    evenly spaced. stages is a number (1 to 12) because it sets the chain.
    """

    params = (Param("rate", *_RATE, default=0.5), Param("stages", "", 1.0, 12.0, default=4.0), _MIX)

    def __init__(self, src: Unit, rate: float | Unit = 0.5, stages: int = 4, mix: float | Unit = 0.5):
        _numbers("Phaser", stages=stages)
        self.src = src
        self.channels = src.channels
        self._set_params(rate=rate, stages=stages, mix=mix)
        self._lfo = Sine(rate)
        self._stages = round(self._values["stages"])
        self.reset()

    def inputs(self) -> list[Unit]:
        return [self.src, self._lfo, *([self._values["mix"]] if isinstance(self._values["mix"], Unit) else [])]

    def reset(self) -> None:
        super().reset()
        self._zi = [np.zeros((1, self.channels)) for _ in range(self._stages)]
        self._done = 0
        self._a = 0.0

    def block(self, n: int) -> np.ndarray:
        x = _frames(self.src.block(n))
        f = 200.0 * 10 ** ((self._lfo.block(n).astype(np.float64) + 1) / 2)
        t = np.tan(np.pi * f / RATE)
        coeff = (t - 1) / (t + 1)
        mix = _p64(self, "mix", n)[:, None]
        first = (-self._done) % _GRID
        cuts = [0, *range(first, n, _GRID), n]
        y = np.empty_like(x)
        for lo, hi in zip(cuts, cuts[1:]):
            if lo == hi:
                continue
            if (self._done + lo) % _GRID == 0:
                self._a = coeff[lo]
            part = x[lo:hi]
            for s in range(self._stages):
                part, self._zi[s] = lfilter([self._a, 1.0], [1.0, self._a], part, axis=0, zi=self._zi[s])
            y[lo:hi] = part
        self._done += n
        return _out((1 - mix) * x + mix * y, self.channels)


def _mono(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float64)
    return x.mean(axis=1) if x.ndim == 2 else x


def _wet(dry: np.ndarray, wet: np.ndarray, mix: np.ndarray) -> np.ndarray:
    dry = _frames(dry)
    mix = mix.astype(np.float64)[:, None]
    return ((1 - mix) * dry + mix * wet).astype(np.float32)


_FDN_TIMES = np.geomspace(0.03, 0.09, 8)  # the eight delay lines, in seconds at size 1


class FDNReverb(Unit):
    """A feedback delay network: eight delay lines whose outputs are mixed by an 8 x 8 Hadamard
    matrix and fed back in, so each echo splits into eight, and the echoes soon blur into a
    smooth tail. Stereo out; a stereo source is mixed to mono first.

    decay is the RT60, the seconds the tail takes to fall 60 dB: each line's gain is set from
    its length so that every trip around the loop loses the same dB per second. size scales the
    line lengths, 30 to 90 ms at size 1 (each moved up to 10 % by the seed): a bigger size is a
    bigger room, with sparser early echoes. damping is a one-pole lowpass in each line, so high
    frequencies die faster than low ones, as in a room with soft walls; decay holds for the low
    frequencies. decay, size, damping and seed are numbers, since they set the lines.
    """

    params = (
        Param("decay", "s", 0.1, 20.0, "log", default=2.0),
        Param("size", "", 0.1, 1.0, default=0.7),
        Param("damping", "", 0.0, 0.95, default=0.3),
        Param("mix", "", 0.0, 1.0, default=0.25),
    )
    channels = 2

    def __init__(
        self,
        src: Unit,
        decay: float = 2.0,
        size: float = 0.7,
        damping: float = 0.3,
        mix: float | Unit = 0.25,
        seed: int = 0,
    ):
        _numbers("FDNReverb", decay=decay, size=size, damping=damping)
        self.src = src
        self._set_params(decay=decay, size=size, damping=damping, mix=mix)
        jitter = 1 + 0.1 * rng(seed).uniform(-1.0, 1.0, 8)
        self._len = np.round(_FDN_TIMES * jitter * self._values["size"] * RATE).astype(np.int64)
        self._gain = 10 ** (-3 * self._len / (RATE * self._values["decay"]))
        self._h = hadamard(8) / np.sqrt(8)
        self._sign = self._h[1] * np.sqrt(8)  # +1 and -1, so the input reaches every line
        self._taps = self._h[[2, 4]].T  # two orthogonal mixes of the lines, left and right
        self._cap = int(self._len.max()) + 1
        self.reset()

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def reset(self) -> None:
        super().reset()
        self._ring = np.zeros((self._cap, 8))
        self._zi = np.zeros((1, 8))
        self._done = 0

    def block(self, n: int) -> np.ndarray:
        dry = self.src.block(n)
        x = _mono(dry)
        d = self._values["damping"]
        wet = np.empty((n, 2))
        lines = np.arange(8)
        i = 0
        while i < n:
            size = min(n - i, int(self._len.min()))
            now = self._done + i + np.arange(size)
            read = self._ring[(now[:, None] - self._len[None, :]) % self._cap, lines]
            read, self._zi = lfilter([1 - d], [1.0, -d], read, axis=0, zi=self._zi)
            wet[i : i + size] = read @ self._taps
            self._ring[now % self._cap] = (read * self._gain) @ self._h.T + x[i : i + size, None] * self._sign
            i += size
        self._done += n
        return _wet(dry, wet, self._param("mix", n))


_PART = 512  # the partition length of the convolution, in samples


class ConvolutionReverb(Unit):
    """A reverb made by convolution with a synthesized impulse response: stereo white noise
    (one independent noise per side, from the seed) that falls 60 dB in decay seconds and lasts
    1.5 times that.

    Convolving with an impulse response plays one copy of it for every input sample, so each
    sound gets a dense, smooth tail with the same decay at every frequency: the spectrum of the
    source, spread in time. Each side of the response has an energy of 1, so a wide-band source
    keeps about its level. The first 512 samples of the response are convolved directly; the
    rest in 512-sample partitions with FFTs, so FFT rounding makes the samples differ by about
    1e-7 between block sizes. decay and seed are numbers, since they make the response.
    """

    params = (Param("decay", "s", 0.1, 10.0, "log", default=2.0), Param("mix", "", 0.0, 1.0, default=0.25))
    channels = 2

    def __init__(self, src: Unit, decay: float = 2.0, mix: float | Unit = 0.25, seed: int = 0):
        _numbers("ConvolutionReverb", decay=decay)
        self.src = src
        self._set_params(decay=decay, mix=mix)
        t = np.arange(round(1.5 * self._values["decay"] * RATE)) / RATE
        h = rng(seed).standard_normal((len(t), 2)) * np.exp(-3 * np.log(10) * t / self._values["decay"])[:, None]
        h /= np.sqrt((h**2).sum(axis=0))
        parts = -(-len(h) // _PART)
        h = np.concatenate([h, np.zeros((parts * _PART - len(h), 2))])
        self._head = h[:_PART]
        # the rest of the response, one spectrum per partition, each zero-padded to two partitions
        rest = h[_PART:].reshape(parts - 1, _PART, 2)
        self._parts = np.ascontiguousarray(rfft(rest, 2 * _PART, axis=1).transpose(1, 0, 2))  # (f, j, side)
        self.reset()

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def reset(self) -> None:
        super().reset()
        self._history = np.zeros(_PART - 1)  # the last inputs, for the directly convolved head
        self._seg = np.zeros(2 * _PART)  # the previous partition of input, then the current one
        # the last J input spectra, twice over so that columns p .. p + J are newest first
        self._fdl = np.zeros((_PART + 1, 2 * self._parts.shape[1]), complex)
        self._rest = np.zeros((_PART, 2))  # the rest's output for the current partition
        self._done = 0

    def block(self, n: int) -> np.ndarray:
        dry = self.src.block(n)
        x = _mono(dry)
        both = np.concatenate([self._history, x])
        head = np.stack([np.convolve(both, self._head[:, c], "valid") for c in (0, 1)], axis=1)
        self._history = both[len(both) - (_PART - 1) :]
        rest = np.empty((n, 2))
        i = 0
        while i < n:
            at = self._done % _PART
            size = min(n - i, _PART - at)
            self._seg[_PART + at : _PART + at + size] = x[i : i + size]
            rest[i : i + size] = self._rest[at : at + size]
            i += size
            self._done += size
            if self._done % _PART == 0:
                # input partition s is complete. Output partition s + 1 is the sum over j of
                # input partition s - j times response partition j (overlap-save).
                parts = self._parts.shape[1]
                p = -(self._done // _PART) % parts
                self._fdl[:, p] = self._fdl[:, p + parts] = rfft(self._seg)
                spectrum = np.matmul(self._fdl[:, None, p : p + parts], self._parts)[:, 0]
                self._rest = irfft(spectrum, 2 * _PART, axis=0)[_PART:]
                self._seg[:_PART] = self._seg[_PART:]
        return _wet(dry, head + rest, self._param("mix", n))


class Pan(Unit):
    """Places a mono source between two speakers: pos -1 is left, 0 the middle, 1 right.

    Constant power: the left gain is cos(θ) and the right sin(θ), θ = (pos + 1) π / 4, so
    left² + right² = 1 and the sound keeps its loudness as it moves; in the middle each side is
    at 0.707 (-3 dB). The spectrum of each side is the source's, scaled. A stereo source is
    balanced instead: each side scaled by √2 times its gain, at most 1, so pos 0 leaves it
    unchanged.
    """

    params = (Param("pos", "", -1.0, 1.0, default=0.0),)
    channels = 2

    def __init__(self, src: Unit, pos: float | Unit = 0.0):
        self.src = src
        self._set_params(pos=pos)

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def block(self, n: int) -> np.ndarray:
        x = self.src.block(n).astype(np.float64)
        theta = (_p64(self, "pos", n) + 1) * np.pi / 4
        g = np.stack([np.cos(theta), np.sin(theta)], axis=1)
        if x.ndim == 2:
            return (x * np.minimum(np.sqrt(2) * g, 1.0)).astype(np.float32)
        return (x[:, None] * g).astype(np.float32)


class Width(Unit):
    """Makes a stereo sound narrower or wider: width 0 is mono, 1 unchanged, 2 twice as wide.

    It splits the sound into mid, (L + R) / 2, what both sides share, and side, (L - R) / 2,
    where they differ, scales the side by width and adds them back: L = M + S, R = M - S. Each
    side's spectrum changes only where the two sides differ. A mono source has no side, so it
    comes out the same on both sides at any width.
    """

    params = (Param("width", "", 0.0, 2.0, default=1.0),)
    channels = 2

    def __init__(self, src: Unit, width: float | Unit = 1.0):
        self.src = src
        self._set_params(width=width)

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def block(self, n: int) -> np.ndarray:
        x = _frames(self.src.block(n))
        if x.shape[1] == 1:
            return np.repeat(x, 2, axis=1).astype(np.float32)
        mid = (x[:, 0] + x[:, 1]) / 2
        side = (x[:, 0] - x[:, 1]) / 2 * _p64(self, "width", n)
        return np.stack([mid + side, mid - side], axis=1).astype(np.float32)
