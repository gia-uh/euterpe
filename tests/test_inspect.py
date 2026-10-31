import sys
from fractions import Fraction

import matplotlib.pyplot as plt
import numpy as np
import pytest

from euterpe import Key, Meter, Pitch, Score, chords, drums, melody
from euterpe.inspect import chords_per_beat, estimate_key, inspect
from euterpe.instruments import Harp, Kit, Organ, Violin
from euterpe.sound.clip import Clip
from euterpe.view import chromagram


def _sines(*beats, seconds: float = 0.5) -> Clip:
    """Each beat a stack of sines of equal amplitude on the given pitch names."""
    t = np.arange(int(seconds * 48_000)) / 48_000
    return Clip(np.concatenate([sum(np.sin(2 * np.pi * Pitch(p).freq * t) for p in names) / (2 * len(names)) for names in beats]))


def _piece() -> Score:
    s = Score(key=Key("D major"), tempo=240)
    s.part("left hand/1", Harp()).add(melody("d4:q f# a d5"))
    s.part("chords", Harp()).add(chords("I:w", voicing="close"))
    return s


def test_the_key_of_a_c_major_scale():
    key, r = estimate_key(chromagram(_sines(*[[p] for p in "C4 D4 E4 F4 G4 A4 B4 C5".split()])))
    assert key == Key("C major") and 0.5 < r <= 1


def test_the_key_of_an_a_minor_scale():
    key, r = estimate_key(chromagram(_sines(*[[p] for p in "A3 B3 C4 D4 E4 F4 G4 A4".split()])))
    assert key == Key("A minor") and 0.5 < r <= 1


def test_estimate_key_takes_one_chroma_or_many_frames():
    frames = chromagram(_sines(["C4", "E4", "G4"]))
    assert estimate_key(frames) == estimate_key(frames.mean(axis=1))


def test_a_silent_chroma_has_no_key_to_trust():
    assert estimate_key(np.zeros(12))[1] == 0.0
    assert estimate_key(np.zeros((12, 0)))[1] == 0.0


def test_chords_per_beat_on_one_four_five_one_in_sines():
    s = Score(key=Key("C major"), tempo=120)
    s.part("chords").add(chords("I:q IV V I", voicing="close"))
    clip = _sines(["C4", "E4", "G4"], ["F4", "A4", "C5"], ["G4", "B4", "D5"], ["C4", "E4", "G4"])
    assert chords_per_beat(clip, s) == [(1, Fraction(1), "C"), (1, Fraction(2), "F"), (1, Fraction(3), "G"), (1, Fraction(4), "C")]


def test_chords_per_beat_says_none_where_no_chord_fits():
    s = Score(tempo=120)
    s.part("a").add(melody("c4:q"))
    assert chords_per_beat(_sines(["C4"]), s)[0] == (1, Fraction(1), None)


@pytest.mark.parametrize("names", [["C4", "G4"], ["C4", "E4"]])
def test_chords_per_beat_names_no_chord_from_two_tones(names):
    s = Score(tempo=120)
    s.part("a").add(melody("c4:q"))
    assert chords_per_beat(_sines(names), s)[0][2] is None


def test_chords_per_beat_reads_an_instrument_with_harmonics():
    s = Score(key=Key("C major"), tempo=96)
    s.part("c", Organ()).add(chords("I:q IV V I | vi:q ii V7 I", voicing="close"))
    assert [name for _, _, name in chords_per_beat(s.play(0).take(), s)] == ["C", "F", "G", "C", "Am", "Dm", "G7", "C"]


def test_chords_per_beat_reads_a_chord_under_a_melody():
    s = Score(key=Key("D major"), meter=Meter("3/4"), tempo=84)
    s.part("melody", Harp()).add(melody("f#4:q a4 d5"))
    s.part("chords", Organ()).add(chords("I:h.", voicing="close"))
    assert [name for _, _, name in chords_per_beat(s.play(0).take(), s)] == ["D", "D", "D"]


def test_one_rich_note_is_no_chord():
    s = Score(tempo=96)
    s.part("a", Violin()).add(melody("c4:q e"))
    assert [name for _, _, name in chords_per_beat(s.play(0).take(), s)][:2] == [None, None]


def test_chords_per_beat_spells_in_the_key_in_force():
    s = Score(key=Key("Eb major"), tempo=120)
    s.part("a").add(chords("IV:q", voicing="close"))
    assert chords_per_beat(_sines(["Ab4", "C5", "Eb5"]), s)[0][2] == "Ab"


def test_chords_per_beat_reads_each_pass_of_a_repeat_and_a_pickup():
    s = Score(meter=Meter("2/4"), tempo=120, pickup=Fraction(1, 4))
    s.part("a").add(chords("I:q | IV:q V:q", voicing="close"))
    s.section("all", 1, 2, repeat=2)
    read = chords_per_beat(_sines(*[["C4", "E4", "G4"], ["F4", "A4", "C5"], ["G4", "B4", "D5"]] * 2), s)
    assert read[:3] == [(1, Fraction(2), "C"), (2, Fraction(1), "F"), (2, Fraction(2), "G")]
    assert read[3:] == read[:3]


def test_the_chroma_of_a_c_major_triad_peaks_at_c_e_g():
    chroma = chromagram(_sines(["C4", "E4", "G4"])).mean(axis=1)
    assert set(np.argsort(chroma)[-3:]) == {0, 4, 7}


@pytest.fixture
def undrawn(monkeypatch):
    """Skips the drawing, half a second a PNG, for tests that read file names or the summary."""
    monkeypatch.setattr("euterpe.inspect._png", lambda view, path: path)


def test_inspect_writes_the_five_kinds_of_file_with_summary_last(tmp_path):
    s = Score(tempo=240)
    s.part("only", Harp()).add(melody("c4:q e"))
    paths = inspect(s, tmp_path / "new" / "dir", seed=3)
    assert [p.name for p in paths] == ["roll-only.png", "spectrogram.png", "chroma.png", "loudness.png", "summary.txt"]
    assert all(plt.imread(p).shape[0] > 100 for p in paths[:-1])
    assert paths[-1].read_text().startswith("length: ")


def test_a_file_per_part_under_a_safe_name(tmp_path, undrawn):
    assert [p.name for p in inspect(_piece(), tmp_path)[:2]] == ["roll-left-hand-1.png", "roll-chords.png"]


def test_the_summary_says_one_fact_per_line(tmp_path, undrawn):
    summary = inspect(_piece(), tmp_path)[-1].read_text().splitlines()
    facts = {line.partition(":")[0]: line.partition(": ")[2] for line in summary}
    assert facts["length"].endswith(" s") and facts["loudness"].endswith(" LUFS") and facts["true peak"].endswith(" dBTP")
    assert facts["key"].endswith("written D major") and "(audio 0." in facts["key"]
    assert facts["chord 1.1"].endswith("written D")
    assert facts["part left hand/1"] == "4 notes, D4 to D5"
    assert facts["part chords"] == "3 notes, D4 to A4"
    assert "metric A-PEAK" in facts and "metric A-LUFS" in facts and "metric R-RANGE" not in facts
    assert any(name.startswith("metric T-") or name.startswith("metric M-") for name in facts)


def test_the_summary_names_every_key_written(tmp_path, undrawn):
    s = Score(key=Key("C major"), tempo=240)
    s.part("a", Harp()).add(melody("c4:w | g4:w"))
    s.change(2, key=Key("G major"))
    lines = inspect(s, tmp_path)[-1].read_text().splitlines()
    assert next(line for line in lines if line.startswith("key:")).endswith("written C major, G major from bar 2")


def test_a_part_of_hits_counts_hits(tmp_path, undrawn):
    s = Score(tempo=240)
    s.part("drums", Kit()).add(drums({"kick": "x.x.", "snare": ".x.x"}, "q"))
    assert "part drums: 4 hits" in inspect(s, tmp_path)[-1].read_text()


def test_two_parts_never_share_a_file(tmp_path, undrawn):
    s = Score(tempo=240)
    s.part("a/b", Harp()).add(melody("c4:q"))
    s.part("a b", Harp()).add(melody("e4:q"))
    assert [p.name for p in inspect(s, tmp_path)[:2]] == ["roll-a-b.png", "roll-a-b-2.png"]


@pytest.mark.parametrize("name", ["..", "///"])
def test_a_part_with_no_safe_letters_stays_in_the_directory(tmp_path, undrawn, name):
    s = Score(tempo=240)
    s.part(name, Harp()).add(melody("c4:q"))
    assert inspect(s, tmp_path)[0] == tmp_path / "roll-part.png"


def test_a_score_with_nothing_written_raises_saying_so(tmp_path):
    s = Score()
    s.part("a", Harp())
    with pytest.raises(ValueError, match="nothing"):
        inspect(s, tmp_path)
    with pytest.raises(ValueError, match="no parts"):
        inspect(Score(), tmp_path)


def test_without_matplotlib_inspect_names_the_extra_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    with pytest.raises(ImportError, match=r"euterpe\[view\]"):
        inspect(_piece(), tmp_path / "out")
    assert not (tmp_path / "out").exists()
