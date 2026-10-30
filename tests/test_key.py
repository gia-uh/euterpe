import pytest

from euterpe import Key, Pitch, Scale
from euterpe.pitch import C4, D4


def test_key_reads_its_text_or_a_tonic_and_mode():
    assert Key("D major") == Key("D", "major")
    assert Key("F# minor").tonic == "F#"
    assert Key("F# minor").mode == "minor"
    assert Key("D", "dorian").mode == "dorian"


@pytest.mark.parametrize("text", ["H major", "D", "D blues", "D harmonic minor", "D major pentatonic", ""])
def test_an_unreadable_key_is_named(text):
    with pytest.raises(ValueError, match=repr(text)):
        Key(text)


def test_a_minor_keys_scale_is_natural_minor():
    assert Key("A minor").scale == Scale("A", "natural minor")
    assert Key("D major").scale == Scale("D", "major")
    assert Key("D", "dorian").scale == Scale("D", "dorian")


@pytest.mark.parametrize(
    "key, signature",
    [
        ("C major", 0),
        ("D major", 2),
        ("F major", -1),
        ("Eb major", -3),
        ("A minor", 0),
        ("F# minor", 3),
        ("C minor", -3),
        ("Cb major", -7),
        ("C# major", 7),
        ("D# major", 9),
    ],
)
def test_signature_counts_sharps_up_and_flats_down(key, signature):
    assert Key(key).signature == signature


@pytest.mark.parametrize(
    "tonic, mode",
    [("C", "ionian"), ("D", "dorian"), ("E", "phrygian"), ("F", "lydian"), ("G", "mixolydian"), ("A", "aeolian"),
     ("B", "locrian")],
)
def test_the_church_modes_on_the_white_keys_have_no_signature(tonic, mode):
    assert Key(tonic, mode).signature == 0


def test_d_sharp_major_holds_its_double_sharps():
    scale = Key("D# major").scale
    assert Pitch("F##4") in scale and Pitch("C##4") in scale
    assert [str(p) for p in scale.pitches()] == ["D#4", "E#4", "F##4", "G#4", "A#4", "B#4", "C##5"]


def test_relative():
    assert Key("F# minor").relative == Key("A major")
    assert Key("A major").relative == Key("F# minor")
    assert Key("Eb major").relative == Key("C minor")


def test_parallel():
    assert Key("C minor").parallel == Key("C major")
    assert Key("C major").parallel == Key("C minor")


@pytest.mark.parametrize("name", ["relative", "parallel"])
def test_a_church_mode_has_no_relative_or_parallel(name):
    with pytest.raises(ValueError, match="dorian"):
        getattr(Key("D", "dorian"), name)


def test_dominant_keeps_the_mode():
    assert Key("C major").dominant == Key("G major")
    assert Key("A minor").dominant == Key("E minor")
    assert Key("D", "dorian").dominant == Key("A", "dorian")


def test_leading_tone_is_a_semitone_under_the_tonic():
    tone = Key("A minor").leading_tone
    assert (tone.letter, tone.alter) == ("G", 1)
    tone = Key("C major").leading_tone
    assert (tone.letter, tone.alter) == ("B", 0)
    tone = Key("D", "dorian").leading_tone
    assert (tone.letter, tone.alter) == ("C", 1)
    assert Key("A minor").leading_tone.pitch_class == (Key("A minor").degree(1).pitch_class - 1) % 12


def test_degree_reads_the_scale():
    assert Key("C major").degree(1) == C4
    assert Key("A minor").degree(7) == Pitch("G5")
    assert Key("C major").degree(2, octave=4) == D4
    assert Key("C major").degree(1, octave=3) == Pitch("C3")


@pytest.mark.parametrize(
    "key, number, name",
    [
        ("C major", 60, "C4"),
        ("C major", 61, "C#4"),
        ("C major", 63, "D#4"),
        ("C major", 66, "F#4"),
        ("C major", 68, "G#4"),
        ("C major", 70, "Bb4"),
        ("F major", 61, "Db4"),
        ("F major", 70, "Bb4"),
        ("F major", 66, "Gb4"),
        ("A minor", 68, "G#4"),
        ("A minor", 66, "F#4"),
        ("A minor", 70, "A#4"),
        ("A minor", 63, "D#4"),
        ("D major", 65, "F4"),
        ("D major", 72, "C5"),
        ("D major", 68, "G#4"),
        ("C minor", 61, "Db4"),
        ("C minor", 69, "A4"),
        ("C minor", 71, "B4"),
        ("G# minor", 65, "E#4"),
        ("C# major", 60, "B#3"),
        ("Cb major", 59, "Cb4"),
        ("D# major", 67, "F##4"),
    ],
)
def test_spell(key, number, name):
    assert str(Key(key).spell(number)) == name


@pytest.mark.parametrize("key", ["C major", "F major", "A minor", "D# major", "Cb major", "D dorian"])
def test_spell_always_gives_back_the_number(key):
    for number in range(40, 90):
        assert Key(key).spell(number).number == number


def test_a_key_is_a_frozen_hashable_value():
    assert len({Key("D major"), Key("D", "major"), Key("D minor")}) == 2
    with pytest.raises(AttributeError):
        Key("D major").tonic = "E"
