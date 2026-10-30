import re

import pytest

from euterpe import Chord, Key, Roman, analyze, cadence
from euterpe.pitch import C5, E5, G4

C_MAJOR = Key("C major")
A_MINOR = Key("A minor")


@pytest.mark.parametrize(
    "text, tones",
    [
        ("I", ("C", "E", "G")),
        ("ii", ("D", "F", "A")),
        ("iii", ("E", "G", "B")),
        ("IV", ("F", "A", "C")),
        ("V", ("G", "B", "D")),
        ("vi", ("A", "C", "E")),
        ("vii°", ("B", "D", "F")),
        ("V7", ("G", "B", "D", "F")),
        ("vii°7/V", ("F#", "A", "C", "Eb")),
        ("bVI", ("Ab", "C", "Eb")),
        ("bII6", ("Db", "F", "Ab")),
        ("V/vi", ("E", "G#", "B")),
        ("V7/IV", ("C", "E", "G", "Bb")),
        ("III+", ("E", "G#", "B#")),
    ],
)
def test_numerals_in_c_major(text, tones):
    assert Roman(text, C_MAJOR).chord.tones == tones


@pytest.mark.parametrize(
    "text, tones",
    [
        ("V", ("E", "G#", "B")),
        ("III", ("C", "E", "G")),
        ("VI", ("F", "A", "C")),
        ("vii°", ("G#", "B", "D")),
        ("vii°7", ("G#", "B", "D", "F")),
        ("VII", ("G", "B", "D")),
        ("i", ("A", "C", "E")),
        ("iv", ("D", "F", "A")),
        ("ii°", ("B", "D", "F")),
        ("V7", ("E", "G#", "B", "D")),
        ("bII6", ("Bb", "D", "F")),
    ],
)
def test_numerals_in_a_minor(text, tones):
    assert Roman(text, A_MINOR).chord.tones == tones


@pytest.mark.parametrize(
    "text, quality",
    [
        ("I7", "maj7"),
        ("ii7", "m7"),
        ("IV7", "maj7"),
        ("V7", "7"),
        ("vi7", "m7"),
        ("viiø7", "m7b5"),
        ("vii°7", "dim7"),
        ("bVII7", "7"),
        ("iv7", "m7"),
    ],
)
def test_a_seventh_on_a_plain_numeral_is_the_keys_own(text, quality):
    assert Roman(text, C_MAJOR).chord.quality == quality


@pytest.mark.parametrize(
    "text, bass",
    [
        ("ii6", "F"),
        ("I64", "G"),
        ("V7", "G"),
        ("V65", "B"),
        ("V43", "D"),
        ("V42", "F"),
    ],
)
def test_a_figure_sets_the_bass(text, bass):
    assert Roman(text, C_MAJOR).chord.bass == bass


def test_the_neapolitan_is_a_flat_two_in_first_inversion():
    assert C_MAJOR.roman("bII6").chord == Chord("Db/F")


def test_a_roman_keeps_its_parts():
    roman = C_MAJOR.roman("vii°7/V")
    assert roman == Roman("vii°7/V", C_MAJOR)
    assert roman.key == C_MAJOR
    assert roman.text == "vii°7/V"
    assert roman.figure == "7"
    assert roman.secondary == "V"
    assert C_MAJOR.roman("V").figure == ""
    assert C_MAJOR.roman("V").secondary is None
    assert hash(roman) == hash(Roman("vii°7/V", C_MAJOR))
    assert repr(C_MAJOR.roman("V7")) == 'Roman("V7", Key("C major"))'


def test_the_ascii_suffixes_are_one_numeral_with_the_signs():
    assert C_MAJOR.roman("viio7") == C_MAJOR.roman("vii°7")
    assert C_MAJOR.roman("vii%7") == C_MAJOR.roman("viiø7")


@pytest.mark.parametrize(
    "text, function",
    [
        ("I", "tonic"),
        ("ii", "predominant"),
        ("iii", "tonic"),
        ("IV", "predominant"),
        ("V", "dominant"),
        ("vi", "tonic"),
        ("vii°", "dominant"),
        ("V7/V", "dominant"),
        ("vii°7/ii", "dominant"),
        ("bVI", "tonic"),
        ("bII6", "predominant"),
    ],
)
def test_each_numeral_has_a_function(text, function):
    assert C_MAJOR.roman(text).function == function


@pytest.mark.parametrize("text", ["", "H", "VIII", "IIII", "V9", "V/", "V/H", "V/V7", "bbII", "Vi", "viiø", "III+7"])
def test_an_unreadable_numeral_is_named(text):
    with pytest.raises(ValueError, match=re.escape(repr(text))):
        Roman(text, C_MAJOR)


def test_a_numeral_past_a_double_accidental_is_named():
    with pytest.raises(ValueError, match="bIV"):
        Roman("bIV", Key("Fb major"))


@pytest.mark.parametrize(
    "symbol, text",
    [
        ("C", "I"),
        ("Dm", "ii"),
        ("Em", "iii"),
        ("F", "IV"),
        ("G", "V"),
        ("Am", "vi"),
        ("Bdim", "vii°"),
        ("G7", "V7"),
        ("Cmaj7", "I7"),
        ("Bm7b5", "viiø7"),
        ("C/E", "I6"),
        ("C/G", "I64"),
        ("G7/B", "V65"),
        ("G7/D", "V43"),
        ("G7/F", "V42"),
    ],
)
def test_analyze_finds_diatonic_numerals_first(symbol, text):
    assert analyze(Chord(symbol), C_MAJOR) == C_MAJOR.roman(text)


@pytest.mark.parametrize(
    "symbol, text",
    [
        ("Am", "i"),
        ("Bdim", "ii°"),
        ("C", "III"),
        ("Dm", "iv"),
        ("E", "V"),
        ("E7", "V7"),
        ("F", "VI"),
        ("G", "VII"),
        ("G#dim", "vii°"),
        ("G#dim7", "vii°7"),
    ],
)
def test_analyze_in_a_minor_takes_the_raised_seventh_as_the_keys_own(symbol, text):
    assert analyze(Chord(symbol), A_MINOR) == A_MINOR.roman(text)


@pytest.mark.parametrize(
    "symbol, text",
    [
        ("D7", "V7/V"),
        ("D", "V/V"),
        ("D7/F#", "V65/V"),
        ("E", "V/vi"),
        ("A7", "V7/ii"),
        ("C7", "V7/IV"),
        ("F#dim7", "vii°7/V"),
        ("F#m7b5", "viiø7/V"),
        ("C#dim", "vii°/ii"),
    ],
)
def test_analyze_then_tries_applied_dominants(symbol, text):
    assert analyze(Chord(symbol), C_MAJOR) == C_MAJOR.roman(text)


@pytest.mark.parametrize(
    "symbol, text",
    [
        ("Ab", "bVI"),
        ("Bb", "bVII"),
        ("Eb", "bIII"),
        ("Db/F", "bII6"),
        ("Fm", "iv"),
        ("Gm", "v"),
        ("Bdim7", "vii°7"),
    ],
)
def test_analyze_then_tries_borrowed_chords(symbol, text):
    assert analyze(Chord(symbol), C_MAJOR) == C_MAJOR.roman(text)


def test_analyze_returns_none_when_nothing_fits():
    assert analyze(Chord("Csus4"), C_MAJOR) is None
    assert analyze(Chord("Ebb"), C_MAJOR) is None


def test_analyze_reads_back_each_numeral_it_returns():
    for symbol in ("C", "D7", "F#dim7", "Ab", "Db/F", "G7/B", "Fm"):
        assert analyze(Chord(symbol), C_MAJOR).chord == Chord(symbol)


def test_analyze_handles_keys_with_many_accidentals():
    key = Key("C# major")
    assert analyze(Chord("G#7"), key) == key.roman("V7")
    assert analyze(Chord("C"), Key("Fb major")) == Key("Fb major").roman("#V")


def chords(*symbols):
    return [Chord(symbol) for symbol in symbols]


@pytest.mark.parametrize(
    "symbols, soprano, name",
    [
        (("F", "G", "C"), C5, "PAC"),
        (("G7", "C"), C5, "PAC"),
        (("G", "C"), None, "IAC"),
        (("G", "C"), E5, "IAC"),
        (("G/B", "C"), C5, "IAC"),
        (("G", "C/E"), C5, "IAC"),
        (("C", "G"), None, "HC"),
        (("C", "Dm", "G"), G4, "HC"),
        (("F", "C"), None, "plagal"),
        (("Fm", "C"), C5, "plagal"),
        (("G", "Am"), None, "deceptive"),
        (("G7", "Am"), None, "deceptive"),
        (("Dm", "Em"), None, None),
        (("C", "Am"), None, None),
        (("Csus4", "C"), None, None),
    ],
)
def test_cadences_in_c_major(symbols, soprano, name):
    assert cadence(chords(*symbols), C_MAJOR, soprano=soprano) == name


@pytest.mark.parametrize(
    "symbols, soprano, name",
    [
        (("E", "Am"), Key("A minor").degree(1, 5), "PAC"),
        (("E7", "Am"), None, "IAC"),
        (("E7", "A"), Key("A minor").degree(1, 5), "PAC"),
        (("Dm", "E"), None, "HC"),
        (("Dm", "Am"), None, "plagal"),
        (("E", "F"), None, "deceptive"),
    ],
)
def test_cadences_in_a_minor(symbols, soprano, name):
    assert cadence(chords(*symbols), A_MINOR, soprano=soprano) == name


def test_cadence_reads_only_the_last_chords():
    assert cadence(chords("C", "Am", "F", "G", "C"), C_MAJOR, soprano=C5) == "PAC"


def test_an_applied_dominant_ending_is_no_half_cadence():
    assert cadence(chords("C", "D7"), C_MAJOR) is None


def test_cadence_on_few_chords():
    assert cadence([], C_MAJOR) is None
    assert cadence(chords("C"), C_MAJOR) is None
    assert cadence(chords("G"), C_MAJOR) == "HC"
