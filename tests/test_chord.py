import pytest

from euterpe import Chord, Key, Pitch, Roman
from euterpe.pitch import C4, C5, Cs4, D4, E4, E5, F4, G4, Gs4


@pytest.mark.parametrize(
    "text, tones",
    [
        ("C", ("C", "E", "G")),
        ("Cm", ("C", "Eb", "G")),
        ("Bdim", ("B", "D", "F")),
        ("Caug", ("C", "E", "G#")),
        ("Csus2", ("C", "D", "G")),
        ("Csus4", ("C", "F", "G")),
        ("Db7", ("Db", "F", "Ab", "Cb")),
        ("Cmaj7", ("C", "E", "G", "B")),
        ("Am7", ("A", "C", "E", "G")),
        ("F#m7b5", ("F#", "A", "C", "E")),
        ("Bdim7", ("B", "D", "F", "Ab")),
    ],
)
def test_a_symbol_spells_its_tones(text, tones):
    assert Chord(text).tones == tones


def test_a_symbol_and_its_parts_are_one_chord():
    assert Chord("Cmaj7") == Chord("C", "maj7")
    assert Chord("C/E") == Chord("C", "", inversion=1)
    assert hash(Chord("C/E")) == hash(Chord("C", "", inversion=1))
    assert Chord(Pitch("F#3"), "m").root == "F#"


def test_a_chord_keeps_its_parts():
    chord = Chord("F#m7b5/A")
    assert (chord.root, chord.quality, chord.inversion) == ("F#", "m7b5", 1)
    assert chord.name == "F#m7b5/A"
    assert repr(chord) == 'Chord("F#m7b5/A")'


def test_the_bass_follows_the_inversion():
    assert Chord("C").bass == "C"
    assert Chord("C/E").bass == "E"
    assert Chord("C", "maj7", inversion=1).bass == "E"
    assert Chord("C", "maj7", inversion=1).name == "Cmaj7/E"


@pytest.mark.parametrize("text", ["C/D", "H", "Cblues", "", "C/", "c", "C/E/G"])
def test_an_unreadable_symbol_is_named(text):
    with pytest.raises(ValueError, match=repr(text)):
        Chord(text)


def test_a_quality_or_inversion_out_of_the_table_is_named():
    with pytest.raises(ValueError, match="blues"):
        Chord("C", "blues")
    with pytest.raises(ValueError, match="inversion 3"):
        Chord("C", "", inversion=3)
    with pytest.raises(ValueError, match="inversion -1"):
        Chord("C", "", inversion=-1)


def test_a_chord_past_a_double_accidental_raises_when_built():
    with pytest.raises(ValueError, match="Cbbm"):
        Chord("Cbbm")


def test_close_voicing_stacks_up_from_the_bass_within_an_octave():
    assert Chord("C").pitches() == (C4, E4, G4)
    assert Chord("C").pitches(octave=3) == (Pitch("C3"), Pitch("E3"), Pitch("G3"))
    assert Chord("C/E").pitches() == (E4, G4, C5)
    assert Chord("C/G").pitches() == (G4, C5, E5)
    assert Chord("Db7/Cb").pitches() == (Pitch("Cb4"), Pitch("Db4"), F4, Pitch("Ab4"))


def test_root_voicing_ignores_the_inversion():
    assert Chord("C/E").pitches(voicing="root") == (C4, E4, G4)


def test_open_voicing_drops_the_second_note_from_the_top_and_stays_sorted():
    assert Chord("C").pitches(voicing="open") == (Pitch("E3"), C4, G4)
    assert Chord("Cmaj7").pitches(voicing="open") == (Pitch("G3"), C4, E4, Pitch("B4"))


def test_an_unknown_voicing_is_named():
    with pytest.raises(ValueError, match="spread"):
        Chord("C").pitches(voicing="spread")


def test_from_pitches_names_a_stack():
    assert Chord.from_pitches([E4, G4, C5]) == Chord("C/E")
    assert Chord.from_pitches([E4, G4, C5, E5]).name == "C/E"
    assert Chord.from_pitches([G4, C4, E4]) == Chord("C")
    assert Chord.from_pitches([Pitch("G3"), Pitch("B3"), D4, F4]) == Chord("G7")
    assert Chord.from_pitches([Pitch("B3"), D4, F4, Pitch("Ab4")]) == Chord("Bdim7")


def test_from_pitches_returns_none_when_no_quality_fits():
    assert Chord.from_pitches([]) is None
    assert Chord.from_pitches([C4]) is None
    assert Chord.from_pitches([C4, C5]) is None
    assert Chord.from_pitches([C4, D4]) is None
    assert Chord.from_pitches([C4, G4]) is None


def test_from_pitches_reads_the_spelling_not_the_sound():
    assert Chord.from_pitches([Cs4, F4, Gs4]) is None
    assert Chord.from_pitches([Cs4, Pitch("E#4"), Gs4]) == Chord("C#")


def test_a_symmetric_stack_takes_the_bass_as_root():
    assert Chord.from_pitches([C4, D4, G4]) == Chord("Csus2")
    assert Chord.from_pitches([Pitch("G3"), C4, D4]) == Chord("Gsus4")
    assert Chord.from_pitches([C4, E4, Pitch("G#4")]) == Chord("Caug")


def test_a_sus_stack_on_neither_root_counts_up_from_the_bass():
    assert Chord.from_pitches([D4, G4, Pitch("C5")]) == Chord("Gsus4/D")


def test_from_pitches_survives_a_heavily_altered_stack():
    assert Chord.from_pitches([Pitch("Cbb4"), Pitch("F##4"), Pitch("Bbb4")]) is None


def test_every_chord_reads_back_from_its_own_pitches():
    for quality in ("", "m", "dim", "aug", "7", "maj7", "m7", "m7b5", "dim7"):
        chord = Chord("Eb", quality)
        for inversion in range(len(chord.tones)):
            inverted = Chord("Eb", quality, inversion=inversion)
            assert Chord.from_pitches(inverted.pitches()) == inverted


def test_chord_roman_reads_the_chord_in_a_key():
    assert Chord("G7").roman(Key("C major")) == Roman("V7", Key("C major"))


def test_chord_roman_raises_when_nothing_fits():
    with pytest.raises(ValueError, match="Csus4"):
        Chord("Csus4").roman(Key("C major"))
