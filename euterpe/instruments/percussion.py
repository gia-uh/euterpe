"""Percussion: drums, cymbals and timpani, struck by a stick, a hand or a mallet."""

from __future__ import annotations

from collections.abc import Hashable

import numpy as np

from euterpe.instruments.core import Articulation, Instrument, Note
from euterpe.pitch import C4, D2, E2, G2, A3, Pitch
from euterpe.sound import FM, BandPass, FDNReverb, HighPass, Modal, Segments, Sine, Square, WhiteNoise
from euterpe.sound.core import RATE, Unit

MEMBRANE = (1.0, 1.59, 2.14, 2.30, 2.65)  # a circular membrane's lowest modes, over its fundamental


def fall(time60: float, at: float = 0.0, steps: int = 24) -> Segments:
    """An exponential fall from 1 to -60 dB in time60 seconds, starting at time at, then silence."""
    t = np.linspace(0.0, time60, steps)
    return Segments([(at, 0.0)] * (at > 0) + [(at + ti, 10 ** (-3 * ti / time60)) for ti in t] + [(at + time60, 0.0)])


def _seed(note: Note) -> int:
    return int(note.rng.integers(2**31))


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


class Kick(Struck):
    """A bass drum: a sine that falls from tune * sweep to tune, the head settling after the
    beater pushes it, under an exponential decay, with a short burst of noise for the beater.

    tune: the head's pitch in Hz. sweep: how many times higher the pitch starts. drop: the
    sweep's time constant in seconds. decay: seconds to fall 60 dB. click: the beater's level.

    Limit: one mode of the head, no shell resonance and no second head; its low end is a
    synthesizer's kick more than an acoustic one.
    """

    def __init__(self, tune: float = 50.0, sweep: float = 3.0, drop: float = 0.04, decay: float = 0.45,
                 click: float = 0.3, level: float = 0.8, variation: float = 0.08, seed: int = 0):
        self.tune, self.sweep, self.drop, self.decay, self.click = tune, sweep, drop, decay, click
        self.level, self.variation, self.seed = level, variation, seed

    def thump(self, note: Note, at: float = 0.0) -> Unit:
        """One beat of the head at time at, without the velocity."""
        force, bright, tuning = self.vary(note)
        f0 = float(note.freq) * tuning
        head = Sine(f0 + f0 * (self.sweep - 1) * fall(6.9 * self.drop, at)) * fall(self.decay, at)
        beater = HighPass(WhiteNoise(_seed(note)), 1500.0) * fall(0.004, at) * (self.click * bright)
        return (head + beater) * force

    def voice(self, note: Note) -> Unit:
        return self.thump(note) * (note.velocity * self.level)


class Stomp(Kick):
    """A crowd stamping on wooden boards: people thumps, each a kick with a low sweep and a loud
    click, a few milliseconds apart, in a hall.

    people: how many stamp. spread: the seconds between the first and the last. room: the
    hall's reverb time in seconds.

    Limit: every foot is the same kick, and the hall is a plain reverb, not a stadium's echo.
    """

    def __init__(self, people: int = 8, spread: float = 0.02, room: float = 1.2, tune: float = 70.0,
                 sweep: float = 1.6, drop: float = 0.02, decay: float = 0.25, click: float = 0.7,
                 level: float = 0.5, variation: float = 0.15, seed: int = 0):
        super().__init__(tune, sweep, drop, decay, click, level, variation, seed)
        if people < 1:
            raise ValueError(f"Stomp needs at least one person, got {people}")
        self.people, self.spread, self.room = people, spread, room

    def voice(self, note: Note) -> Unit:
        times = np.sort(note.rng.uniform(0.0, self.spread, self.people))
        feet = sum((self.thump(note, float(t)) for t in times[1:]), self.thump(note, float(times[0])))
        gain = note.velocity * self.level / np.sqrt(self.people)
        return FDNReverb(feet * gain, decay=self.room, size=1.2, mix=0.3, seed=_seed(note))


class Snare(Struck):
    """A snare drum: the head as three modes of a membrane, and the wires under it as a burst of
    band-passed noise.

    tune: the head's pitch in Hz. decay: the head's seconds to fall 60 dB. snappy: the wires'
    level. wires: their seconds to fall 60 dB.

    Limit: the wires do not follow the head's motion, and a rimshot or a buzz roll is not modelled.
    """

    def __init__(self, tune: float = 185.0, decay: float = 0.18, snappy: float = 0.7, wires: float = 0.22,
                 level: float = 0.35, variation: float = 0.08, seed: int = 0):
        self.tune, self.decay, self.snappy, self.wires = tune, decay, snappy, wires
        self.level, self.variation, self.seed = level, variation, seed

    def voice(self, note: Note) -> Unit:
        force, bright, tuning = self.vary(note)
        f0 = float(note.freq) * tuning
        b = min(1.0, bright * (0.5 + 0.5 * note.velocity))
        head = Modal([f0 * r for r in MEMBRANE[:3]], [self.decay, 0.7 * self.decay, 0.5 * self.decay],
                     [1.0, 0.6 * b, 0.4 * b])
        wires = BandPass(WhiteNoise(_seed(note)), 5000.0, 0.7) * fall(self.wires) * (self.snappy * 2.0 * b)
        return (head + wires) * (note.velocity * self.level * force)


class Tom(Struck):
    """A tom: the membrane's five lowest modes, the fundamental dropping a little as the head
    settles, and a click of the stick.

    tune: the pitch in Hz. decay: seconds for the fundamental to fall 60 dB.

    Limit: one head and no shell, so it rings cleaner than a real tom.
    """

    def __init__(self, tune: float = 110.0, decay: float = 0.5, level: float = 0.4,
                 variation: float = 0.08, seed: int = 0):
        self.tune, self.decay, self.level, self.variation, self.seed = tune, decay, level, variation, seed

    def voice(self, note: Note) -> Unit:
        force, bright, tuning = self.vary(note)
        f0 = float(note.freq) * tuning
        b = min(1.0, bright * (0.5 + 0.5 * note.velocity))
        body = Sine(f0 * (1 + 0.12 * fall(0.15))) * fall(self.decay)
        rest = Modal([f0 * r for r in MEMBRANE[1:]], [self.decay * k for k in (0.6, 0.45, 0.4, 0.35)],
                     [0.5 * b, 0.35 * b, 0.25 * b, 0.2 * b])
        stick = HighPass(WhiteNoise(_seed(note)), 3000.0) * fall(0.006) * (0.3 * b)
        return (body + rest + stick) * (note.velocity * self.level * force)


class Clap(Struck):
    """Hands clapping: a burst of noise per hand, a few milliseconds apart, through a band-pass
    at a hand's resonance, the last one with a short tail.

    hands: how many clap at once. spread: the seconds between the first and the last.
    decay: the tail's seconds to fall 60 dB.

    Limit: every hand has the same resonance; a crowd of hundreds needs a room as well.
    """

    def __init__(self, hands: int = 4, spread: float = 0.011, decay: float = 0.15, tune: float = 1200.0,
                 level: float = 0.6, variation: float = 0.08, seed: int = 0):
        if hands < 1:
            raise ValueError(f"Clap needs at least one hand, got {hands}")
        self.hands, self.spread, self.decay, self.tune = hands, spread, decay, tune
        self.level, self.variation, self.seed = level, variation, seed

    def resource(self, note: Note) -> Hashable | None:
        """None: claps overlap, nothing stops them."""
        return None

    def voice(self, note: Note) -> Unit:
        force, bright, tuning = self.vary(note)
        times = np.sort(np.concatenate([[0.0], note.rng.uniform(0.0, self.spread, self.hands - 1)]))
        env = sum((fall(0.012, float(t)) for t in times[:-1]), fall(self.decay, float(times[-1])))
        noise = WhiteNoise(_seed(note)) * env
        return BandPass(noise, float(note.freq) * tuning, 1.2 * bright) * (note.velocity * self.level * force * 2.0)


METAL = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)  # six square waves that beat as metal, in Hz


class HiHat(Struck):
    """A hi-hat: six square waves at inharmonic frequencies that beat against each other as
    metal does, plus noise, high-passed. Closed it is a tick; Open() lets it ring. One pedal
    holds both cymbals, so a closed stroke chokes an open one still ringing.

    closed, open: seconds to fall 60 dB in each position. tone: the high-pass in Hz.

    Limit: the metal is a fixed cluster of tones, not the modes of two real cymbals, and the
    pedal has no half-open position or foot chick.
    """

    def __init__(self, closed: float = 0.05, open: float = 0.45, tone: float = 7000.0, level: float = 0.35,
                 variation: float = 0.08, seed: int = 0):
        self.closed, self.open, self.tone, self.tune = closed, open, tone, METAL[0]
        self.level, self.variation, self.seed = level, variation, seed

    def voice(self, note: Note) -> Unit:
        force, bright, tuning = self.vary(note)
        k = float(note.freq) / METAL[0] * tuning
        metal = sum((Square(f * k) for f in METAL[1:]), Square(METAL[0] * k)) * (1 / 3)
        ring = self.open if isinstance(note.articulation, Open) else self.closed
        shimmer = HighPass(metal + WhiteNoise(_seed(note)) * 0.5, self.tone * bright)
        return HighPass(shimmer, self.tone * bright) * fall(ring) * (note.velocity * self.level * force)


class Cymbal(Struck):
    """A suspended cymbal: three frequency-modulated pairs at inharmonic ratios for the metal's
    dense modes, and high-passed noise for its wash, under a long decay. Hits overlap, so the
    wash builds as a player keeps striking it.

    decay: seconds to fall 60 dB. wash: the noise's level. bell: the level of the bell, two
    modes struck at the cup.

    Limit: the modes do not spread over time as a real cymbal's energy moves up the spectrum,
    and there is no choke by hand.
    """

    def __init__(self, decay: float = 2.0, wash: float = 0.6, bell: float = 0.0, tune: float = 340.0,
                 level: float = 0.25, variation: float = 0.08, seed: int = 0):
        self.decay, self.wash, self.bell, self.tune = decay, wash, bell, tune
        self.level, self.variation, self.seed = level, variation, seed

    def resource(self, note: Note) -> Hashable | None:
        """None: a cymbal struck again keeps ringing under the new hit."""
        return None

    def voice(self, note: Note) -> Unit:
        force, bright, tuning = self.vary(note)
        f0 = float(note.freq) * tuning
        metal = (FM(f0, ratio=1.47, index=4.0 * bright) + FM(f0 * 1.53, ratio=2.13, index=3.5 * bright)
                 + FM(f0 * 2.4, ratio=3.31, index=3.0 * bright)) * (1 / 3)
        noise = HighPass(WhiteNoise(_seed(note)), 5000.0) * self.wash
        sound = HighPass(metal + noise, 300.0) * fall(self.decay)
        if self.bell:
            sound = sound + Modal([f0 * 2.0, f0 * 5.1], [0.8 * self.decay, 0.5 * self.decay], [self.bell, 0.5 * self.bell])
        return sound * (note.velocity * self.level * force)


class Crash(Cymbal):
    """A crash cymbal: bright, a lot of wash, about two seconds of ring.

    Limit: as Cymbal's; the swell of a real crash just after the hit is missing.
    """

    def __init__(self, decay: float = 2.0, wash: float = 0.8, bell: float = 0.0, tune: float = 340.0,
                 level: float = 0.25, variation: float = 0.08, seed: int = 0):
        super().__init__(decay, wash, bell, tune, level, variation, seed)


class Ride(Cymbal):
    """A ride cymbal: less wash, a bell, a longer and more defined ring for patterns.

    Limit: as Cymbal's; the stick's ping does not change with where it lands.
    """

    def __init__(self, decay: float = 3.0, wash: float = 0.25, bell: float = 0.3, tune: float = 420.0,
                 level: float = 0.2, variation: float = 0.08, seed: int = 0):
        super().__init__(decay, wash, bell, tune, level, variation, seed)


STEPS = {"x": 0.8, "X": 1.0, "g": 0.3, "o": 0.8}  # what each step of a grid plays, at what velocity


class Kit(Instrument):
    """A drum kit: the drums a drummer plays sitting at one kit, each one an instrument of its
    own (kit.kick, kit.toms[0]). A note sounds on the drum that made it, so a pattern may also
    name a drum that is not part of the kit, such as a Clap().

    toms: from the highest to the lowest.
    level: the gain on every drum, so that the whole kit struck at once stays under full scale
    while each drum alone keeps its own level.

    Limit: each drum sounds alone; the snare's wires do not buzz when the toms ring, and the
    drums share no room.
    """

    polyphony = 24

    def __init__(self, kick: Struck | None = None, snare: Struck | None = None, hihat: Struck | None = None,
                 toms: tuple[Struck, ...] | None = None, crash: Struck | None = None, ride: Struck | None = None,
                 level: float = 0.35):
        self.kick, self.snare, self.hihat = kick or Kick(), snare or Snare(), hihat or HiHat()
        self.toms = toms if toms is not None else (Tom(196.0), Tom(147.0), Tom(98.0, decay=0.7))
        self.crash, self.ride, self.level = crash or Crash(), ride or Ride(), level

    @staticmethod
    def _drum(note: Note) -> Struck:
        if not isinstance(note.resource, Struck):
            raise ValueError(f"note at {note.time:.2f} s names no drum; make it with a drum's hit() or Kit.pattern")
        return note.resource

    def voice(self, note: Note) -> Unit:
        return self._drum(note).voice(note) * self.level

    def resource(self, note: Note) -> Hashable | None:
        return self._drum(note).resource(note)

    def pattern(self, grid: dict[Struck, str], step: float, at: float = 0.0, repeat: int = 1) -> list[Note]:
        """Notes from a step grid: one row of characters per drum, one character per step of
        step seconds. x is a hit, X an accent, g a ghost note, o an open stroke (the hi-hat's
        Open()); a dot or a space is a rest. The grid lasts as long as its longest row, and
        repeat plays it that many times."""
        if step <= 0 or repeat < 1:
            raise ValueError(f"pattern needs a step above 0 and repeat of at least 1, got {step} and {repeat}")
        length = max((len(row) for row in grid.values()), default=0)
        notes = []
        for drum, row in grid.items():
            for i, c in enumerate(row):
                if c in ". ":
                    continue
                if c not in STEPS:
                    raise ValueError(f"pattern: {c!r} at step {i} is not one of x X g o . or a space")
                for r in range(repeat):
                    notes += drum.hit(at + (r * length + i) * step, STEPS[c], articulation=Open() if c == "o" else None)
        return sorted(notes, key=lambda n: n.time)


class Mallet:
    """What strikes a timpano or a bar: its contact as a raised pulse, from 4 ms long at
    hardness 0 (soft felt or yarn) to 0.3 ms at 1 (hard plastic or brass). A shorter contact
    holds higher frequencies, so a harder mallet is brighter."""

    def __init__(self, hardness: float = 0.5):
        if not 0.0 <= hardness <= 1.0:
            raise ValueError(f"Mallet hardness must be from 0 to 1, got {hardness}")
        self.hardness = hardness

    def pulse(self, force: float = 1.0) -> Segments:
        """The contact force over time, with an area of one sample at force 1."""
        w = 0.004 * (0.0003 / 0.004) ** self.hardness
        return Segments([(0.0, 0.0), (w / 2, force * 2 / (w * RATE)), (w, 0.0)])


TIMPANI = (1.0, 1.50, 1.98, 2.44, 2.90)  # the kettle's modes over the principal one


class Timpani(Struck):
    """Timpani: a membrane over a copper kettle, whose air pulls its modes close to the
    harmonics 1, 1.5, 2, 2.5 and 3 of a note an octave below the principal, so a timpano has a
    pitch where a tom has none; plus the head's lowest mode, a short thud below it. A felt
    mallet strikes it.

    kettles: how many drums, so how many pitches ring at once. decay: the principal mode's
    seconds to fall 60 dB.

    Limit: the kettles are retuned instantly (no pedal glissando), and the roll is single
    strokes with no alternation between two mallets.
    """

    playable = (D2, C4)
    comfortable = (E2, A3)

    def __init__(self, mallet: Mallet | None = None, kettles: int = 4, decay: float = 2.5, level: float = 0.3,
                 variation: float = 0.08, seed: int = 0):
        self.mallet = mallet or Mallet(0.3)
        self.polyphony, self.decay, self.tune = kettles, decay, G2.freq
        self.level, self.variation, self.seed = level, variation, seed

    def resource(self, note: Note) -> Hashable:
        """The kettle tuned to the note's pitch: a stroke on it stops the one ringing there."""
        return round(69 + 12 * np.log2(float(note.freq) / 440.0))

    def voice(self, note: Note) -> Unit:
        force, bright, tuning = self.vary(note)
        f0 = float(note.freq) * tuning
        d = self.decay
        head = Modal([f0 * r for r in TIMPANI] + [0.82 * f0], [d, 0.8 * d, 0.6 * d, 0.5 * d, 0.4 * d, 0.2],
                     [1.0, 0.8 * bright, 0.5 * bright, 0.35 * bright, 0.25 * bright, 0.6],
                     excite=self.mallet.pulse(force))
        return head * (note.velocity * self.level)
