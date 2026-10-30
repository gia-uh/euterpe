"""Keys: a tonic and a mode, with the signature and the spelling of any note they imply."""

from __future__ import annotations

from dataclasses import dataclass

from euterpe.pitch import Interval, Pitch
from euterpe.theory.scale import Scale

_FIFTHS = "FCGDAEB"  # each letter a fifth above the last; C has no sharps or flats, F has one flat
_MODE_FIFTHS = {"major": 0, "ionian": 0, "lydian": 1, "mixolydian": -1, "dorian": -2, "minor": -3, "aeolian": -3,
                "phrygian": -4, "locrian": -5}  # how far each mode's signature sits from its tonic's major


@dataclass(frozen=True, init=False, repr=False)
class Key:
    """A tonic and a mode: Key("D major"), Key("F# minor") or Key("D", "dorian"). The modes are major, minor
    and the seven church modes. A minor key's scale is natural minor, and its raised 6th and 7th also
    count as in the key when spelling."""

    tonic: str
    mode: str

    def __init__(self, tonic: str | Pitch, mode: str | None = None):
        text = tonic
        if mode is None:
            tonic, _, mode = str(text).partition(" ")
        if mode not in _MODE_FIFTHS:
            raise ValueError(f"Key: cannot read {text!r} with mode {mode!r}; the modes are {', '.join(_MODE_FIFTHS)}")
        try:
            scale = Scale(tonic, "natural minor" if mode == "minor" else mode)
        except ValueError as error:
            raise ValueError(f"Key: cannot read {text!r}: {error}") from None
        object.__setattr__(self, "tonic", scale.tonic)
        object.__setattr__(self, "mode", mode)

    @property
    def scale(self) -> Scale:
        return Scale(self.tonic, "natural minor" if self.mode == "minor" else self.mode)

    @property
    def signature(self) -> int:
        """Sharps as a positive count and flats as a negative one: D major 2, F major -1, D♯ major 9."""
        tonic = self.degree(1)
        return _FIFTHS.index(tonic.letter) - 1 + 7 * tonic.alter + _MODE_FIFTHS[self.mode]

    @property
    def leading_tone(self) -> Pitch:
        """The 7th a semitone under the tonic, whatever the mode's own 7th, in degree 7's place."""
        return self.degree(1) + Interval("M7")

    @property
    def relative(self) -> Key:
        """The major or minor key with the same signature."""
        if self.mode == "major":
            return Key(self.degree(1) + Interval("M6"), "minor")
        if self.mode == "minor":
            return Key(self.degree(1) + Interval("m3"), "major")
        raise ValueError(f"Key: {self.tonic} {self.mode} has no relative; only major and minor do")

    @property
    def parallel(self) -> Key:
        """The major or minor key on the same tonic."""
        if self.mode not in ("major", "minor"):
            raise ValueError(f"Key: {self.tonic} {self.mode} has no parallel; only major and minor do")
        return Key(self.tonic, "minor" if self.mode == "major" else "major")

    @property
    def dominant(self) -> Key:
        """The key a fifth up, in the same mode."""
        return Key(self.degree(1) + Interval("P5"), self.mode)

    def degree(self, n: int, octave: int = 4) -> Pitch:
        """The nth note of the key's scale, as Scale.degree counts."""
        return self.scale.degree(n, octave)

    def spell(self, number: int) -> Pitch:
        """A MIDI number spelled in this key. A note of the key keeps its name; so do the lowered 7th and
        raised 4th in major and the raised 6th and 7th in minor. Any other note takes the plain sharp, or
        the plain flat in a key with flats."""
        tonic = self.degree(1)
        extra = {"major": ("m7", "A4"), "minor": ("M6", "M7")}.get(self.mode, ())
        for pitch in (*self.scale.pitches(), *(tonic + Interval(name) for name in extra)):
            if (number - pitch.number) % 12 == 0:
                return Pitch(pitch.letter, pitch.alter, pitch.octave + (number - pitch.number) // 12)
        plain = Pitch(number)
        if plain.alter and self.signature < 0:
            above = Pitch(number + 1)
            return Pitch(above.letter, -1, above.octave)
        return plain

    def __repr__(self) -> str:
        return f'Key("{self.tonic} {self.mode}")'
