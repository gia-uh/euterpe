"""Percussion: drums, cymbals and timpani, struck by a stick, a hand or a mallet."""

from __future__ import annotations

from collections.abc import Hashable

import numpy as np

from euterpe.instruments.core import Articulation, Instrument, Note
from euterpe.pitch import Pitch


class Open(Articulation):
    """The hi-hat's open stroke: the cymbals held apart, so they ring. Other instruments ignore it."""


class Struck(Instrument):
    """The base of everything hit by a stick, a hand or a mallet. Nothing struck sustains: each
    voice dies on its own and rings past its written duration, unless a later hit on its
    resource stops it. Its techniques return notes: hit, roll and flam.

    tune: the drum's pitch in Hz; a note's pitch retunes one hit.
    level: the gain of one hit at full velocity.
    variation: how far each hit's force and brightness move, as a fraction; its tuning moves a
    tenth as far. Two hits are never quite the same.
    seed: which instrument of its make this is.
    """

    polyphony = 8
    tune: float = 100.0
    level: float = 0.5
    variation: float = 0.08
    seed: int = 0

    def resource(self, note: Note) -> Hashable | None:
        """The drum itself: a new hit stops the one still ringing on it."""
        return self

    def hit(self, at: float, velocity: float = 0.8, pitch: Pitch | float | None = None,
            articulation: Articulation | None = None) -> list[Note]:
        """One stroke at time at."""
        return [Note(at, self.tune if pitch is None else pitch, 0.1, velocity, articulation, resource=self)]

    def roll(self, at: float, length: float, velocity: float = 0.6, end: float | None = None,
             rate: float = 20.0, pitch: Pitch | float | None = None) -> list[Note]:
        """Strokes rate times a second from at for length seconds, the velocity moving in a
        straight line from velocity to end (by default it stays)."""
        if rate <= 0 or length <= 0:
            raise ValueError(f"roll needs a rate and a length above 0, got {rate} and {length}")
        n = max(1, int(np.ceil(length * rate - 1e-9)))
        end = velocity if end is None else end
        ramp = np.linspace(velocity, end, n)
        return [s for i in range(n) for s in self.hit(at + i / rate, float(ramp[i]), pitch)]

    def flam(self, at: float, velocity: float = 0.8, grace: float = 0.025,
             pitch: Pitch | float | None = None) -> list[Note]:
        """A soft grace stroke grace seconds before the main one; at 0 the main stroke moves later."""
        start = max(0.0, at - grace)
        return self.hit(start, velocity / 2, pitch) + self.hit(start + grace, velocity, pitch)

    def vary(self, note: Note) -> tuple[float, float, float]:
        """Factors for this hit's force, brightness and tuning; all 1 without variation."""
        v = self.variation
        if not v:
            return (1.0, 1.0, 1.0)
        a, b, c = note.rng.uniform(-1.0, 1.0, 3)
        return (float(1 + v * a), float(1 + v * b), float(1 + 0.1 * v * c))
