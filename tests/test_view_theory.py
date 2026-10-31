import re
from fractions import Fraction

import numpy as np
import pytest

from euterpe import Chord, Key, Scale, Score, melody
from euterpe.instruments import Guitar
from euterpe.instruments.fretted import Shape
from euterpe.pitch import A4, C4, E4, G4
from euterpe.sound.clip import Clip
from euterpe.sound.core import RATE
from euterpe.view import View, chromagram, row
from euterpe.view.special import chord as chord_diagram
from euterpe.view.style import MADDER, WASH
from euterpe.view.theory import keyboard


def _sines(*pitches, seconds: float = 0.5, rate: int = RATE) -> Clip:
    t = np.arange(round(seconds * rate)) / rate
    return Clip(sum(np.sin(2 * np.pi * p.freq * t) for p in pitches) / len(pitches), rate)


def _classes(frame) -> set[int]:
    return set(np.argsort(frame)[-3:].tolist())


def _texts(view: View) -> list[str]:
    return [re.sub("<[^>]+>", "", t) for t in re.findall(r"<text[^>]*>(.*?)</text>", view.svg().decode())]


# chromagram


def test_the_chromagram_of_a_c_major_triad_peaks_at_c_e_and_g():
    chroma = chromagram(_sines(C4, E4, G4))
    assert chroma.shape[0] == 12
    assert _classes(chroma.mean(axis=1)) == {0, 4, 7}
    assert chroma.mean(axis=1)[[0, 4, 7]].sum() > 0.95


def test_each_frame_sums_to_one():
    chroma = chromagram(_sines(C4, E4, G4))
    assert chroma.sum(axis=0) == pytest.approx(np.ones(chroma.shape[1]))


def test_a_frame_is_a_2048_hop():
    assert chromagram(_sines(A4, seconds=2048 * 5 / RATE)).shape == (12, 5)
    assert chromagram(_sines(A4, seconds=(2048 * 5 + 1) / RATE)).shape == (12, 6)


def test_a_silent_clip_gives_silent_frames_and_no_nan():
    chroma = chromagram(Clip(np.zeros(RATE // 2)))
    assert np.isfinite(chroma).all() and not chroma.any()


def test_silence_after_a_note_stays_silent_and_the_note_still_sums_to_one():
    clip = Clip(np.concatenate([_sines(A4, seconds=0.5).samples, np.zeros(RATE)]))
    totals = chromagram(clip).sum(axis=0)
    assert totals[0] == pytest.approx(1.0) and totals[-1] == 0.0


def test_a_clip_shorter_than_the_window_has_a_frame():
    chroma = chromagram(_sines(A4, seconds=0.01))
    assert chroma.shape == (12, 1) and chroma[9, 0] == pytest.approx(chroma.max())


def test_an_empty_clip_has_no_frames():
    assert chromagram(Clip(np.zeros(0))).shape == (12, 0)


def test_energy_outside_55_to_5000_hz_is_left_out():
    t = np.arange(RATE // 2) / RATE
    assert not chromagram(Clip(np.sin(2 * np.pi * 12000 * t)))[:, 2:9].any()  # the clip's cut edges splatter into the band
    low_and_a = np.sin(2 * np.pi * 30 * t) + np.sin(2 * np.pi * A4.freq * t)
    assert chromagram(Clip(low_and_a))[9, 2:9].min() > 0.99


def test_the_frames_line_up_with_the_clip_in_time():
    clip = Clip(np.concatenate([_sines(C4, seconds=1.0).samples, _sines(G4, seconds=1.0).samples]))
    chroma = chromagram(clip)
    second = RATE // 2048
    assert chroma[:, second // 2].argmax() == 0 and chroma[:, second + second // 2].argmax() == 7


def test_a_stereo_clip_keeps_a_note_panned_or_out_of_phase():
    mono = _sines(A4).samples
    assert chromagram(Clip(np.stack([mono, -mono], axis=1)))[9, 2:9] == pytest.approx(1.0, abs=0.01)


def test_the_rate_sets_the_folding():
    assert chromagram(_sines(A4, rate=44100))[:, 2].argmax() == 9


# the views of it


def test_clip_chroma_is_a_view_with_twelve_named_rows():
    view = _sines(C4, E4, G4).chroma(caption="a triad")
    assert isinstance(view, View) and view.caption == "a triad"
    fig = view.figure()
    assert [t.get_text() for t in fig.axes[0].get_yticklabels()][0] == "C" and len(fig.axes[0].get_yticks()) == 12
    data, _ = view._repr_mimebundle_()
    assert data["image/svg+xml"].startswith("<?xml") or "<svg" in data["image/svg+xml"]


def test_clip_chroma_draws_a_silent_and_an_empty_clip():
    assert b"<svg" in Clip(np.zeros(RATE // 4)).chroma().svg()
    assert b"<svg" in Clip(np.zeros(0)).chroma().svg()


def _cadence() -> Score:
    s = Score()
    s.part("keys").add(melody("<c4 e4 g4>:w | <f4 a4 c5> | <g4 b4 d5> | <c4 e4 g4>"))
    return s


def test_score_chroma_needs_no_render(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("rendered")

    monkeypatch.setattr(Score, "play", refuse)
    view = _cadence().chroma()
    assert isinstance(view, View) and view.audio is None and b"<svg" in view.svg()


def test_score_chroma_has_a_column_per_beat_summing_to_one():
    view = _cadence().chroma()
    assert view.matrix.shape == (12, 16)
    assert view.matrix.sum(axis=0) == pytest.approx(np.ones(16))
    assert set(np.nonzero(view.matrix[:, 0])[0]) == {0, 4, 7}
    assert set(np.nonzero(view.matrix[:, 4])[0]) == {0, 5, 9}


def test_score_chroma_weighs_a_tone_by_how_long_it_is_held_in_the_beat():
    s = Score()
    s.part("a").add(melody("c4:q. e4:e"))
    matrix = s.chroma().matrix
    assert matrix[0, 0] == pytest.approx(1.0)
    assert matrix[0, 1] == pytest.approx(0.5) and matrix[4, 1] == pytest.approx(0.5)


def test_score_chroma_writes_the_harmony_above_the_bars_once_per_change():
    fig = _cadence().chroma().figure()
    assert [t.get_text() for t in fig.axes[0].texts] == ["I", "IV", "V", "I"]


def test_score_chroma_marks_a_beat_with_no_chord_with_a_question_mark():
    s = Score()
    s.part("a").add(melody("c4:w"))
    assert [t.get_text() for t in s.chroma().figure().axes[0].texts] == ["?"]


def test_score_chroma_keeps_a_pickup_in_its_bar():
    s = Score(pickup=Fraction(1, 4))
    s.part("a").add(melody("g4:q | c4:w"))
    view = s.chroma()
    assert view.matrix.shape == (12, 5) and view.matrix[7, 0] == pytest.approx(1.0)
    assert view.edges[0] == 0 and view.edges[1] == pytest.approx(0.25)


def test_score_chroma_leaves_rests_white_and_counts_every_part():
    s = Score()
    s.part("a").add(melody("c4:q r r r"))
    s.part("b").add(melody("r:q g4 r r"))
    matrix = s.chroma().matrix
    assert matrix[0, 0] == pytest.approx(1.0) and matrix[7, 1] == pytest.approx(1.0)
    assert not matrix[:, 2:].any()
    assert b"<svg" in s.chroma().svg()


def test_score_chroma_of_nothing_says_so():
    with pytest.raises(ValueError, match="no parts"):
        Score().chroma()
    s = Score()
    s.part("a")
    with pytest.raises(ValueError, match="nothing written"):
        s.chroma()


# the circle


def test_the_circle_names_every_major_and_minor():
    texts = _texts(Key("D major").circle())
    for name in ("C", "G", "D", "A", "E", "B", "F♯", "D♭", "A♭", "E♭", "B♭", "F"):
        assert name in texts
    for name in ("a", "e", "b", "f♯", "c♯", "g♯", "d♯", "b♭", "f", "c", "g", "d"):
        assert name in texts


def test_the_circle_writes_minors_in_italic():
    svg = Key("D major").circle().svg().decode()
    assert re.search(r'<text[^>]*font-style="italic"[^>]*>f♯</text>', svg)
    assert not re.search(r'<text[^>]*font-style="italic"[^>]*>F♯</text>', svg)


def _wedges(key: Key) -> tuple[list[str], list[str]]:
    svg = key.circle().svg().decode()
    return re.findall(rf'<path data-key="([^"]+)" [^>]*fill="{MADDER}"', svg), re.findall(rf'<path data-key="([^"]+)" [^>]*fill="{WASH}"', svg)


@pytest.mark.parametrize("key, marked, near", [
    (Key("D major"), ["D"], ["G", "A"]),
    (Key("B minor"), ["D"], ["G", "A"]),
    (Key("C major"), ["C"], ["F", "G"]),  # the neighbours wrap around the top
    (Key("F major"), ["F"], ["B♭", "C"]),
    (Key("D", "dorian"), ["C"], ["F", "G"]),  # a mode sits with its signature
    (Key("C# major"), ["D♭"], ["F♯", "A♭"]),  # seven sharps is the wedge of five flats
    (Key("Gb major"), ["F♯"], ["B", "D♭"]),
])
def test_the_circle_shades_the_key_and_its_neighbours(key, marked, near):
    wedges, wash = _wedges(key)
    assert wedges == marked and sorted(wash) == sorted(near)


def test_the_circle_says_which_key_it_marks():
    assert "D major" in _texts(Key("D major").circle())
    assert "F♯ minor" in _texts(Key("F# minor").circle())
    assert "D dorian" in _texts(Key("D", "dorian").circle())


def test_two_circles_are_equal_and_the_bundle_carries_the_svg():
    view = Key("D major").circle(caption="near keys")
    assert isinstance(view, View) and view.caption == "near keys"
    data, meta = view._repr_mimebundle_()
    assert ">F♯<" in data["image/svg+xml"] and ">F♯<" in data["text/html"] and "near keys" in data["text/html"]
    assert meta["caption"] == "near keys"
    assert Key("D major").circle().svg() == Key("D major").circle().svg()


# keyboards


def _pressed(view: View) -> list[str]:
    return re.findall(rf'<rect data-key="([^"]+)" [^>]*fill="{MADDER}"', view.svg().decode())


def test_a_chord_on_the_keyboard_presses_its_keys_and_names_them():
    view = Chord("Cmaj7").keyboard()
    assert isinstance(view, View)
    assert _pressed(view) == ["C4", "E4", "G4", "B4"]
    texts = _texts(view)
    assert {"C4", "E4", "G4", "B4"} <= set(texts) and "Cmaj7" in texts


def test_octave_cs_are_grey_and_named_and_a_pressed_c_is_not_grey():
    svg = Chord("Cmaj7").keyboard().svg().decode()
    assert re.search(r'<text[^>]*fill="#9aa0a8"[^>]*>C3</text>', svg) and re.search(r'<text[^>]*fill="#9aa0a8"[^>]*>C5</text>', svg)
    assert not re.search(r'<text[^>]*fill="#9aa0a8"[^>]*>C4</text>', svg)


def test_the_keyboard_spells_as_the_chord_does():
    view = Chord("Ebm").keyboard()
    assert _pressed(view) == ["E♭4", "G♭4", "B♭4"]
    assert "E♭m" in _texts(view)
    assert _pressed(Chord("F#").keyboard()) == ["F♯4", "A♯4", "C♯5"]
    assert "B♭m7♭5" in _texts(Chord("Bbm7b5").keyboard())


def test_a_flat_on_a_white_key_presses_the_white_key():
    view = keyboard([Key("Cb major").degree(1)])
    assert _pressed(view) == ["C♭4"]
    svg = view.svg().decode()
    assert re.search(r'<rect data-key="C♭4" [^>]*width="30"', svg)


def test_a_black_key_stays_on_top_when_its_neighbour_is_pressed():
    svg = Chord("C#").keyboard().svg().decode()
    assert svg.index('data-key="C♯4"') > svg.index('data-key="D4"')


def test_a_scale_on_the_keyboard():
    view = Scale("D", "dorian").keyboard(caption="D dorian")
    assert _pressed(view) == ["D4", "E4", "F4", "G4", "A4", "B4", "C5"]
    assert "D dorian" in _texts(view) and view.caption == "D dorian"
    assert "B♭4" in _pressed(Scale("Bb", "major").keyboard())


def test_the_keyboard_shows_every_note_of_a_wide_chord():
    view = keyboard([Chord("C").pitches()[0] - 24, Chord("C").pitches()[0] + 24])
    assert _pressed(view) == ["C2", "C6"]


def test_two_keyboards_are_equal():
    assert Chord("Cmaj7").keyboard().svg() == Chord("Cmaj7").keyboard().svg()
    assert Scale("C", "major").keyboard().svg() == Scale("C", "major").keyboard().svg()


def test_a_keyboard_with_nothing_pressed_raises():
    with pytest.raises(ValueError, match="no pitches"):
        keyboard([])


def test_keyboards_go_in_a_row():
    both = row(Chord("C").keyboard(), Chord("Am").keyboard(), caption="two chords")
    svg = both.svg().decode()
    assert ">Am<" in svg and svg.count('data-key="') > 40
    assert float(re.search(r'width="([\d.]+)pt"', svg).group(1)) <= 7 * 72 + 12


def test_the_circle_draws_every_church_mode():
    for mode in ("lydian", "mixolydian", "phrygian", "locrian", "aeolian", "ionian"):
        assert b"<svg" in Key("A", mode).circle().svg()


# Shape's label


def _label(shape: Shape) -> str:
    return chord_diagram(shape, Guitar.tuning)[0]


@pytest.mark.parametrize("frets, name", [
    ((None, 0, 2, 2, 1, 0), "Am"),
    ((None, 0, 2, 2, 2, 0), "A"),
    ((3, 2, 0, 0, 0, 3), "G"),
    ((0, 3, 2, 0, 1, 0), "C/E"),
    ((None, 2, 4, 4, 3, 2), "Bm"),
    ((2, 4, 4, 2, 2, 2), "F♯m"),
    ((None, 3, 5, 5, 4, 3), "Cm"),  # its third needs a flat: D♯ would read as no chord
    ((None, 1, 3, 3, 3, 1), "B♭"),
])
def test_a_shape_is_labelled_with_its_chord_name(frets, name):
    assert f">{name}<" in _label(Shape(*frets))


def test_every_shape_gets_a_label_without_raising():
    frets = np.random.default_rng(7).integers(-1, 13, (300, 6)).tolist()
    for row_of_frets in frets:
        assert _label(Shape(*(None if f < 0 else f for f in row_of_frets)))


def test_a_shape_with_a_name_keeps_its_tab():
    assert "x02210" in _label(Shape(None, 0, 2, 2, 1, 0))
    assert ">Am<" in Shape(None, 0, 2, 2, 1, 0).view().svg().decode()


def test_a_shape_no_chord_fits_keeps_todays_label():
    power = _label(Shape(0, 2, 2, None, None, None))
    assert re.search(r'<text [^>]*font-family="ui-monospace,monospace">022xxx</text>', power)
    assert "<tspan" not in power
