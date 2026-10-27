"""Notes, articulations, controls and the Instrument class that turns notes into sound."""

from __future__ import annotations

from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

import numpy as np

from euterpe.pitch import Pitch
from euterpe.sound.core import Unit

if TYPE_CHECKING:
    from euterpe.instruments.phrase import Phrase


@dataclass
class Note:
    """One note to play: when it starts (s), which pitch (a Pitch or Hz), how long it is held
    (s), how hard (0 to 1), how it is played, and which physical resource it uses (a string,
    a key, a drum head): a new note on a resource that is still sounding stops the old one."""

    time: float
    pitch: Pitch | float
    duration: float
    velocity: float = 0.8
    articulation: Articulation | None = None
    resource: Hashable | None = None
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(0), init=False, repr=False)
    _freq: float | Unit | None = field(default=None, init=False, repr=False)

    @property
    def freq(self) -> float | Unit:
        """The frequency in Hz, or a unit that moves it when a slur joins several notes."""
        if self._freq is not None:
            return self._freq
        return self.pitch.freq if isinstance(self.pitch, Pitch) else float(self.pitch)


class Articulation:
    """A way of playing a note. Any articulation applies to any instrument: it changes the
    note here, and an instrument whose parts it acts on reads it in voice()."""

    def apply(self, note: Note) -> Note:
        return note


@dataclass
class Staccato(Articulation):
    """Detached: the note is held for only a fraction of its written duration."""

    fraction: float = 0.5

    def apply(self, note: Note) -> Note:
        return _copy(note, duration=note.duration * self.fraction)


@dataclass
class Accent(Articulation):
    """Stressed: the velocity is multiplied by boost, up to 1."""

    boost: float = 1.3

    def apply(self, note: Note) -> Note:
        return _copy(note, velocity=min(1.0, note.velocity * self.boost))


@dataclass
class Legato(Articulation):
    """Joined to the note before it: a monophonic instrument slurs into it in one breath or
    bow stroke instead of starting again."""


@dataclass
class Control:
    """An event that is not a note, such as a pedal or a bend; the instrument whose model has
    that control reads it in perform()."""

    time: float


class Instrument:
    """Turns notes into sound. A subclass writes voice(note), the sound of one note.

    polyphony: how many notes sound at once before the oldest is stopped.
    playable, comfortable: the lowest and highest pitch the instrument can play, and the
    range where it plays well; the lint rules check notes against them.
    """

    polyphony: int = 8
    playable: tuple[Pitch, Pitch] | None = None
    comfortable: tuple[Pitch, Pitch] | None = None

    def voice(self, note: Note) -> Unit:
        """The sound of one note, from its start until it falls silent."""
        raise NotImplementedError

    def resource(self, note: Note) -> Hashable | None:
        """The physical resource the note uses; two notes on one resource cannot sound together."""
        return note.resource

    def perform(self, notes: list[Note], controls: list[Control]) -> list[Note]:
        """Apply the controls to the notes, such as a pedal holding them; by default nothing."""
        return notes

    def play(self, events: Iterable, seed: int = 0) -> Phrase:
        """Notes, controls and (time, pitch, duration[, velocity]) tuples, as one unit."""
        return play(self, events, seed)

    def note(self, pitch: Pitch | float, duration: float, velocity: float = 0.8,
             articulation: Articulation | None = None) -> Phrase:
        """One note at time 0, as a unit."""
        return self.play([Note(0.0, pitch, duration, velocity, articulation)])


def play(instrument, events: Iterable, seed: int = 0) -> Phrase:
    """Play events on any object with voice(note) and polyphony, inheriting or not.

    Each note gets its own random generator, derived from seed in time order, so the same
    seed gives the same samples.
    """
    from euterpe.instruments.phrase import Phrase

    notes, controls = [], []
    for e in events:
        if isinstance(e, Control):
            controls.append(e)
            continue
        note = e if isinstance(e, Note) else Note(*e)
        _check(note)
        notes.append(note.articulation.apply(note) if note.articulation else note)
    notes.sort(key=lambda n: n.time)
    for note, child in zip(notes, np.random.SeedSequence(seed).spawn(len(notes))):
        note.rng = np.random.default_rng(child)
    perform = getattr(instrument, "perform", None)
    if perform is not None:
        notes = sorted(perform(notes, sorted(controls, key=lambda c: c.time)), key=lambda n: n.time)
    return Phrase(notes, instrument)


def _check(note: Note) -> None:
    if note.duration <= 0:
        raise ValueError(f"note {note} needs a duration above 0")
    if not 0.0 <= note.velocity <= 1.0:
        raise ValueError(f"note {note} needs a velocity from 0 to 1")
    if note.time < 0:
        raise ValueError(f"note {note} starts before 0 s")


def _copy(note: Note, **changes) -> Note:
    """A copy of note with changes, keeping the fields set after construction."""
    copy = replace(note, **changes)
    copy.rng, copy._freq = note.rng, note._freq
    return copy
