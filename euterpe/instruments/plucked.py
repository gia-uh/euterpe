"""The plucked family: a string excited by a finger or a plectrum, heard through a body.

PluckedString is the first instrument, written by hand from chapter 7's Pluck. Plucked builds
the same string from parts (an exciter, a string, a body), and the presets choose their parts.
"""

from __future__ import annotations

import math
from collections.abc import Hashable
from dataclasses import dataclass

from euterpe.instruments.core import Instrument, Note, Staccato
from euterpe.pitch import A7, C1, C2, C6, E6, G2, G7, Pitch
from euterpe.sound import ADSR, Body, Pluck
from euterpe.sound.core import Unit


class PluckedString(Instrument):
    """A plucked string: Karplus-Strong's burst circulating in a delay line (chapter 7's Pluck),
    muted by the finger when the note ends. It has no body, so it sounds closer to a harp or a
    bare steel string than to a guitar.

    damping: how much of the vibration survives each trip along the string.
    brightness: how much of the high partials the pluck puts in.
    position: where along the string it is plucked, 0 at the bridge to 0.5 at the middle.
    mute: how long the finger takes to stop the string, in seconds.
    level: the gain of one string at full velocity, low enough that six together stay under
    full scale.
    """

    polyphony = 6

    def __init__(self, damping: float = 0.996, brightness: float = 0.5, position: float = 0.1,
                 mute: float = 0.08, level: float = 0.3):
        self.damping, self.brightness, self.position = damping, brightness, position
        self.mute, self.level = mute, level

    def voice(self, note: Note) -> Unit:
        string = Pluck(note.freq, damping=self.damping, brightness=self.brightness,
                       position=self.position, seed=int(note.rng.integers(2**31)))
        finger = ADSR(attack=0.0, decay=0.0, sustain=1.0, release=self.mute, gate=note.duration)
        return string * finger * note.velocity * self.level


@dataclass(frozen=True)
class Exciter:
    """What sets the string moving. position: where along the string, 0 at the bridge to 0.5
    at the middle; brightness: how much of the high partials it puts in, 0 to 1; variation:
    how much each pluck's position, brightness and force move, as a fraction, since no finger or
    pick touches a string twice the same way. The draws come from each note's generator."""

    position: float = 0.2
    brightness: float = 0.4
    variation: float = 0.08


@dataclass(frozen=True)
class Finger(Exciter):
    """The flesh of a finger: soft, plucked away from the bridge."""

    position: float = 0.2
    brightness: float = 0.4


@dataclass(frozen=True)
class Plectrum(Exciter):
    """A hard pick: bright, close to the bridge."""

    position: float = 0.1
    brightness: float = 0.6


@dataclass(frozen=True)
class Tolerance:
    """How far each string of one instrument is from the ideal, drawn once per string from the
    instrument's seed: its tuning (up to cents either way), its level (up to that fraction louder
    or softer) and its losses (up to that fraction more or fewer, so it rings shorter or longer)."""

    cents: float = 0.0
    level: float = 0.0
    decay: float = 0.0


@dataclass(frozen=True)
class String:
    """The vibrating string. damping: how much of the vibration survives each trip along it,
    so a lower value dies sooner, and high notes (more trips per second) die sooner than low.
    tolerance: how far each string of the instrument is from the ideal (Tolerance)."""

    damping: float = 0.997
    tolerance: Tolerance = Tolerance(cents=3.0, level=0.05, decay=0.1)


@dataclass(frozen=True)
class Steel(String):
    """A steel string: rings long."""

    damping: float = 0.997


@dataclass(frozen=True)
class Nylon(String):
    """A nylon string: softer and shorter than steel."""

    damping: float = 0.995


@dataclass(frozen=True)
class Gut(String):
    """A gut string, as on a harp or a violin."""

    damping: float = 0.993


@dataclass(frozen=True)
class Soundboard:
    """An instrument's body as a few resonant modes (frequency in Hz, decay in s, gain), plus how
    much of the string reaches the ear directly. Calling it on a string gives a Body unit."""

    freqs: tuple[float, ...] = ()
    decays: tuple[float, ...] = ()
    amps: tuple[float, ...] = ()
    dry: float = 0.5

    def __call__(self, src: Unit) -> Body:
        return Body(src, self.freqs, self.decays, self.amps, dry=self.dry)


@dataclass(frozen=True)
class GuitarBody(Soundboard):
    """A guitar's box: the air mode near 100 Hz, then the top plate."""

    freqs: tuple[float, ...] = (100.0, 200.0, 390.0, 550.0)
    decays: tuple[float, ...] = (0.15, 0.10, 0.06, 0.05)
    amps: tuple[float, ...] = (1.0, 0.7, 0.4, 0.3)
    dry: float = 0.5


@dataclass(frozen=True)
class BassBody(Soundboard):
    """An acoustic bass guitar's larger box, its air mode near 70 Hz, kept below the string so
    the box does not colour every note the same."""

    freqs: tuple[float, ...] = (70.0, 140.0, 260.0)
    decays: tuple[float, ...] = (0.20, 0.12, 0.08)
    amps: tuple[float, ...] = (0.6, 0.4, 0.2)
    dry: float = 0.7


@dataclass(frozen=True)
class HarpBody(Soundboard):
    """A harp's soundboard and box, low and broad."""

    freqs: tuple[float, ...] = (90.0, 180.0, 360.0)
    decays: tuple[float, ...] = (0.20, 0.12, 0.08)
    amps: tuple[float, ...] = (0.8, 0.6, 0.3)
    dry: float = 0.6


@dataclass(frozen=True)
class ViolinBody(Soundboard):
    """A violin's body: the air mode near 275 Hz and the two plate modes above it."""

    freqs: tuple[float, ...] = (275.0, 460.0, 530.0)
    decays: tuple[float, ...] = (0.05, 0.04, 0.04)
    amps: tuple[float, ...] = (1.0, 0.8, 0.8)
    dry: float = 0.4


class Plucked(Instrument):
    """A plucked string built from parts: an exciter sets Pluck's string moving, the body
    colours it. The string rings until it dies, a later note takes it, or polyphony steals it.

    exciter: Finger or Plectrum, where and how bright the pluck is; velocity makes it brighter.
    string: Steel, Nylon or Gut, how long it rings.
    body: the Soundboard it sounds through, or None for a bare string.
    let_ring: False to have the finger mute each string at its note's end, as Staccato does.
    mute: how long the finger takes to stop the string, in seconds.
    level: the gain of one string at full velocity.
    seed: which instrument of its make this is: each string's flaws (the string's tolerance)
    come from it, and stay the same on every note.
    """

    polyphony = 6

    def __init__(self, exciter: Exciter = Finger(), string: String = Steel(),
                 body: Soundboard | None = GuitarBody(), let_ring: bool = True, mute: float = 0.08,
                 level: float = 0.25, seed: int = 0):
        self.exciter, self.string, self.body = exciter, string, body
        self.let_ring, self.mute, self.level, self.seed = let_ring, mute, level, seed

    def traits(self, resource: Hashable) -> tuple[float, float, float]:
        """The flaws of the string that is resource: its detuning in cents, and the fractions by
        which its level and its losses differ from the ideal; all 0 without tolerance."""
        tol = self.string.tolerance
        if not (tol.cents or tol.level or tol.decay):
            return (0.0, 0.0, 0.0)
        a, b, c = self.character(resource).uniform(-1.0, 1.0, 3)
        return (float(a * tol.cents), float(b * tol.level), float(c * tol.decay))

    def vary(self, note: Note) -> tuple[float, float, float]:
        """Factors for this pluck's position, brightness and force; all 1 without variation."""
        v = self.exciter.variation
        if not v:
            return (1.0, 1.0, 1.0)
        a, b, c = 1 + v * note.rng.uniform(-1.0, 1.0, 3)
        return (float(a), float(b), float(c))

    def pluck(self, note: Note, freq: float, vary: tuple[float, float, float] = (1.0, 1.0, 1.0),
              traits: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> Unit:
        """The bare string for note at freq, with the string's flaws, before the finger and the body."""
        cents, _, decay = traits
        damping = min(0.9999, 1 - (1 - self.string.damping) * (1 + decay))
        return Pluck(freq * 2 ** (cents / 1200), damping=damping,
                     brightness=min(1.0, self.exciter.brightness * (0.5 + 0.5 * note.velocity) * vary[1]),
                     position=min(0.5, self.exciter.position * vary[0]), seed=int(note.rng.integers(2**31)))

    def voice(self, note: Note) -> Unit:
        traits = self.traits(_string_of(self, note))
        vary = self.vary(note)
        return self.finish(note, self.pluck(note, note.freq, vary, traits), vary[2] * (1 + traits[1]))

    def finish(self, note: Note, string: Unit, force: float = 1.0) -> Unit:
        """The finger's mute when asked, then the body, then the note's gain."""
        if not self.let_ring or isinstance(note.articulation, Staccato):
            string = string * ADSR(attack=0.0, decay=0.0, sustain=1.0, release=self.mute, gate=note.duration)
        if self.body is not None:
            string = self.body(string)
        return string * note.velocity * force * self.level


def _string_of(instrument: Instrument, note: Note) -> Hashable:
    """The string a note sounds on: its resource, or else the nearest pitch's number."""
    r = instrument.resource(note)
    if r is not None:
        return r
    if isinstance(note.pitch, Pitch):
        return note.pitch.number
    return round(69 + 12 * math.log2(float(note.pitch) / 440.0))


class Harp(Plucked):
    """A concert harp: 47 gut strings from C1 to G7, plucked with the fingers near the middle,
    through a harp's soundboard. Each pitch has its own string, so a note rings until it dies
    or the same pitch is plucked again.

    Limit: no pedals (each pitch is simply its own string), no buzz of a string against the
    pedal mechanism, and no damping by the hand between chords.
    """

    polyphony = 16
    playable = (C1, G7)
    comfortable = (C2, C6)

    def __init__(self, exciter: Exciter = Finger(position=0.45, brightness=0.3), string: String = Gut(),
                 body: Soundboard | None = HarpBody(), let_ring: bool = True, mute: float = 0.08,
                 level: float = 0.45, seed: int = 0):
        super().__init__(exciter, string, body, let_ring, mute, level, seed)

    def resource(self, note: Note) -> Hashable:
        """The string: one per pitch, a frequency in Hz going to the nearest pitch's string."""
        if isinstance(note.pitch, Pitch):
            return note.pitch.number
        return round(69 + 12 * math.log2(float(note.pitch) / 440.0))


class PizzicatoStrings(Plucked):
    """A string section plucking: players slightly out of tune with each other, each a short gut
    string through a violin's body.

    players: how many play each note; each is detuned by up to 6 cents, drawn per note.

    Limit: one body for the whole section, no room, and all players pluck at the same instant;
    the low notes sound through a violin's body even where a cello's would be larger.
    """

    polyphony = 12
    playable = (C2, A7)
    comfortable = (G2, E6)

    def __init__(self, players: int = 3, exciter: Exciter = Finger(position=0.3, brightness=0.3),
                 string: String = Gut(damping=0.97), body: Soundboard | None = ViolinBody(),
                 let_ring: bool = True, mute: float = 0.08, level: float = 0.6, seed: int = 0):
        super().__init__(exciter, string, body, let_ring, mute, level, seed)
        if players < 1:
            raise ValueError(f"PizzicatoStrings needs players of at least 1, got {players}")
        self.players = players

    def voice(self, note: Note) -> Unit:
        traits = self.traits(_string_of(self, note))
        vary = self.vary(note)
        cents = note.rng.uniform(-6.0, 6.0, self.players)
        section = sum((self.pluck(note, note.freq * 2 ** (c / 1200), vary, traits) for c in cents[1:]),
                      self.pluck(note, note.freq * 2 ** (cents[0] / 1200), vary, traits))
        return self.finish(note, section * (1 / math.sqrt(self.players)), vary[2] * (1 + traits[1]))
