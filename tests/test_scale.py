import pytest

from euterpe import Pitch, Scale
from euterpe.pitch import C4, D4, E4, Gs4


def names(scale):
    return [str(p) for p in scale.pitches()]


def test_d_major_is_spelled_by_its_letters():
    assert names(Scale("D", "major")) == ["D4", "E4", "F#4", "G4", "A4", "B4", "C#5"]


def test_a_harmonic_minor_has_g_sharp():
    assert Pitch("G#4") in Scale("A", "harmonic minor")
    assert Pitch("G4") not in Scale("A", "harmonic minor")


def test_a_melodic_minor_rises_with_f_sharp_and_g_sharp():
    assert names(Scale("A", "melodic minor")) == ["A4", "B4", "C5", "D5", "E5", "F#5", "G#5"]


def test_d_dorian_has_b_and_c_naturals():
    scale = Scale("D", "dorian")
    assert Pitch("B4") in scale and Pitch("C4") in scale
    assert Pitch("Bb4") not in scale and Pitch("C#4") not in scale


@pytest.mark.parametrize(
    "mode, steps",
    [
        ("major", (2, 2, 1, 2, 2, 2, 1)),
        ("natural minor", (2, 1, 2, 2, 1, 2, 2)),
        ("harmonic minor", (2, 1, 2, 2, 1, 3, 1)),
        ("melodic minor", (2, 1, 2, 2, 2, 2, 1)),
        ("ionian", (2, 2, 1, 2, 2, 2, 1)),
        ("dorian", (2, 1, 2, 2, 2, 1, 2)),
        ("phrygian", (1, 2, 2, 2, 1, 2, 2)),
        ("lydian", (2, 2, 2, 1, 2, 2, 1)),
        ("mixolydian", (2, 2, 1, 2, 2, 1, 2)),
        ("aeolian", (2, 1, 2, 2, 1, 2, 2)),
        ("locrian", (1, 2, 2, 1, 2, 2, 2)),
        ("major pentatonic", (2, 2, 3, 2, 3)),
        ("minor pentatonic", (3, 2, 2, 3, 2)),
    ],
)
def test_each_mode_has_its_steps(mode, steps):
    assert Scale("C", mode).steps == steps


def test_pentatonics_skip_letters():
    assert names(Scale("C", "major pentatonic")) == ["C4", "D4", "E4", "G4", "A4"]
    assert names(Scale("A", "minor pentatonic")) == ["A4", "C5", "D5", "E5", "G5"]


def test_pitches_start_in_the_octave_asked_for():
    assert Scale("C", "major").pitches(octave=2)[0] == Pitch("C2")


def test_degree_counts_from_one_and_climbs_past_the_octave():
    scale = Scale("C", "major")
    assert scale.degree(1) == C4
    assert scale.degree(7) == Pitch("B4")
    assert scale.degree(8) == Pitch("C5")
    assert scale.degree(1, octave=2) == Pitch("C2")
    assert Scale("C", "major pentatonic").degree(6) == Pitch("C5")


def test_there_is_no_degree_zero():
    with pytest.raises(ValueError, match="0"):
        Scale("C", "major").degree(0)


def test_membership_reads_the_spelling_in_any_octave():
    scale = Scale("C", "major")
    assert D4 in scale and Pitch("D7") in scale and E4 in scale
    assert Pitch("B#3") not in scale
    assert Gs4 not in Scale("A", "natural minor")
    assert Pitch("Ab4") not in Scale("A", "harmonic minor")


def test_a_scale_is_a_frozen_hashable_value():
    assert Scale("D", "major") == Scale("D", "major")
    assert hash(Scale("D", "major")) == hash(Scale("D", "major"))
    assert Scale("D", "major") != Scale("D", "dorian")
    with pytest.raises(AttributeError):
        Scale("D", "major").mode = "dorian"


def test_tonic_is_its_name_and_a_pitch_gives_up_its_octave():
    assert Scale("F#", "major").tonic == "F#"
    assert Scale(Pitch("Bb3"), "major") == Scale("Bb", "major")


@pytest.mark.parametrize("tonic", ["H", "C4", "c", ""])
def test_an_unreadable_tonic_is_named(tonic):
    with pytest.raises(ValueError, match=repr(tonic)):
        Scale(tonic, "major")


def test_an_unknown_mode_is_named():
    with pytest.raises(ValueError, match="'blues'"):
        Scale("C", "blues")


def test_a_scale_needing_a_triple_flat_fails_when_built():
    with pytest.raises(ValueError, match="Bbbb"):
        Scale("Fbb", "major")
