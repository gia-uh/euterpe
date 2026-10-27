"""PluckedString: the first instrument, written by hand from chapter 7's Pluck."""

from __future__ import annotations

from euterpe.instruments.core import Instrument, Note
from euterpe.sound import ADSR, Pluck
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
