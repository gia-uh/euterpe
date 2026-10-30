import builtins
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction

import matplotlib.pyplot as plt
from matplotlib.colors import to_hex
import pytest

from euterpe import Key, Meter, Pitch, Score, chords, drums, melody
from euterpe.instruments import Harp, Kit, Note
from euterpe.view import display
from euterpe.view.notation import PAGE_WIDTH, SCALE
from euterpe.view.special import X0, X1, roll as special_roll
from euterpe.view.widget import FONT


def _score(text: str = "c4:q d e f | g:q a b c5 | c5:q b a g | c4:w", instrument=None, **options) -> Score:
    s = Score(**options)
    s.part("melody", instrument).add(melody(text))
    return s


def _cadence() -> Score:
    s = Score()
    s.part("keys", Harp()).add(melody("<c4 e4 g4>:w | <g3 b3 d4> | <c4 e4 g4>"))
    return s


def _shown(monkeypatch, score: Score, **options):
    shown = []
    monkeypatch.setattr(builtins, "display", shown.append, raising=False)
    display(score, **options)
    assert len(shown) == 1
    return shown[0]


def _text(svg: bytes) -> list[str]:
    return re.findall(r"<(?:tspan|text)\b[^>]*>([^<]+)<", svg.decode())


def _bars(svg: bytes) -> list[float]:
    return [float(x) for x in re.findall(r'class="eu-bar" x1="([\d.]+)"', svg.decode())]


def _marks(svg: bytes) -> list[tuple[float, str, str]]:
    """Each note's rectangle in a roll, as (y, fill, data-t)."""
    return [(float(y), fill, t) for y, fill, t in re.findall(r'<rect x="[\d.]+" y="([\d.]+)"[^>]*fill="([^"]+)" data-t="([\d.]+)"', svg.decode())]


def _numerals(view) -> list[tuple[str, float]]:
    """Each numeral under a roll, as (text, seconds), from where it is drawn."""
    found = re.findall(r'<text x="([\d.]+)" y="[\d.]+" font-size="9" font-style="italic">([^<]+)</text>', view.svg().decode())
    return [(text, (float(x) - X0) / (X1 - X0) * view.seconds) for x, text in found]


def _numeral_and_tick_rows(svg: bytes) -> tuple[float, float]:
    text = svg.decode()
    numeral = re.search(r'<text x="[\d.]+" y="([\d.]+)" font-size="9" font-style="italic">', text)
    tick = re.search(r'<text x="[\d.]+" y="([\d.]+)" text-anchor="middle" fill="#6b7078">', text)
    return float(numeral.group(1)), float(tick.group(1))


def test_two_renders_of_a_score_are_byte_equal():
    assert _score().notation().svg() == _score().notation().svg()


def test_the_svg_has_no_script_and_no_font_file():
    svg = _score().notation().svg()
    assert b"<script" not in svg
    assert b"@font-face" not in svg
    assert b"base64" not in svg


def test_the_tempo_mark_needs_no_music_font():
    svg = _score().notation().svg().decode()
    assert "♩" in svg
    assert "Leipzig" not in svg
    assert not re.search("[\ue000-\uf8ff]", svg)


@pytest.mark.parametrize("meter", ["4/4", "2/2", "6/8", "3/8", "2/1", "3/16"])
def test_no_meter_leaves_a_music_font_character_in_the_tempo_mark(meter):
    s = Score(meter=Meter(meter))
    s.part("a").add(melody("r:w"))
    assert not re.search("[\ue000-\uf8ff]", s.notation().svg().decode())


def test_a_full_score_engraves_with_no_music_font_character():
    s = Score(key=Key("D major"), meter=Meter("4/4"), tempo=96, pickup=Fraction(1, 4), title="All of it")
    s.change(3, key=Key("F major"), meter=Meter("6/8"), tempo=60)
    s.ramp(4, 1, 40)
    s.section("A", 2, 3, repeat=3)
    s.section("B", 4, 5)
    tune = s.part("tune", Harp())
    tune.add(melody("a4:q | mf f#4:e' g4> a4_ gb4 < 3[c5:e d5 e5] ( f5:q | g5:q.~ g5:q. ) | f! a4:h. | b4:q. <c4 e4 g4>:q."))
    tune.hairpin((5, 1), (5, 2), ">")
    s.part("bass", clef="bass").add(melody("R | c3:w | R | R | c3:h."))
    s.part("kit", Kit()).add(drums({"kick": "x...", "hihat": "XgoX"}, step="q"), at=2)
    svg = s.notation().svg()
    assert b"<script" not in svg and b"@font-face" not in svg
    assert not re.search("[\ue000-\uf8ff]", svg.decode())


def test_the_svg_is_no_wider_than_a_phone():
    svg = _score(" | ".join(["c4:q d e f"] * 40)).notation().svg().decode()
    width = float(re.search(r'<svg[^>]*\bwidth="([\d.]+)', svg).group(1))
    assert width == PAGE_WIDTH * SCALE / 100 <= 390
    assert re.search(r'<svg[^>]*viewBox="0 0 [\d.]+ [\d.]+"', svg)


def test_a_short_score_is_only_as_high_as_its_music():
    svg = _score("c4:q d e f").notation().svg().decode()
    assert float(re.search(r'<svg[^>]*\bheight="([\d.]+)', svg).group(1)) < 200


def test_a_title_is_left_to_the_caption():
    assert "Eine kleine" not in " ".join(_text(_score(title="Eine kleine").notation().svg()))


def test_the_svg_is_in_the_house_ink():
    svg = _score().notation().svg()
    assert b"#1e2430" in svg
    assert b"black" not in svg


def test_the_svg_is_in_the_house_serif():
    svg = _score().notation().svg().decode()
    assert FONT in svg
    assert "Times" not in svg


def test_bars_shows_those_measures():
    s = _score()
    assert s.notation(bars=(3, 4)).svg().count(b'class="measure"') == 2
    assert s.notation().svg().count(b'class="measure"') == 4


def test_bars_the_score_does_not_have_raise():
    with pytest.raises(ValueError, match="no bars"):
        _score().notation(bars=(8, 9))


def test_numerals_go_in_the_svg_text():
    s = _cadence()
    assert "V" in _text(s.notation(numerals=True).svg())
    assert "V" not in _text(s.notation().svg())


def test_notation_carries_its_caption_and_no_sound():
    view = _score(instrument=Harp()).notation(caption="The opening")
    assert view.caption == "The opening"
    assert view.audio is None
    data, meta = view._repr_mimebundle_()
    assert data["image/svg+xml"].startswith("<svg")
    assert "audio/mpeg" not in data
    assert meta["caption"] == "The opening"


def test_a_score_too_long_for_one_page_raises_and_names_bars(monkeypatch):
    monkeypatch.setattr("euterpe.view.notation.PAGE_HEIGHT", 1000)
    with pytest.raises(ValueError, match="bars="):
        _score(" | ".join(["c4:q d e f"] * 30)).notation()


def test_notation_without_verovio_names_the_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "verovio", None)
    with pytest.raises(ImportError, match=r"euterpe\[notation\]"):
        _score().notation()


def test_line_notation_renders():
    svg = melody("c4:q d e f").notation().svg()
    assert svg.count(b'class="measure"') == 1
    assert svg.count(b'class="note"') == 4


def test_line_notation_is_in_treble_clef_whatever_its_pitch():
    low = melody("c2:q d e f").notation().svg()
    assert b"#E050-" in low  # the G clef's glyph
    assert b"#E062-" not in low  # the F clef's


@pytest.mark.parametrize(("text", "expected"), [
    ("c4:q d e | f g a", Meter("3/4")),
    ("c4:e d e f g a", Meter("3/4")),
    ("c4:q d e f", Meter("4/4")),
    ("c4:q d e f g", Meter("5/4")),
    ("c4:q 3[d:q e]", Meter("3/4")),
    ("3[c4:h d]", Meter("3/4")),
])
def test_a_line_with_no_meter_takes_the_length_of_its_longest_bar(text, expected, monkeypatch):
    seen = []
    import euterpe.view.notation as module

    real = module.musicxml_bytes
    monkeypatch.setattr(module, "musicxml_bytes", lambda score, *a, **k: seen.append(score) or real(score, *a, **k))
    melody(text).notation()
    assert seen[0].meter.bar == expected.bar
    assert seen[0].meter.denominator == expected.denominator
    assert melody(text).notation().svg().count(b'class="measure"') == text.count("|") + 1


def test_a_line_takes_a_meter_it_is_given():
    assert melody("c4:q d e f g a").notation().svg().count(b'class="measure"') == 1
    assert melody("c4:q d e f g a").notation(meter=Meter("3/4")).svg().count(b'class="measure"') == 2


def test_display_shows_the_notation_with_the_player_under_it(monkeypatch):
    s = _score("c4:q d e f", Harp())
    view = _shown(monkeypatch, s, caption="A scale", id="fig-scale")
    data, meta = view._repr_mimebundle_()
    assert view.svg() == s.notation().svg()
    assert "audio/mpeg" in data
    assert data["text/html"].index("<svg") < data["text/html"].index("<audio")
    assert meta == {"caption": "A scale", "id": "fig-scale"}


def test_display_of_a_score_with_no_instrument_shows_the_notation_alone(monkeypatch):
    view = _shown(monkeypatch, _score("c4:q d e f"))
    assert view.audio is None
    assert b'class="note"' in view.svg()


def test_display_of_a_score_with_one_part_without_an_instrument_has_no_player(monkeypatch):
    s = _score("c4:q d e f", Harp())
    s.part("written").add(melody("c3:w"))
    assert _shown(monkeypatch, s).audio is None


@pytest.mark.parametrize("normalize", [True, False])
def test_display_passes_normalize_to_the_player(monkeypatch, normalize):
    view = _shown(monkeypatch, _score("c4:q d e f", Harp()), normalize=normalize)
    assert view.normalize is normalize


def test_display_without_verovio_falls_back_to_the_roll_with_a_note(monkeypatch):
    s = _score("c4:q d e f", Harp())
    monkeypatch.setitem(sys.modules, "verovio", None)
    view = _shown(monkeypatch, s, caption="A scale")
    svg = view.svg()
    assert b"melody" in svg
    assert svg.count(b"data-t=") == s.roll().svg().count(b"data-t=") == 4
    assert b"euterpe[notation]" in svg
    assert view.caption == "A scale"  # the note is in the drawing, so a caption does not hide it
    assert view.audio is not None


def test_peak_marks_the_highest_note_where_it_sounds_and_nothing_else():
    s = _score()
    plain, peak = _marks(s.roll().svg()), _marks(s.roll(peak=True).svg())
    assert "#b0361f" not in {fill for _, fill, _ in plain}
    marked = [(y, t) for y, fill, t in peak if fill == "#b0361f"]
    assert [t for _, t in marked] == ["3.500", "4.000"]  # c5, on bar 2's last beat and bar 3's first
    assert {y for y, _ in marked} == {min(y for y, _, _ in peak)}  # the row of the highest note
    assert [(y, t) for y, _, t in plain] == [(y, t) for y, _, t in peak]


def test_peak_marks_each_parts_own_highest_note():
    s = _score("c5:q f e d")
    s.part("low").add(melody("f2:q c d e"))
    marked = [t for _, fill, t in _marks(s.roll(peak=True).svg()) if fill == "#b0361f"]
    assert marked == ["0.500", "0.000"]  # f5 on the second beat, f2 on the first


def test_the_roll_rules_every_bar_at_its_time():
    s = _score()
    s.change(3, tempo=60)
    view = s.roll()
    tempo = s.tempo_map()
    starts = [tempo.seconds(Fraction(n)) for n in range(4)]
    assert starts == [0.0, 2.0, 4.0, 8.0]
    assert _bars(view.svg()) == pytest.approx([X0 + (X1 - X0) * t / view.seconds for t in starts], abs=0.06)


def test_the_roll_rules_bars_on_both_passes_of_a_repeat():
    s = _score()
    s.section("A", 1, 2, repeat=2)
    assert s.roll().svg().count(b'class="eu-bar"') == 6


def test_the_roll_rules_a_kits_bars_at_their_time():
    s = Score()
    s.part("k", Kit()).add(drums({"kick": "x...", "snare": "..x."}, step="q") * 2)
    view = s.roll()
    assert _bars(view.svg()) == pytest.approx([X0 + (X1 - X0) * t / view.seconds for t in (0.0, 2.0)], abs=0.06)


def test_the_roll_reaches_the_end_of_a_note_past_the_last_bar():
    s = _score("c4:q d e f g")  # five quarters in a bar of four
    notes = s.performance.notes(s, 0)["melody"]
    end = notes[-1].time + notes[-1].duration
    assert end > 2.0
    assert s.roll().seconds == pytest.approx(end)


def test_each_numeral_sits_on_its_beat():
    s = _score("<c4 e4 g4>:h <g3 b3 d4>")
    found = _numerals(s.roll())
    assert [text for text, _ in found] == ["I", "V"]
    assert [t for _, t in found] == pytest.approx([0.0, 1.0], abs=0.01)


def test_an_unchanged_numeral_is_not_written_again():
    s = _score("<c4 e4 g4>:h <c4 e4 g4> | <c4 e4 g4>:w | <g3 b3 d4>:w")
    found = _numerals(s.roll())
    assert [text for text, _ in found] == ["I", "V"]
    assert [t for _, t in found] == pytest.approx([0.0, 4.0], abs=0.01)


def test_a_repeats_short_closing_bar_leaves_out_the_beat_it_does_not_play():
    s = Score(pickup=Fraction(1, 4))
    s.part("a").add(melody("<c4 e4 g4>:q | <c4 e4 g4>:h."))
    s.section("A", 1, 2, repeat=2)
    # The first pass stops bar 2 after three beats and goes back to the pickup; only the last pass has its fourth beat.
    found = _numerals(s.roll())
    assert [text for text, _ in found] == ["I", "?"]
    assert [t for _, t in found] == pytest.approx([0.0, 4.0], abs=0.01)


def test_the_numerals_sit_under_the_notes_and_above_the_ticks():
    s = _cadence()
    svg = s.roll().svg()
    numeral, tick = _numeral_and_tick_rows(svg)
    assert numeral > max(y for y, _, _ in _marks(svg))
    assert tick - numeral >= 9  # the font's size, so the two rows do not touch


def test_the_roll_writes_numerals_and_a_question_mark_where_it_finds_none():
    s = _cadence()
    s.part("keys").add(melody("r:w"))
    texts = _text(s.roll().svg())
    assert "I" in texts and "V" in texts and "?" in texts


def test_the_roll_shows_one_part_by_name():
    s = _score()
    s.part("low").add(melody("c2:w"))
    assert b"low" in s.roll().svg()
    assert b"low" not in s.roll(part="melody").svg()
    with pytest.raises(ValueError, match="no part"):
        s.roll(part="nobody")


def _rows(svg: bytes) -> list[str]:
    return [text for text in _text(svg) if text in {"crash", "ride", "hihat", "tom1", "tom2", "snare", "kick"}]


@pytest.mark.parametrize("instrument", [None, Kit()], ids=["no instrument", "a kit"])
def test_the_roll_draws_drums_as_written_in_notation_order(instrument):
    s = Score()
    s.part("k", instrument).add(drums({"kick": "x...", "tom2": "..x.", "tom1": "x...", "hihat": "xxxx"}, step="q"))
    view = s.roll()
    assert _rows(view.svg()) == ["hihat", "tom1", "tom2", "kick"]
    fig = view.figure()
    assert [t.get_text() for t in fig.axes[0].get_yticklabels()][::-1] == ["hihat", "tom1", "tom2", "kick"]
    assert fig.axes[0].get_ylim() == (-0.5, 3.5)
    plt.close(fig)
    assert b"?" not in view.svg()


def test_the_rows_of_a_kit_part_mark_each_hit_in_its_own_row():
    s = Score()
    s.part("k").add(drums({"tom1": "x...", "tom2": "..x."}, step="q"))
    marks = re.findall(r'<rect x="[\d.]+" y="([\d.]+)"[^>]*data-t="([\d.]+)"', s.roll().svg().decode())
    assert [t for _, t in marks] == ["0.000", "1.000"]
    assert marks[0][0] != marks[1][0]


def test_a_part_name_is_escaped_in_the_roll():
    s = Score()
    s.part("a<b&c").add(melody("c4:q d e f"))
    root = ET.fromstring(s.roll().svg())
    assert "a<b&c" in {text.text for text in root.iter("{http://www.w3.org/2000/svg}text")}


def test_the_roll_of_a_thin_score_does_not_crash():
    s = Score()
    s.part("silent")
    assert b"no notes" in s.roll().svg()
    with pytest.raises(ValueError, match="no parts"):
        Score().roll()


def test_display_of_a_thin_score_does_not_crash(monkeypatch):
    silent = Score()
    silent.part("a", Harp())
    assert _shown(monkeypatch, silent).audio is None
    rests = Score()
    rests.part("a", Harp()).add(melody("r:w"))
    assert _shown(monkeypatch, rests).audio is not None


def test_a_line_of_drums_or_numerals_engraves():
    assert b'class="measure"' in drums({"kick": "x...", "snare": "..x."}, step="q").notation().svg()
    assert b'class="measure"' in chords("I:w | V").notation().svg()


def test_a_short_bar_in_a_line_engraves():
    assert melody("c4:q d e f | g:q").notation().svg().count(b'class="measure"') == 2


def test_the_fallback_needs_neither_verovio_nor_matplotlib(monkeypatch):
    s = _score("c4:q d e f", Harp())
    monkeypatch.setitem(sys.modules, "verovio", None)
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", None)
    data, _ = _shown(monkeypatch, s)._repr_mimebundle_()
    assert "euterpe[notation]" in data["image/svg+xml"]
    assert "audio/mpeg" in data


def test_the_rolls_are_deterministic_and_have_no_playhead():
    s = _score(instrument=Harp(), key=Key("G major"))
    assert s.roll().svg() == s.roll().svg()
    assert b"eu-ph" not in s.roll().svg()


def test_the_roll_saves_as_a_png_through_its_figure(tmp_path):
    s = _cadence()
    s.part("kit", Kit()).add(drums({"kick": "x..."}, step="q"))
    fig = s.roll(peak=True).figure()
    path = tmp_path / "roll.png"
    fig.savefig(path)
    plt.close(fig)
    assert path.read_bytes().startswith(b"\x89PNG")


def test_the_figure_draws_what_the_svg_draws():
    s = _cadence()
    s.change(1, tempo=60)
    fig = s.roll(peak=True).figure()
    ax = fig.axes[0]
    assert [line.get_xdata()[0] for line in ax.lines] == pytest.approx([0.0, 4.0, 8.0])
    assert ax.patches  # the keyboard
    colors = [to_hex(color) for color in ax.collections[0].get_colors()]
    assert colors.count("#b0361f") == 2  # g4, in bars 1 and 3
    assert colors.count("#1f5f8b") == 7
    assert {"I", "V"} <= {text.get_text() for text in ax.texts}
    plain = s.roll().figure()
    assert "#b0361f" not in {to_hex(color) for color in plain.axes[0].collections[0].get_colors()}
    plt.close(fig)
    plt.close(plain)


def test_the_figure_rules_a_kits_bars():
    s = Score()
    s.part("k", Kit()).add(drums({"kick": "x..."}, step="q") * 2)
    fig = s.roll().figure()
    assert len(fig.axes[0].lines) == 3  # two rules and the hits
    plt.close(fig)


def test_a_roll_names_a_pitch_as_it_is_spelled():
    body, *_ = special_roll([Note(0.0, Pitch("Eb4"), 1.0), Note(1.0, Pitch("D#4"), 1.0), Note(2.0, 311.13, 1.0)], 3.0)
    assert ">E♭4<" in body and body.count(">D♯4<") == 2
