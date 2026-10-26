"""A Clip: a sound rendered for a known number of seconds, ready to look at and listen to."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from euterpe.sound.core import RATE


class Clip:
    """Float32 samples, (n,) or (n, 2), at rate. defaulted is true when the length was the
    1 s default because the unit never ends, so a view can say so."""

    def __init__(self, samples: np.ndarray, rate: int = RATE, *, defaulted: bool = False):
        self.samples = np.asarray(samples, np.float32)
        self.rate = rate
        self.defaulted = defaulted

    @classmethod
    def read(cls, path: str | Path) -> Clip:
        from euterpe.io import read

        samples, rate = read(path)
        return cls(samples, rate)

    @property
    def seconds(self) -> float:
        return len(self.samples) / self.rate

    @property
    def channels(self) -> int:
        return 1 if self.samples.ndim == 1 else self.samples.shape[1]

    def __len__(self) -> int:
        return len(self.samples)

    def __array__(self, dtype=None, copy=None):
        return self.samples if dtype is None else self.samples.astype(dtype)

    def view(self):
        """The default view: what display() shows."""
        from euterpe.view import default

        return default(self)

    def waveform(self, **kw):
        from euterpe.view import waveform

        return waveform(self, **kw)

    def spectrum(self, **kw):
        from euterpe.view import spectrum

        return spectrum(self, **kw)

    def spectrogram(self, **kw):
        from euterpe.view import spectrogram

        return spectrogram(self, **kw)

    def level(self, **kw):
        from euterpe.view import level

        return level(self, **kw)

    def _repr_mimebundle_(self, include=None, exclude=None):
        return self.view()._repr_mimebundle_(include, exclude)

    def __repr__(self) -> str:
        peak = float(np.abs(self.samples).max()) if len(self.samples) else 0.0
        db = 20 * np.log10(peak) if peak > 0 else float("-inf")
        return f"Clip({self.seconds:g} s, peak {db:.1f} dBFS)"
