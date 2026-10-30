import subprocess
import sys

import pytest

from euterpe import EqualTemperament, JustIntonation, Pitch, Pythagorean
from euterpe.pitch import A4, Ab4, C4, C5, E4, G4, Gs4


def test_equal_temperament_follows_its_a():
    assert EqualTemperament().freq(A4) == 440.0
    assert EqualTemperament().freq(C4) == C4.freq
    assert EqualTemperament(a4=432.0).freq(A4) == 432.0
    assert EqualTemperament(a4=432.0).freq(Pitch("A5")) == 864.0


@pytest.mark.parametrize(
    "name, ratio",
    [
        ("C4", 1),
        ("Db4", 16 / 15),
        ("D4", 9 / 8),
        ("Eb4", 6 / 5),
        ("E4", 5 / 4),
        ("F4", 4 / 3),
        ("F#4", 45 / 32),
        ("Gb4", 64 / 45),
        ("G4", 3 / 2),
        ("G#4", 25 / 16),
        ("Ab4", 8 / 5),
        ("A4", 5 / 3),
        ("Bb4", 9 / 5),
        ("B4", 15 / 8),
        ("C5", 2),
        ("Bb3", 9 / 10),
        ("E3", 5 / 8),
        ("Cb4", 24 / 25),
        ("D#4", 75 / 64),
    ],
)
def test_just_intonation_of_each_interval_over_c(name, ratio):
    assert JustIntonation(C4).freq(Pitch(name)) == pytest.approx(C4.freq * ratio)


def test_just_intonation_tells_g_sharp_from_a_flat():
    tuning = JustIntonation(C4)
    assert tuning.freq(Gs4) != pytest.approx(tuning.freq(Ab4))


def test_just_intonation_keeps_its_tonic_equal_tempered():
    assert JustIntonation(C4).freq(Pitch("C4")) == Pitch("C4").freq


def test_just_intonation_reads_intervals_from_any_tonic():
    tuning = JustIntonation(Pitch("Eb4"))
    assert tuning.freq(Pitch("G4")) == pytest.approx(Pitch("Eb4").freq * 5 / 4)
    assert tuning.freq(Pitch("Bb4")) == pytest.approx(Pitch("Eb4").freq * 3 / 2)


@pytest.mark.parametrize(
    "name, ratio",
    [
        ("C4", 1),
        ("D4", 9 / 8),
        ("E4", 81 / 64),
        ("F4", 4 / 3),
        ("G4", 3 / 2),
        ("A4", 27 / 16),
        ("B4", 243 / 128),
        ("C5", 2),
        ("G#4", 6561 / 4096),
        ("Ab4", 128 / 81),
        ("Bb3", 8 / 9),
    ],
)
def test_pythagorean_stacks_fifths_over_c(name, ratio):
    assert Pythagorean(C4).freq(Pitch(name)) == pytest.approx(C4.freq * ratio)


def test_pythagorean_reads_fifths_from_any_tonic():
    tuning = Pythagorean(G4)
    assert tuning.freq(Pitch("B4")) == pytest.approx(G4.freq * 81 / 64)
    assert tuning.freq(Pitch("D5")) == pytest.approx(G4.freq * 3 / 2)


def test_tunings_are_each_their_own_frozen_hashable_class():
    for tuning in (EqualTemperament(), JustIntonation(C4), Pythagorean(C4)):
        hash(tuning)
        with pytest.raises(AttributeError):
            tuning.tonic = C5
    assert EqualTemperament() == EqualTemperament(a4=440.0)
    assert JustIntonation(C4) != Pythagorean(C4)
    assert JustIntonation(C4) != JustIntonation(E4)


def test_theory_imports_no_audio():
    code = "import euterpe.theory, sys; print('euterpe.sound' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip() == "False"
