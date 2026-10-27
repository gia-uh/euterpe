"""Body: the resonances of an instrument's wooden body, driven by its string."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from euterpe.sound.core import Unit
from euterpe.sound.synth import Modal


class _Held(Unit):
    """The block its owner pulled last, so one source can drive Modal and the dry path."""

    def __init__(self, channels: int):
        self.channels = channels
        self.x = np.zeros(0, np.float32)

    def block(self, n: int) -> np.ndarray:
        return self.x


class Body(Unit):
    """A wooden body as a few resonant modes: src drives one resonator per mode, as in Modal,
    and the output is dry * src plus what the modes ring.

    freqs, decays, amps: each mode's frequency (Hz), its time to fall 60 dB (s) and its gain.
    dry: how much of the string reaches the ear directly.

    Its limit: a real body has hundreds of modes, spread and coupled; a few of them give the low
    resonance (the air in the box, the top plate) but not the body's whole colour.
    """

    def __init__(self, src: Unit, freqs: Sequence[float], decays: Sequence[float], amps: Sequence[float],
                 dry: float = 0.5):
        self.src = src
        self.dry = float(dry)
        self._held = _Held(src.channels)
        self._modes = Modal(freqs, decays, amps, excite=self._held)
        self.channels = src.channels

    def inputs(self) -> list[Unit]:
        return [self.src]

    def reset(self) -> None:
        super().reset()
        self._modes.reset()

    @property
    def duration(self) -> float | None:
        """The source's duration plus the slowest mode's decay."""
        d = self.src.duration
        return None if d is None else d + float(np.max(self._modes.decays))

    def block(self, n: int) -> np.ndarray:
        x = self.src.block(n)
        self._held.x = x
        return (self.dry * x + self._modes.block(n)).astype(np.float32)
