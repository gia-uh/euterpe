"""Pitches of twelve-tone equal temperament, as constants from A0 to C8.

A pitch is counted in semitones from C-1, as MIDI does: C4 is 60 and A4 is 69, tuned to
440 Hz. Sharps are written with s (Cs4) and flats with b (Db4); both name the same object.
"""

from __future__ import annotations

from dataclasses import dataclass

_NAMES = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]


@dataclass(frozen=True, order=True)
class Pitch:
    """A note of twelve-tone equal temperament, counted in semitones from C-1 (A4 is 69)."""

    number: int

    @property
    def freq(self) -> float:
        """The frequency in Hz, with A4 at 440 Hz."""
        return 440.0 * 2 ** ((self.number - 69) / 12)

    def __add__(self, semitones: int) -> Pitch:
        return Pitch(self.number + semitones)

    def __sub__(self, other: int | Pitch) -> Pitch | int:
        """A pitch minus semitones is a pitch; a pitch minus a pitch is the interval in semitones."""
        if isinstance(other, Pitch):
            return self.number - other.number
        return Pitch(self.number - other)

    def __repr__(self) -> str:
        return f"{_NAMES[self.number % 12]}{self.number // 12 - 1}"


# Written out, not generated at import, so editors and type checkers see every name.
A0 = Pitch(21)
As0 = Pitch(22)
Bb0 = As0
B0 = Pitch(23)
C1 = Pitch(24)
Cs1 = Pitch(25)
Db1 = Cs1
D1 = Pitch(26)
Ds1 = Pitch(27)
Eb1 = Ds1
E1 = Pitch(28)
F1 = Pitch(29)
Fs1 = Pitch(30)
Gb1 = Fs1
G1 = Pitch(31)
Gs1 = Pitch(32)
Ab1 = Gs1
A1 = Pitch(33)
As1 = Pitch(34)
Bb1 = As1
B1 = Pitch(35)
C2 = Pitch(36)
Cs2 = Pitch(37)
Db2 = Cs2
D2 = Pitch(38)
Ds2 = Pitch(39)
Eb2 = Ds2
E2 = Pitch(40)
F2 = Pitch(41)
Fs2 = Pitch(42)
Gb2 = Fs2
G2 = Pitch(43)
Gs2 = Pitch(44)
Ab2 = Gs2
A2 = Pitch(45)
As2 = Pitch(46)
Bb2 = As2
B2 = Pitch(47)
C3 = Pitch(48)
Cs3 = Pitch(49)
Db3 = Cs3
D3 = Pitch(50)
Ds3 = Pitch(51)
Eb3 = Ds3
E3 = Pitch(52)
F3 = Pitch(53)
Fs3 = Pitch(54)
Gb3 = Fs3
G3 = Pitch(55)
Gs3 = Pitch(56)
Ab3 = Gs3
A3 = Pitch(57)
As3 = Pitch(58)
Bb3 = As3
B3 = Pitch(59)
C4 = Pitch(60)
Cs4 = Pitch(61)
Db4 = Cs4
D4 = Pitch(62)
Ds4 = Pitch(63)
Eb4 = Ds4
E4 = Pitch(64)
F4 = Pitch(65)
Fs4 = Pitch(66)
Gb4 = Fs4
G4 = Pitch(67)
Gs4 = Pitch(68)
Ab4 = Gs4
A4 = Pitch(69)
As4 = Pitch(70)
Bb4 = As4
B4 = Pitch(71)
C5 = Pitch(72)
Cs5 = Pitch(73)
Db5 = Cs5
D5 = Pitch(74)
Ds5 = Pitch(75)
Eb5 = Ds5
E5 = Pitch(76)
F5 = Pitch(77)
Fs5 = Pitch(78)
Gb5 = Fs5
G5 = Pitch(79)
Gs5 = Pitch(80)
Ab5 = Gs5
A5 = Pitch(81)
As5 = Pitch(82)
Bb5 = As5
B5 = Pitch(83)
C6 = Pitch(84)
Cs6 = Pitch(85)
Db6 = Cs6
D6 = Pitch(86)
Ds6 = Pitch(87)
Eb6 = Ds6
E6 = Pitch(88)
F6 = Pitch(89)
Fs6 = Pitch(90)
Gb6 = Fs6
G6 = Pitch(91)
Gs6 = Pitch(92)
Ab6 = Gs6
A6 = Pitch(93)
As6 = Pitch(94)
Bb6 = As6
B6 = Pitch(95)
C7 = Pitch(96)
Cs7 = Pitch(97)
Db7 = Cs7
D7 = Pitch(98)
Ds7 = Pitch(99)
Eb7 = Ds7
E7 = Pitch(100)
F7 = Pitch(101)
Fs7 = Pitch(102)
Gb7 = Fs7
G7 = Pitch(103)
Gs7 = Pitch(104)
Ab7 = Gs7
A7 = Pitch(105)
As7 = Pitch(106)
Bb7 = As7
B7 = Pitch(107)
C8 = Pitch(108)
