"""Fretted instruments: a hand on a fingerboard, written as shapes, tabs or plain pitches."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import permutations
from typing import ClassVar

from euterpe.instruments.core import Control, Feedback, Note
from euterpe.instruments.plucked import (
    BassBody,
    Bridge,
    Exciter,
    Finger,
    GuitarBody,
    Neck,
    Pickup,
    Plectrum,
    Plucked,
    Soundboard,
    Steel,
    String,
    _string_of,
)
from euterpe.pitch import A1, A2, B3, D2, D3, E1, E2, E4, G2, G3, Pitch
from euterpe.sound import ADSR, Pluck, Segments, Sine
from euterpe.sound.core import RATE, Unit


@dataclass(frozen=True, init=False)
class Shape:
    """A hand position: one fret per string in tab order, from the lowest string to the highest,
    None for a string not played. Shape(None, 0, 2, 2, 2, 0) is the A chord, x02220."""

    frets: tuple[int | None, ...]

    def __init__(self, *frets: int | None):
        object.__setattr__(self, "frets", tuple(frets))

    def __repr__(self) -> str:
        return f"Shape({', '.join(map(repr, self.frets))})"

    def view(self, normalize: bool = True, caption: str | None = None, id: str | None = None):
        """The chord diagram over the shape strummed down once on Guitar(), 2 s."""
        from euterpe.view.special import chord
        from euterpe.view.widget import Widget

        guitar = Guitar()
        clip = guitar.play(guitar.strum(self, at=0.0, length=2.0)).take(2.0)
        return Widget(clip, caption=caption, id=id, normalize=normalize, special=chord(self, guitar.tuning))

    def _repr_mimebundle_(self, include=None, exclude=None):
        return self.view()._repr_mimebundle_(include, exclude)


class Fretted(Plucked):
    """A plucked instrument whose strings are stopped on frets. A subclass sets frets (how many)
    and its standard tuning (the open strings in tab order, from the lowest string), which
    tuning= replaces. Strings are numbered as players do: 1 is the last in tab order. A note's
    resource is its string; a note written as a pitch alone gets one in perform. The capo raises
    every string, and frets in a shape or a tab count from it.
    """

    tuning: tuple[Pitch, ...] = ()
    frets: ClassVar[int] = 0

    def __init__(self, tuning: Sequence[Pitch] | None = None, capo: int = 0, exciter: Exciter = Finger(),
                 string: String = Steel(), body: Soundboard | None = GuitarBody(), let_ring: bool = True,
                 mute: float = 0.08, level: float = 0.25, seed: int = 0):
        super().__init__(exciter, string, body, let_ring, mute, level, seed)
        if not 0 <= capo < self.frets:
            raise ValueError(f"capo {capo} is not a fret of {type(self).__name__} (0 to {self.frets - 1})")
        self.tuning = tuple(tuning) if tuning is not None else type(self).tuning
        self.capo = capo
        low = min(self.tuning, key=lambda p: p.number)
        high = max(self.tuning, key=lambda p: p.number)
        self.playable = (low + capo, high + self.frets)
        self.comfortable = (low + capo, high + 12)

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
        """A shape that plays pitches, one string each, nearest the nut."""
        frets: list[int | None] = [None] * len(self.tuning)
        for p, s in zip(pitches, self._solve(pitches)):
            frets[len(self.tuning) - s] = self._fret(_pitch(p), s)
        return Shape(*frets)

    def _solve(self, pitches: Sequence[Pitch | float], used: frozenset[int] = frozenset(), hand: int = 0) -> list[int]:
        """A string for each pitch, the lowest pitch on the lowest open string, all on different
        strings, the fretted ones within a span of 4 frets; of those, the one whose farthest fret
        is nearest the hand, then the narrowest, then the one with most open strings."""
        order = sorted(range(len(pitches)), key=lambda k: _pitch(pitches[k]).number)
        strings = sorted((s for s in range(1, len(self.tuning) + 1) if s not in used),
                         key=lambda s: (self._open(s).number, -s))
        best, best_cost = None, None
        for chosen in permutations(strings, len(order)):
            if any(self._open(a).number > self._open(b).number for a, b in zip(chosen, chosen[1:])):
                continue
            frets = [self._fret(_pitch(pitches[k]), s) for k, s in zip(order, chosen)]
            if None in frets:
                continue
            fretted = [f for f in frets if f > 0]
            span = max(fretted) - min(fretted) if fretted else 0
            if span > 4:
                continue
            cost = (max((abs(f - hand) for f in fretted), default=0), span, frets.count(0) * -1, [-s for s in chosen])
            if best_cost is None or cost < best_cost:
                best, best_cost = chosen, cost
        if best is None:
            names = [repr(_pitch(p)) for p in pitches]
            missing = next((n for n, p in zip(names, pitches)
                            if all(self._fret(_pitch(p), s) is None for s in strings)), None)
            raise ValueError(f"no string of {type(self).__name__} is left for {missing or ', '.join(names)} "
                             f"in {names}")
        result = [0] * len(pitches)
        for k, s in zip(order, best):
            result[k] = s
        return result

    def strum(self, chord: Shape | Sequence[Pitch | float], at: float, length: float, up: bool = False,
              strings: int | None = None, velocity: float = 0.8, spread: float = 0.012) -> list[Note]:
        """One strum: down from the lowest sounding string to the highest, up the other way,
        spread seconds between strings. strings: only that many of the highest sounding strings."""
        if strings is not None and strings < 1:
            raise ValueError(f"strum needs strings of at least 1, got {strings}")
        if isinstance(chord, Shape):
            self._check(chord)
            sounding = self._sounding(chord)
        else:  # keep each pitch as written, Hz included; the solver only picks the strings
            sounding = sorted(zip(self._solve(chord), chord), key=lambda sp: -sp[0])
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
            used = {n.resource for n in group if n.resource is not None}
            if len(free) > 1:
                try:
                    for n, s in zip(free, self._solve([n.pitch for n in free], frozenset(used), hand)):
                        n.resource = s
                except ValueError:
                    pass  # placed one by one below
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
        for f in shape.frets:
            if f is not None and not 0 <= f <= self.frets - self.capo:
                raise ValueError(f"{shape!r}: fret {f} is not on {type(self).__name__} (0 to {self.frets - self.capo})")

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

    def __init__(self, tuning: Sequence[Pitch] | None = None, capo: int = 0, exciter: Exciter = Plectrum(),
                 string: String = Steel(), body: Soundboard | None = GuitarBody(), let_ring: bool = True,
                 mute: float = 0.08, level: float = 0.75, seed: int = 0):
        super().__init__(tuning, capo, exciter, string, body, let_ring, mute, level, seed)


class BassGuitar(Fretted):
    """An acoustic bass guitar: four strings tuned E1 A1 D2 G2, 20 frets, played with the
    fingers, through a bass body. As a bass player does, it damps each note when the next one
    is due (let_ring=False), and its finger varies each pluck by 0.15. Its strings lose
    5 % of their vibration each trip (damping=0.95): a low string makes few trips a second, so
    a gentler damping would let it ring almost unchanged and run each note into the next.

    Limit: the least convincing preset of its family. The low strings' stiffness is not
    modelled, so the upper partials sit exactly in tune; there is no thump of the finger at the
    attack, which carries much of what the ear recognises; and the body's three modes give less
    boom than a real box.
    """

    tuning = (E1, A1, D2, G2)
    frets = 20
    polyphony = 4

    def __init__(self, tuning: Sequence[Pitch] | None = None, capo: int = 0,
                 exciter: Exciter = Finger(position=0.15, brightness=0.5, variation=0.15), string: String = Steel(damping=0.95),
                 body: Soundboard | None = BassBody(), let_ring: bool = False, mute: float = 0.06,
                 level: float = 1.1, seed: int = 0):
        super().__init__(tuning, capo, exciter, string, body, let_ring, mute, level, seed)


class Electric(Fretted):
    """A solid-body fretted instrument: the string has no soundboard to colour it, and a Pickup
    hears it instead, at a point that sits further along a fretted string (the fraction of the
    sounding string grows as the fret shortens it). Meant to go through an Amp and a Cabinet.
    pickup=None hears the bare string."""

    def __init__(self, tuning: Sequence[Pitch] | None = None, capo: int = 0, exciter: Exciter = Plectrum(),
                 string: String = Steel(damping=0.998), pickup: Pickup | None = Bridge(), let_ring: bool = True,
                 mute: float = 0.08, level: float = 0.5, seed: int = 0):
        super().__init__(tuning, capo, exciter, string, None, let_ring, mute, level, seed)
        self.pickup = pickup

    FEEDBACK = (0.5, 0.3)  # a held string's level after the swell, and its harmonic's

    def fraction(self, string: int, fret: int) -> float:
        """Where the pickup sits along string stopped at fret, as a fraction of the part that
        sounds, at most 0.5 (past the middle the comb repeats)."""
        if self.pickup is None:
            return 0.0
        return min(0.5, self.pickup.position * 2 ** ((fret + self.capo) / 12))

    def feedback(self, string: int, fret: int, at: float, length: float, harmonic: int = 2,
                 velocity: float = 0.8) -> list[Note]:
        """One note from a tab that the amp holds for length seconds and that blooms into its
        harmonic (Feedback); a later note on the same string takes the string from it."""
        note = self.pick(string, fret, at, length, velocity)[0]
        note.articulation = Feedback(harmonic)
        return [note]

    def voice(self, note: Note) -> Unit:
        traits = self.traits(_string_of(self, note))
        vary = self.vary(note)
        string = self.pluck(note, note.freq, vary, traits)
        fb = note.articulation if isinstance(note.articulation, Feedback) else None
        if fb is not None:  # the string held at its level, its harmonic swelling over it
            string = Pluck(note.freq, damping=0.99995, brightness=self.exciter.brightness,
                           position=self.exciter.position, seed=int(note.rng.integers(2**31)))
            fade = Segments([(0.0, 1.0), (fb.onset, 1.0), (fb.onset + fb.rise, self.FEEDBACK[0])])
            swell = Segments([(0.0, 0.0), (fb.onset, 0.0), (fb.onset + fb.rise, self.FEEDBACK[1])])
            string = string * fade + Sine(note.freq * fb.harmonic) * swell
            string = string * ADSR(attack=0.0, decay=0.0, sustain=1.0, release=self.mute, gate=note.duration)
        if self.pickup is not None:
            s = note.resource if isinstance(note.resource, int) and 1 <= note.resource <= len(self.tuning) else None
            fret = (self._fret(_pitch(note.pitch), s) or 0) if s is not None else 0
            string = self.pickup(string, note.freq, self.fraction(s or 1, fret))
        return self.finish(note, string, vary[2] * (1 + traits[1]))


class ElectricGuitar(Electric):
    """A solid-body electric guitar: six steel strings tuned E2 A2 D3 G3 B3 E4, 22 frets, played
    with a plectrum, heard through the bridge pickup. By itself it sounds thin and dry, with no
    box to give it body; through Amp and Cabinet it becomes the electric guitar.

    Techniques: those of Guitar, strum and pick; feedback(string, fret, at, length, harmonic)
    for a note the amp holds and that blooms into its harmonic; PalmMute on a note for the
    muted chug.

    Limit: the strings of Guitar, with the same missing bends, slides and fret noise; one pickup
    at a time; the pickup hears the string at one point, where a real coil hears a short stretch.
    Feedback is drawn, not computed: the string is held and a sine at its harmonic swells over
    it, where a real one comes from the speaker's sound driving the string.
    """

    tuning = (E2, A2, D3, G3, B3, E4)
    frets = 22
    polyphony = 6


class ElectricBass(Electric):
    """A solid-body electric bass: four strings tuned E1 A1 D2 G2, 20 frets, played with the
    fingers, heard through the neck pickup, each note damped when the next is due as BassGuitar
    does. Under distorted guitars it carries the fundamental the amp's bend thins out.

    Limit: the strings of BassGuitar, without their stiffness or the finger's thump.
    """

    tuning = (E1, A1, D2, G2)
    frets = 20
    polyphony = 4

    def __init__(self, tuning: Sequence[Pitch] | None = None, capo: int = 0,
                 exciter: Exciter = Finger(position=0.15, brightness=0.5, variation=0.15),
                 string: String = Steel(damping=0.95), pickup: Pickup | None = Neck(), let_ring: bool = False,
                 mute: float = 0.06, level: float = 1.0, seed: int = 0):
        super().__init__(tuning, capo, exciter, string, pickup, let_ring, mute, level, seed)
