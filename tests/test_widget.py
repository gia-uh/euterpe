import base64
import builtins
import subprocess
import sys

import numpy as np
import pytest

from euterpe.instruments import Guitar, Harp, Kit
from euterpe.instruments.fretted import Shape
from euterpe.pitch import C4, E4, G4
from euterpe.sound import ADSR, Pluck, Sine
from euterpe.sound.clip import Clip
from euterpe.view import Widget, listen
from euterpe.view.loudness import CEILING, TARGET, loudness


def decoded(view, tmp_path) -> Clip:
    from euterpe.io import read

    path = tmp_path / "v.mp3"
    path.write_bytes(view.mp3())
    samples, rate = read(path)
    return Clip(samples, rate)


def rock_bar():
    kit = Kit()
    grid = {kit.kick: "x.......x.x.....", kit.snare: "....x.......x...", kit.hihat: "x.x.x.x.x.x.x.x."}
    return kit.play(kit.pattern(grid, step=0.15, repeat=2))


@pytest.mark.parametrize("make", [lambda: Sine(440.0).take(1.5), lambda: rock_bar().take(5.0)], ids=["sine", "kit"])
def test_the_widget_plays_at_the_target_loudness(make, tmp_path):
    clip = make()
    view = Widget(clip)
    g = view.gain()[0]
    expected = TARGET if g * np.abs(clip.samples).max() < 10 ** (CEILING / 20) - 1e-6 else loudness(clip) + 20 * np.log10(g)
    assert loudness(decoded(view, tmp_path)) == pytest.approx(expected, abs=0.5)


def test_the_sine_lands_on_the_target(tmp_path):
    assert loudness(decoded(Widget(Sine(440.0).take(1.5)), tmp_path)) == pytest.approx(TARGET, abs=0.5)


def test_a_peaky_click_stays_under_the_ceiling(tmp_path):
    click = (Sine(2000.0) * ADSR(attack=0.0005, decay=0.003, sustain=0.0, release=0.0, gate=0.004)).take(1.0)
    view = Widget(click)
    g = view.gain()[0]
    assert 20 * np.log10(np.abs(click.samples).max() * g) <= CEILING + 1e-6
    assert 20 * np.log10(np.abs(decoded(view, tmp_path).samples).max()) <= -0.5


def test_normalize_false_keeps_the_rendered_level(tmp_path):
    clip = (Sine(440.0) * 0.05).take(1.0)
    view = Widget(clip, normalize=False)
    assert view.gain()[0] == 1.0
    assert loudness(decoded(view, tmp_path)) == pytest.approx(loudness(clip), abs=0.5)
    assert "rendered level" in view.level_line()


def test_silence_and_very_short_clips_do_not_raise():
    silent = Widget(Clip(np.zeros(4800)))
    assert silent.gain()[0] == 1.0 and silent.level_line() == "silent"
    assert "audio/mpeg" in Widget(Sine(440.0).take(0.1))._repr_mimebundle_()[0]


def test_listen_normalizes_too():
    assert listen((Sine(440.0) * 0.05).take(1.0)).gain()[0] > 1
    assert listen((Sine(440.0) * 0.05).take(1.0), normalize=False).gain()[0] == 1.0


def test_the_bundle_has_html_svg_audio_and_asks_for_the_site():
    data, meta = Pluck(220).take(1.0, "A pluck")._repr_mimebundle_()
    assert set(data) == {"text/html", "image/svg+xml", "audio/mpeg", "text/plain"}
    assert meta == {"caption": "A pluck", "site": "html"}
    h = data["text/html"]
    assert h.startswith('<figure class="euterpe-widget"') and h.endswith("</figure>")
    assert h.count("<audio") == 1 and "<svg" in h and "<script>" in h and "<figcaption" in h
    assert "\n\n" not in h  # a blank line would end a raw HTML block in Markdown


def test_the_same_sound_gives_the_same_bytes():
    a, _ = Pluck(220).take(1.0)._repr_mimebundle_()
    b, _ = Pluck(220).take(1.0)._repr_mimebundle_()
    assert a["text/html"] == b["text/html"] and a["image/svg+xml"] == b["image/svg+xml"]


def test_a_widget_stays_under_12_kb_without_its_mp3_and_script():
    h = Widget(rock_bar().take(5.0)).html(b"")
    assert len(h[: h.index("<script>")].encode()) < 12_000


def test_defaulted_lengths_are_named():
    assert "1 s (default)" in Widget(Sine(440).take()).svg().decode()
    assert "10 s (default)" in Widget(Pluck(55, damping=0.9999)).svg().decode()


def test_display_hands_the_widget_to_the_host(monkeypatch):
    shown = []
    monkeypatch.setattr(builtins, "display", shown.append, raising=False)
    import euterpe

    euterpe.display(Sine(440.0).take(0.5), normalize=False, caption="A sine")
    assert isinstance(shown[0], Widget) and shown[0].normalize is False and shown[0].caption == "A sine"


def test_the_widget_needs_no_matplotlib():
    code = ("import sys; from euterpe.sound import Sine; Sine(440).take(0.2)._repr_mimebundle_(); "
            "assert 'matplotlib' not in sys.modules")
    subprocess.run([sys.executable, "-c", code], check=True)


# -- special views ---------------------------------------------------------------------------

def test_a_clip_keeps_the_unit_it_came_from():
    phrase = Harp().play([(0.0, C4, 0.5)])
    assert phrase.take(1.0).source is phrase


def test_a_shape_shows_its_chord_diagram_and_strums():
    view = Shape(None, 0, 2, 2, 2, 0).view()
    svg = view.svg().decode()
    assert "×" in svg and "x02220" in svg and ">2<" in svg and "C♯" in svg
    assert view.audio.seconds == pytest.approx(2.0)


def test_a_high_shape_names_its_first_fret():
    assert ">5fr<" in Shape(5, 7, 7, 6, 5, 5).view().svg().decode()


def test_a_guitar_phrase_shows_tablature():
    guitar = Guitar()
    view = Widget(guitar.play(guitar.pick(1, 3, 0.0, 0.5) + guitar.pick(6, 0, 0.5, 0.5)).take(1.5))
    body = view.special[0]
    assert ">3<" in body and ">0<" in body and 'data-t="0.500"' in body
    assert body.count("<line") >= 6


def test_a_kit_phrase_shows_a_hit_grid():
    body = Widget(rock_bar().take(5.0)).special[0]
    assert ">hi-hat<" in body and ">snare<" in body and ">kick<" in body and ">crash<" not in body


def test_a_pitched_phrase_shows_a_piano_roll():
    body = Widget(Harp().play([(0.25 * k, p, 0.9) for k, p in enumerate([C4, E4, G4])]).take(2.0)).special[0]
    assert ">C4<" in body and ">E4<" in body and ">G4<" in body


def test_plain_sounds_and_mixes_have_no_special_view():
    a, b = Harp().play([(0.0, C4, 0.5)]), Harp().play([(0.5, E4, 0.5)])
    assert Widget(Sine(440.0).take(0.5)).special is None
    assert Widget((a + b).take(1.0)).special is None


def test_special_views_go_to_print_too():
    data, _ = Shape(None, 0, 2, 2, 2, 0)._repr_mimebundle_()
    assert "x02220" in data["image/svg+xml"] and "x02220" in data["text/html"]
    assert base64.b64decode(data["audio/mpeg"])
