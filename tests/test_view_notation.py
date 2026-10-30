import builtins
import re
import sys
from fractions import Fraction

import matplotlib.pyplot as plt
import pytest

from euterpe import Key, Meter, Score, chords, drums, melody
from euterpe.instruments import Harp, Kit
from euterpe.view import display
from euterpe.view.notation import PAGE_WIDTH, SCALE


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
    assert not re.search("[-]", svg)


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


def test_the_svg_is_in_the_house_ink():
    svg = _score().notation().svg()
    assert b"#1e2430" in svg
    assert b"black" not in svg


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
])
def test_a_line_with_no_meter_takes_the_length_of_its_longest_bar(text, expected, monkeypatch):
    seen = []
    import euterpe.view.notation as module

    real = module.musicxml_bytes
    monkeypatch.setattr(module, "musicxml_bytes", lambda score, *a, **k: seen.append(score) or real(score, *a, **k))
    melody(text).notation()
    assert seen[0].meter.bar == expected.bar
    assert seen[0].meter.denominator == expected.denominator


def test_a_line_takes_a_meter_it_is_given():
    svg = melody("c4:q d e | f g a").notation(meter=Meter("3/4")).svg()
    assert svg.count(b'class="measure"') == 2


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


def test_display_without_verovio_falls_back_to_the_roll_with_a_note(monkeypatch):
    s = _score("c4:q d e f", Harp())
    monkeypatch.setitem(sys.modules, "verovio", None)
    view = _shown(monkeypatch, s, caption="A scale")
    svg = view.svg()
    assert svg.startswith(s.roll().svg()[:4])
    assert b"euterpe[notation]" in svg
    assert view.caption == "A scale"  # the note is in the drawing, so a caption does not hide it
    assert view.audio is not None


def test_peak_differs_from_the_plain_roll_and_marks_the_highest_note_in_madder():
    s = _score()
    plain, peak = s.roll().svg().decode(), s.roll(peak=True).svg().decode()
    assert plain != peak
    assert "#b0361f" not in plain
    assert peak.count('fill="#b0361f"') == 2  # c5 twice


def test_peak_marks_each_parts_own_highest_note():
    s = _score("c5:q d e f")
    s.part("low").add(melody("c2:q d e f"))
    assert s.roll(peak=True).svg().count(b'fill="#b0361f"') == 2


def test_the_roll_rules_every_bar():
    s = _score()
    tempo = s.tempo_map()
    svg = s.roll().svg().decode()
    assert svg.count('class="eu-bar"') == 4
    assert tempo.seconds(Fraction(1)) == 2.0


def test_the_roll_rules_bars_on_both_passes_of_a_repeat():
    s = _score()
    s.section("A", 1, 2, repeat=2)
    assert s.roll().svg().count(b'class="eu-bar"') == 6


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


def test_the_roll_draws_a_kit_as_rows_of_hits():
    s = Score()
    s.part("kit", Kit()).add(drums({"kick": "x...", "snare": "..x."}, step="q"))
    svg = s.roll().svg()
    assert b"kick" in svg and b"snare" in svg
    assert b"?" not in svg


def test_the_roll_of_a_thin_score_does_not_crash():
    s = Score()
    s.part("silent")
    assert b"no notes" in s.roll().svg()
    with pytest.raises(ValueError, match="no parts"):
        Score().roll()


def test_display_of_a_thin_score_does_not_crash(monkeypatch):
    silent = Score()
    silent.part("a", Harp())
    assert _shown(monkeypatch, silent) is not None
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
