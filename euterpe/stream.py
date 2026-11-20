"""Rendering ahead in chunks, for music that has no end: the first piece of streaming.

A program that plays music while it runs, such as a game, cannot render a whole score: it
composes a few bars at a time and renders them before they are heard. chunks() asks a
compose function for each chunk's unit and renders it with a tail, so notes still ringing at
the chunk's end are not cut; join() adds the chunks at their starts, as the player does.

What chunking cannot keep: a voice that stops another across a seam. An instrument that
damps a ringing string when its next note takes the string cannot see a note of the next
chunk, so that string rings into the tail instead. Chunks of independent voices add up to
the samples of one long render.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from itertools import count

import numpy as np

from euterpe.sound.core import RATE, Unit, render


@dataclass
class Chunk:
    """A chunk's samples, length plus tail, and its start in seconds from the first chunk's."""

    start: float
    samples: np.ndarray


def chunks(compose: Callable[[int], tuple[Unit, float]], tail: float = 2.5) -> Iterator[Chunk]:
    """Chunk after chunk without end: compose(k) gives chunk k's unit, whose time 0 is the
    chunk's start, and its length in seconds. Each chunk renders length + tail seconds, and the
    next starts where this one's length ends."""
    start = 0.0
    for k in count():
        unit, length = compose(k)
        yield Chunk(start, render(unit, length + tail))
        start += length


def join(parts: Iterable[Chunk], seconds: float) -> np.ndarray:
    """The chunks added at their starts, cut at seconds."""
    total = round(seconds * RATE)
    out = None
    for c in parts:
        if out is None:
            out = np.zeros((total,) + c.samples.shape[1:], np.float32)
        a = round(c.start * RATE)
        if a >= total:
            continue
        x = c.samples[: total - a]
        out[a:a + len(x)] += x
    return out if out is not None else np.zeros(total, np.float32)
