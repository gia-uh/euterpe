"""Spectrum helpers for the tests."""

import numpy as np

RATE = 48_000


def _power(x):
    x = np.asarray(x, np.float64)
    if x.ndim == 2:
        x = x.mean(axis=1)
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    return np.fft.rfftfreq(len(x), 1 / RATE), spectrum


def peak_hz(x) -> float:
    """The frequency of the strongest component, refined by a parabola through the top bin."""
    freqs, power = _power(x)
    k = int(np.argmax(power[1:-1])) + 1
    a, b, c = np.log(power[k - 1 : k + 2] + 1e-30)
    delta = 0.5 * (a - c) / (a - 2 * b + c)
    return float((k + delta) * (freqs[1] - freqs[0]))


def band_db(x, lo, hi) -> float:
    """The share of the signal's energy between lo and hi Hz, in dB (0 dB is all of it)."""
    freqs, power = _power(x)
    band = power[(freqs >= lo) & (freqs <= hi)].sum()
    return float(10 * np.log10(band / power.sum() + 1e-30))


from euterpe.instruments import Instrument  # noqa: E402
from euterpe.pitch import C4, C6, C7  # noqa: E402
from euterpe.sound import ADSR, Sine  # noqa: E402


class Theremin(Instrument):
    """A one-voice sine instrument for the tests: polyphony 1, playable C4 to C7."""

    polyphony = 1
    playable = (C4, C7)
    comfortable = (C4, C6)

    def voice(self, note):
        return Sine(note.freq) * ADSR(attack=0.01, release=0.05, gate=note.duration) * note.velocity * 0.5
