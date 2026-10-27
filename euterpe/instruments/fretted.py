"""Fretted instruments: a hand on a fingerboard, written as shapes, tabs or plain pitches."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from euterpe.instruments.core import Control, Note
from euterpe.instruments.plucked import (
    BassBody,
    Exciter,
    Finger,
    GuitarBody,
    Plectrum,
    Plucked,
    Soundboard,
    Steel,
    String,
)
from euterpe.pitch import A1, A2, B3, D2, D3, E1, E2, E4, G2, G3, Pitch
from euterpe.sound.core import RATE


@dataclass(frozen=True, init=False)
class Shape:
    """A hand position: one fret per string in tab order, from the lowest string to the highest,
    None for a string not played. Shape(None, 0, 2, 2, 2, 0) is the A chord, x02220."""

    frets: tuple[int | None, ...]

    def __init__(self, *frets: int | None):
        object.__setattr__(self, "frets", tuple(frets))

    def __repr__(self) -> str:
        return f"Shape({', '.join(map(repr, self.frets))})"


class Fretted(Plucked):
    """A plucked instrument whose strings are stopped on frets. A subclass sets tuning (the open
    strings, lowest first) and frets (how many). Strings are numbered as players do: 1 is the
    highest. A note's resource is its string; a note written as a pitch alone gets one in
    perform. The capo raises every string, and frets in a shape or a tab count from it.
    """

    tuning: ClassVar[tuple[Pitch, ...]] = ()
    frets: ClassVar[int] = 0

    def __init__(self, capo: int = 0, exciter: Exciter = Finger(), string: String = Steel(),
                 body: Soundboard | None = GuitarBody(), let_ring: bool = True, mute: float = 0.08,
                 level: float = 0.25):
        super().__init__(exciter, string, body, let_ring, mute, level)
        if not 0 <= capo < self.frets:
            raise ValueError(f"capo {capo} is not a fret of {type(self).__name__} (0 to {self.frets - 1})")
        self.capo = capo
        self.playable = (self.tuning[0] + capo, self.tuning[-1] + self.frets)
        self.comfortable = (self.tuning[0] + capo, self.tuning[-1] + 12)

    def _open(self, string: int) -> Pitch:
        """The pitch of string (1 the highest) played open, with the capo."""
        return self.tuning[len(self.tuning) - string] + self.capo

    def _fret(self, pitch: Pitch, string: int) -> int | None:
        """The fret (from the capo) that plays pitch on string, or None if the string cannot."""
        fret = pitch - self._open(string)
        return fret if 0 <= fret <= self.frets - self.capo else None

    def pitches(self, shape: Shape) -> list[Pitch]:
        """The pitches a shape sounds, lowest string first."""
        self._check(shape)
        return [p for _, p in self._sounding(shape)]

    def shape(self, pitches: Sequence[Pitch | float]) -> Shape:
        """A shape that plays pitches: each, from the lowest, on the next free string above the
        previous one where its fret is lowest."""
        n = len(self.tuning)
        frets: list[int | None] = [None] * n
        last = n + 1  # the string the previous pitch went on; the next goes on a higher one
        for p in sorted((_pitch(p) for p in pitches), key=lambda p: p.number):
            options = [(f, s) for s in range(last - 1, 0, -1) if (f := self._fret(p, s)) is not None]
            if not options:
                raise ValueError(f"no string of {type(self).__name__} is left for {p!r} in {list(pitches)}")
            fret, last = min(options, key=lambda o: (o[0], -o[1]))
            frets[n - last] = fret
        return Shape(*frets)

    def strum(self, chord: Shape | Sequence[Pitch | float], at: float, length: float, up: bool = False,
              strings: int | None = None, velocity: float = 0.8, spread: float = 0.012) -> list[Note]:
        """One strum: down from the lowest sounding string to the highest, up the other way,
        spread seconds between strings. strings: only that many of the highest sounding strings."""
        shape = chord if isinstance(chord, Shape) else self.shape(chord)
        self._check(shape)
        sounding = self._sounding(shape)
        if strings is not None:
            sounding = sounding[-strings:]
        if up:
            sounding = sounding[::-1]
        return [Note(at + k * spread, p, length, velocity, resource=s) for k, (s, p) in enumerate(sounding)]

    def pick(self, string: int, fret: int, at: float, length: float, velocity: float = 0.8) -> list[Note]:
        """One note from a tab: string (1 the highest) at fret (0 open, counted from the capo)."""
        if not 1 <= string <= len(self.tuning):
            raise ValueError(f"{type(self).__name__} has strings 1 to {len(self.tuning)}, not {string}")
        if not 0 <= fret <= self.frets - self.capo:
            raise ValueError(f"fret {fret} is not on {type(self).__name__} (0 to {self.frets - self.capo})")
        return [Note(at, self._open(string) + fret, length, velocity, resource=string)]

    def perform(self, notes: list[Note], controls: list[Control]) -> list[Note]:
        """Give a string to each note written without one. Notes that start together are placed
        as a shape. A lone note goes where it costs least: an open string costs nothing, a fret
        its distance from the hand (the last fretted note's fret); ties go to the lower string."""
        hand = 0
        i = 0
        while i < len(notes):
            j = i
            while j < len(notes) and round(notes[j].time * RATE) == round(notes[i].time * RATE):
                j += 1
            group = notes[i:j]
            free = [n for n in group if n.resource is None]
            if len(free) > 1:
                try:
                    shape = self.shape([n.pitch for n in free])
                except ValueError:
                    shape = None
                if shape is not None:
                    by_pitch = {}
                    for s, p in self._sounding(shape):
                        by_pitch.setdefault(p, []).append(s)
                    for n in sorted(free, key=lambda n: _pitch(n.pitch).number):
                        n.resource = by_pitch[_pitch(n.pitch)].pop(0)
            used = {n.resource for n in group if n.resource is not None}
            for n in group:
                if n.resource is None:
                    p = _pitch(n.pitch)
                    options = [(0 if f == 0 else abs(f - hand), -s, s) for s in range(1, len(self.tuning) + 1)
                               if s not in used and (f := self._fret(p, s)) is not None]
                    if options:
                        n.resource = min(options)[2]
                        used.add(n.resource)
                if n.resource is not None and 1 <= n.resource <= len(self.tuning):
                    f = self._fret(_pitch(n.pitch), n.resource)
                    if f:
                        hand = f
            i = j
        return notes

    def _check(self, shape: Shape) -> None:
        if len(shape.frets) != len(self.tuning):
            raise ValueError(f"{shape!r} has {len(shape.frets)} frets; {type(self).__name__} has "
                             f"{len(self.tuning)} strings")

    def _sounding(self, shape: Shape) -> list[tuple[int, Pitch]]:
        """(string, pitch) for each string the shape plays, lowest string first."""
        n = len(self.tuning)
        return [(n - i, self.tuning[i] + self.capo + f) for i, f in enumerate(shape.frets) if f is not None]


def _pitch(p: Pitch | float) -> Pitch:
    """A Pitch, or the nearest one to a frequency in Hz."""
    return p if isinstance(p, Pitch) else Pitch(round(69 + 12 * math.log2(float(p) / 440.0)))


class Guitar(Fretted):
    """A steel-string acoustic guitar: six strings tuned E2 A2 D3 G3 B3 E4, 19 frets, played
    with a plectrum, through a guitar body. Guitar(string=Nylon(), exciter=Finger()) is a
    classical guitar played with the fingers.

    Techniques: strum(chord, at, length, up=False, strings=None) and pick(string, fret, at,
    length). A chord is a Shape or a list of pitches; plain pitches get their strings in perform.

    Limit: one string model with a four-mode body; the strings do not couple through the bridge,
    and there are no fret noises, slides, bends or hammer-ons.
    """

    tuning = (E2, A2, D3, G3, B3, E4)
    frets = 19
    polyphony = 6

    def __init__(self, capo: int = 0, exciter: Exciter = Plectrum(), string: String = Steel(),
                 body: Soundboard | None = GuitarBody(), let_ring: bool = True, mute: float = 0.08,
                 level: float = 0.25):
        super().__init__(capo, exciter, string, body, let_ring, mute, level)


class BassGuitar(Fretted):
    """An acoustic bass guitar: four strings tuned E1 A1 D2 G2, 20 frets, played with the
    fingers, through a bass body.

    Limit: the low strings' stiffness is not modelled, so the upper partials sit exactly in
    tune, and the body's three modes give less boom than a real box.
    """

    tuning = (E1, A1, D2, G2)
    frets = 20
    polyphony = 4

    def __init__(self, capo: int = 0, exciter: Exciter = Finger(position=0.15), string: String = Steel(damping=0.998),
                 body: Soundboard | None = BassBody(), let_ring: bool = True, mute: float = 0.08,
                 level: float = 0.3):
        super().__init__(capo, exciter, string, body, let_ring, mute, level)
