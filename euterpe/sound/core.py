"""Units, parameters, mixing and block rendering.

A unit is a stateful sound processor. It answers block(n) with its next n
samples, pulling from the units it was built on. render() asks the top unit
for fixed-size blocks, so the size of the blocks never changes the result.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal

import numpy as np

RATE = 48_000
BLOCK = 1024


@dataclass(frozen=True)
class Param:
    """A unit's parameter: its name, its physical unit, its range and its default."""

    name: str
    unit: str
    lo: float
    hi: float
    scale: Literal["lin", "log"] = "lin"
    default: float | None = None


class Unit(ABC):
    """A sound processor that keeps its own state and yields samples block by block."""

    params: ClassVar[tuple[Param, ...]] = ()
    channels: int = 1

    def _set_params(self, **values) -> None:
        known = {p.name: p for p in self.params}
        unknown = set(values) - set(known)
        if unknown:
            raise TypeError(f"{type(self).__name__} has no parameter {', '.join(sorted(unknown))}")
        self._values = {}
        for p in self.params:
            v = values.get(p.name, p.default)
            if v is None:
                raise TypeError(f"{type(self).__name__}.{p.name} is required")
            if not isinstance(v, Unit):
                v = float(v)
                if not p.lo <= v <= p.hi:
                    raise ValueError(
                        f"{type(self).__name__}.{p.name}={v} outside [{p.lo}, {p.hi}]"
                        + (f" {p.unit}" if p.unit else "")
                    )
            self._values[p.name] = v

    def _param(self, name: str, n: int) -> np.ndarray:
        v = self._values[name]
        if not isinstance(v, Unit):
            return np.full(n, v, np.float32)
        p = next(p for p in self.params if p.name == name)
        x = v.block(n)
        if x.ndim == 2:
            x = x.mean(axis=1)
        return np.clip(x, p.lo, p.hi).astype(np.float32)

    def inputs(self) -> list[Unit]:
        """The units this one pulls from: its modulated parameters and its sources."""
        return [v for v in getattr(self, "_values", {}).values() if isinstance(v, Unit)]

    def reset(self) -> None:
        """Return this unit and its inputs to their state before the first sample."""
        for u in self.inputs():
            u.reset()

    @abstractmethod
    def block(self, n: int) -> np.ndarray:
        """The next n samples: shape (n,) when mono, (n, 2) when stereo, float32."""

    def __add__(self, other: Unit | float) -> Mix:
        return Mix(self, _unit(other))

    def __radd__(self, other: Unit | float) -> Mix:
        return Mix(_unit(other), self)

    def __mul__(self, gain: Unit | float) -> Gain:
        return Gain(self, gain)

    __rmul__ = __mul__


def _unit(x: Unit | float) -> Unit:
    return x if isinstance(x, Unit) else Const(x)


class Const(Unit):
    """A constant value. Its spectrum is a single line at 0 Hz."""

    channels = 1

    def __init__(self, value: float):
        self.value = float(value)

    def block(self, n: int) -> np.ndarray:
        return np.full(n, self.value, np.float32)


class Mix(Unit):
    """The sum of its inputs, each scaled by its gain. The spectrum is the sum of their spectra.

    Stereo when any input is stereo; a mono input is copied to both sides.
    """

    def __init__(self, *units: Unit, gains: Sequence[float] | None = None):
        if gains is not None and len(gains) != len(units):
            raise ValueError(f"Mix got {len(units)} units and {len(gains)} gains")
        self.units = list(units)
        self.gains = [1.0] * len(units) if gains is None else [float(g) for g in gains]
        self.channels = 2 if any(u.channels == 2 for u in units) else 1

    def inputs(self) -> list[Unit]:
        return self.units

    def block(self, n: int) -> np.ndarray:
        out = np.zeros((n, 2) if self.channels == 2 else n, np.float32)
        for u, g in zip(self.units, self.gains):
            x = u.block(n)
            if self.channels == 2 and x.ndim == 1:
                x = x[:, None]
            out += np.float32(g) * x
        return out


class Gain(Unit):
    """Its source multiplied by a gain. A constant gain scales the spectrum; a moving gain
    (an envelope, a slow sine) spreads each component into sidebands at the gain's frequencies.
    """

    params = (Param("gain", "", -1e6, 1e6, default=1.0),)  # also scales modulators, in Hz

    def __init__(self, src: Unit, gain: float | Unit):
        self.src = src
        self.channels = src.channels
        self._set_params(gain=gain)

    def inputs(self) -> list[Unit]:
        return [self.src, *super().inputs()]

    def block(self, n: int) -> np.ndarray:
        x = self.src.block(n)
        g = self._param("gain", n)
        return x * (g[:, None] if x.ndim == 2 else g)


def rng(seed: int) -> np.random.Generator:
    """A random generator (PCG64) that yields the same numbers for the same seed."""
    return np.random.Generator(np.random.PCG64(seed))


def render(
    unit: Unit, seconds: float, *, to: str | Path | None = None, block: int = BLOCK
) -> np.ndarray | Path:
    """Reset the unit and pull round(seconds * RATE) frames from it, block by block.

    Returns the samples, or, with to, writes them to that file and returns its path.
    """
    if seconds < 0:
        raise ValueError(f"render needs seconds >= 0, got {seconds}")
    if block < 1:
        raise ValueError(f"render needs block >= 1, got {block}")
    unit.reset()
    total = round(seconds * RATE)
    parts = []
    done = 0
    while done < total:
        n = min(block, total - done)
        parts.append(np.asarray(unit.block(n), np.float32))
        done += n
    if parts:
        samples = np.concatenate(parts)
    else:
        samples = np.zeros((0, 2) if unit.channels == 2 else 0, np.float32)
    if to is None:
        return samples
    from euterpe.io import write

    return write(samples, to)
