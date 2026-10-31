import json
import re
import subprocess
import sys
from fractions import Fraction

import pytest

from euterpe import Key, Score, melody
from euterpe.instruments import Harp, Kit
from euterpe.score.perform import Performance, Swing
from euterpe.view import ScoreWidget, Widget
from euterpe.view.notation import _panel, roll, time_map
from euterpe.view.widget import PLATE, _script

MP3 = b"not really an mp3"


def _score(text: str = "c4:q d e f | g:q a b c5 | c5:q b a g | c4:w", instrument=None, **options) -> Score:
    s = Score(**options)
    s.part("melody", instrument).add(melody(text))
    return s


def _map(s: Score) -> list:
    return time_map(s, s.notation().written)


def _times(events: list, id: str) -> list[tuple[str, float]]:
    return [("on" if id in on else "off", t) for t, on, off in events if id in on or id in off]


def _quarters(s: Score, *quarters) -> list[float]:
    tempo = s.tempo_map()
    return [round(tempo.seconds(Fraction(q) / 4), 3) for q in quarters]


def _natural(html: str) -> tuple[float, str]:
    root = re.search(r"<svg[^>]*>", html).group(0)
    return float(re.search(r'\bwidth="([\d.]+)"', root).group(1)), root


def _widget_html(s: Score, **options) -> str:
    return s.view(**options).html(MP3)


# -- size and plate ----------------------------------------------------------------------------


def test_the_natural_width_is_the_columns():
    width, root = _natural(_score().notation()._repr_mimebundle_()[0]["text/html"])
    assert 520 <= width <= 580
    assert f"max-width:{width:g}px" in root
    assert "width:100%" in root


def test_the_panel_scrolls_sideways_on_a_phone_and_inside_itself():
    html = _score().notation()._repr_mimebundle_()[0]["text/html"]
    assert re.search(r'class="eu-score" style="[^"]*max-height:60vh[^"]*overflow:auto', html)
    assert re.search(r"@media \(max-width:640px\)\{[^}]*\.eu-score>svg\{min-width:600px\}", html)


def test_the_inner_svg_has_its_size_for_print():
    svg = _score().notation().svg().decode()
    width, height = re.search(r'<svg width="(\d+)" height="(\d+)"', svg).groups()
    inner = re.search(r'<svg[^>]*class="definition-scale"[^>]*>', svg).group(0)
    for name, value in (("x", "0"), ("y", "0"), ("width", width), ("height", height)):
        assert f' {name}="{value}"' in inner


def test_a_score_wraps_to_systems_at_that_width():
    svg = _score(" | ".join(["c4:q d e f"] * 40)).notation().svg()
    assert svg.count(b'class="system"') > 1


@pytest.mark.parametrize("view", [
    lambda: _score().notation(bars=(1, 2), caption="Two bars"),
    lambda: melody("c4:q d e f").notation(),
    lambda: _score().roll(),
], ids=["notation", "line_notation", "roll"])
def test_a_still_view_is_the_panel_alone_on_the_plate(view):
    data, meta = view()._repr_mimebundle_()
    html = data["text/html"]
    assert meta["site"] == "html"
    assert html.startswith("<figure")
    assert PLATE in html
    assert 'class="eu-score"' in html
    assert "<audio" not in html and "eu-map" not in html and "<script" not in html
    assert data["image/svg+xml"].startswith("<svg")


def test_a_still_views_caption_closes_its_figure():
    html = _score().notation(caption="Two <bars>")._repr_mimebundle_()[0]["text/html"]
    assert html.endswith("<figcaption style=\"font-style:italic;font-size:.9em;margin-top:4px\">Two &lt;bars&gt;</figcaption></figure>")


# -- the time map ------------------------------------------------------------------------------


def test_the_map_follows_the_tempo_map_through_a_ramp():
    s = _score("c4:q d e f | g:q a b c5 | c5:q b a g | f4:q e d c")
    s.ramp(2, 2, 60)
    events = _map(s)
    assert [t for t, on, _ in events if on] == pytest.approx(_quarters(s, *range(16)), abs=0.001)
    assert events[-1][0] == _quarters(s, 16)[0]


def test_every_id_in_the_map_is_in_the_svg():
    s = _score("<c4 e4 g4>:h c4:e d e f | r:q 3[g4:e a b] c5:h~ | c5:w")
    svg = s.notation().svg().decode()
    ids = {i for _, on, off in _map(s) for i in on + off}
    assert ids
    assert all(f'id="{i}"' in svg for i in ids)


def test_the_first_event_is_at_zero_and_each_note_goes_on_then_off():
    events = _map(_score())
    assert events[0][0] == 0
    assert events[0][1] and not events[0][2]
    assert [t for t, _, _ in events] == sorted({t for t, _, _ in events})
    assert not events[-1][1] and events[-1][2]


def test_a_pickup_counts_from_zero_and_the_downbeat_comes_after_it():
    s = _score("g4:q | c5:q d e f | g:w", pickup=Fraction(1, 4), tempo=60)
    times = [t for t, on, _ in _map(s) if on]
    assert times[0] == 0
    assert times[1] == round(s.tempo_map().seconds(Fraction(1, 4)), 3) == 1.0


def test_a_repeated_bar_is_in_the_map_on_both_passes():
    s = _score("c4:q d e f | g:w", tempo=120)
    s.section("A", 1, 1, repeat=2)
    events = _map(s)
    first = events[0][1][0]
    assert _times(events, first) == [("on", 0.0), ("off", 0.5), ("on", 2.0), ("off", 2.5)]
    assert not any("-rend" in i for _, on, off in events for i in on + off)
    assert events[-1][0] == 6.0


def test_a_repeat_goes_on_for_every_pass():
    s = _score("c4:w | g4:w", tempo=120)
    s.section("A", 1, 1, repeat=3)
    events = _map(s)
    assert [t for kind, t in _times(events, events[0][1][0]) if kind == "on"] == [0.0, 2.0, 4.0]
    assert events[-1][0] == 8.0


def test_the_last_note_of_a_pass_goes_off_where_the_next_pass_comes_on():
    s = _score("c4:w", tempo=120)
    s.section("A", 1, 1, repeat=2)
    assert _map(s) == [[0.0, [i := _map(s)[0][1][0]], []], [2.0, [i], [i]], [4.0, [], [i]]]


def test_a_repeats_short_closing_bar_leaves_out_what_it_does_not_play():
    s = _score("g3:q | c4:q d e g3", pickup=Fraction(1, 4), tempo=60)
    s.section("A", 1, 2, repeat=2)
    assert s.tempo_map().played[1].length == 1
    events = _map(s)
    on = [t for t, ids, _ in events if ids]
    assert on == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]


def test_the_map_lands_where_the_swing_puts_a_note():
    s = _score("c4:e d e f g a b c5", tempo=60, performance=Performance(swing=Swing(2 / 3)))
    notes = s.performance.notes(s, 0)["melody"]
    assert [t for t, on, _ in _map(s) if on] == pytest.approx([round(n.time, 3) for n in notes], abs=0.001)


def test_a_tuplets_times_are_exact():
    s = _score("3[c4:q d e] f:h", tempo=60)
    assert [t for t, on, _ in _map(s) if on] == [0.0, 0.667, 1.333, 2.0]


def test_every_part_is_in_the_map_at_its_time():
    s = Score(tempo=120)
    s.part("a").add(melody("c5:w"))
    s.part("b").add(melody("c3:q d e f"))
    events = _map(s)
    assert len(events[0][1]) == 2
    assert [len(on) for _, on, _ in events] == [2, 1, 1, 1, 0]


def test_a_tied_note_is_on_through_the_tie():
    s = _score("c4:h~ c4:h | d4:w", tempo=120)
    assert [len(on) for _, on, _ in _map(s)] == [1, 1, 1, 0]


def test_the_map_is_the_same_each_time():
    assert _map(_score()) == _map(_score())


# -- the roll's map ----------------------------------------------------------------------------


def test_the_rolls_map_lists_every_note_once_with_its_played_start_and_end():
    s = _score(instrument=Harp())
    s.part("kit", Kit()).add(melody("r:w"))
    view = s.roll()
    events = view.events()
    notes = s.performance.notes(s, 0)["melody"]
    ids = re.findall(r'<rect [^>]*data-t="[\d.]+" id="(r\d+)"', view.svg().decode())
    assert len(ids) == len(set(ids)) == len(notes)
    assert all(sum(i in on for _, on, _ in events) == 1 and sum(i in off for _, _, off in events) == 1 for i in ids)
    spans = sorted((_times(events, i)[0][1], _times(events, i)[1][1]) for i in ids)
    assert spans == pytest.approx(sorted((n.time, n.time + n.duration) for n in notes), abs=0.001)


def test_the_rolls_map_holds_a_kits_hits():
    from euterpe import drums

    s = Score()
    s.part("k", Kit()).add(drums({"kick": "x...", "snare": "..x."}, step="q"))
    ids = {i for _, on, _ in s.roll().events() for i in on}
    assert len(ids) == 2
    assert all(f'id="{i}"' in s.roll().svg().decode() for i in ids)


def test_the_rolls_lanes_are_one_system():
    s = _score()
    s.part("low").add(melody("c2:w"))
    assert s.roll().svg().count(b'class="system"') == 1


# -- the widget --------------------------------------------------------------------------------


def test_display_of_a_playable_score_is_one_widget():
    s = _score("c4:q d e f", Harp())
    view = s.view()
    assert isinstance(view, ScoreWidget) and isinstance(view, Widget)
    html = view.html(MP3)
    assert 'class="euterpe-widget euterpe-score"' in html
    assert html.count("<audio") == 1 and html.count("<figure") == 1
    for before, after in (('class="eu-score"', 'class="eu-map"'), ('class="eu-map"', 'class="eu-grid"'),
                          ('class="eu-grid"', "<audio")):
        assert html.index(before) < html.index(after)


def test_the_widgets_map_is_json_in_the_figure():
    s = _score("c4:q d e f", Harp())
    html = _widget_html(s)
    found = re.search(r'<script type="application/json" class="eu-map">(.*?)</script>', html).group(1)
    assert json.loads(found) == _map(s)


def test_the_widget_prints_the_score_over_the_envelope_and_the_spectrum():
    s = _score("c4:q d e f", Harp())
    svg = s.view().svg().decode()
    assert s.notation().svg().decode() in svg
    assert svg.index('class="note"') < svg.index("eu-avg")


def test_the_widgets_bundle_asks_the_site_for_its_html():
    data, meta = _score("c4:q d e f", Harp()).view()._repr_mimebundle_()
    assert meta["site"] == "html"
    assert {"text/html", "image/svg+xml", "audio/mpeg"} <= set(data)


def test_a_score_on_the_widget_styles_what_sounds_in_madder():
    html = _widget_html(_score("c4:q d e f", Harp()))
    assert ".euterpe-score .eu-on,.euterpe-score .eu-on *{fill:#b0361f;stroke:#b0361f}" in html
    assert re.search(r"\.eu-cursor\{[^}]*stroke:#b0361f[^}]*stroke-width:1\.5[^}]*pointer-events:none", html)


def test_without_verovio_the_roll_is_the_panel_with_the_same_map(monkeypatch):
    s = _score("c4:q d e f", Harp(), tempo=120)
    monkeypatch.setitem(sys.modules, "verovio", None)
    view = s.view()
    assert isinstance(view, ScoreWidget)
    html = view.html(MP3)
    assert "euterpe[notation]" in html
    events = json.loads(re.search(r'class="eu-map">(.*?)</script>', html).group(1))
    assert [t for t, on, _ in events if on] == [0.0, 0.5, 1.0, 1.5]
    assert all(f'id="{i}"' in html for _, on, _ in events for i in on)


def test_no_blank_line_ends_the_raw_html_block_in_markdown():
    s = _score("c4:q d e f", Harp())
    assert "\n\n" not in s.view().html(MP3)
    assert "\n\n" not in s.notation()._repr_mimebundle_()[0]["text/html"]
    assert "\n\n" not in s.roll()._repr_mimebundle_()[0]["text/html"]


def test_a_figure_without_a_map_is_left_to_the_plain_widget():
    assert 'class="eu-score"' not in Widget(_score("c4:q d e f", Harp()).play().take()).html(MP3)


def test_the_widget_animates_only_its_special_views_marks():
    assert '".eu-sp [data-t]"' in _script()


# -- page weight -------------------------------------------------------------------------------


def _thirty_bars() -> Score:
    s = Score(key=Key("G major"))
    s.part("a").add(melody(" | ".join(["g4:q a b c5"] * 30)))
    s.part("b").add(melody(" | ".join(["g3:h d4"] * 30)))
    return s


def test_a_thirty_bar_two_part_score_stays_in_the_budget():
    s = _thirty_bars()
    view = s.notation()
    assert len(view.svg()) < 250_000
    assert len(json.dumps(time_map(s, view.written), separators=(",", ":"))) < 10_000


def test_the_widget_without_the_engraving_the_map_and_the_mp3_stays_in_the_budget():
    view = _score(instrument=Harp()).view()
    html = view.html(MP3)
    assert _panel(view.panel.svg()) in html
    rest = html.replace(_panel(view.panel.svg()), "")
    rest = re.sub(r'(class="eu-map">).*?(</script>)', r"\1\2", rest)
    assert len(rest.encode()) < 12_000


def test_the_script_stays_under_its_budget():
    assert len(_script().encode()) < 8192


def test_the_library_does_not_import_verovio():
    code = "import sys, euterpe, euterpe.view; sys.exit('verovio' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_the_roll_of_a_score_needs_no_engraving(monkeypatch):
    monkeypatch.setitem(sys.modules, "verovio", None)
    assert roll(_score()).events()
