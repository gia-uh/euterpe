import base64
import subprocess
import sys

from euterpe.sound import Pluck, Sine
from euterpe.view import listen


def test_player_bundle_has_audio_and_html():
    data, meta = listen(Pluck(220), caption="A pluck", id="aud-p")._repr_mimebundle_()
    assert base64.b64decode(data["audio/mpeg"]).startswith((b"ID3", b"\xff"))
    assert "<audio" in data["text/html"] and meta == {"caption": "A pluck", "id": "aud-p"}
    assert "image/svg+xml" not in data


def test_unit_displays_through_its_default_view():
    data, _ = Pluck(220)._repr_mimebundle_()
    assert "audio/mpeg" in data


def test_clip_displays_too():
    data, _ = Sine(440).take(0.2)._repr_mimebundle_()
    assert "audio/mpeg" in data


def test_style_is_deterministic():
    from euterpe.view.style import rc
    assert rc()["svg.fonttype"] == "path" and rc()["svg.hashsalt"] == "euterpe"


def test_sound_does_not_import_matplotlib():
    code = "import sys, euterpe.sound; print('matplotlib' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout.strip() == "False"


import warnings
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from euterpe.sound import Clip, Pan, Saw, WhiteNoise
from euterpe.view import default, level, spectrogram, spectrum, waveform


def _svg(view):
    data = view.svg()
    ET.fromstring(data)  # parses
    return data


@pytest.mark.parametrize("make", [
    lambda: waveform(Sine(440).take(0.01)),
    lambda: default(Pluck(220).take(1.0)),
    lambda: spectrum(Saw(220).take(0.5), f0=220),
    lambda: spectrum(WhiteNoise(seed=1).take(0.5)),
    lambda: spectrogram(Pluck(220).take(0.5)),
    lambda: level(Pluck(220).take(0.5)),
])
def test_each_view_draws_the_same_bytes_twice(make):
    assert _svg(make()) == _svg(make())


def test_overlay_draws_one_line_per_source():
    v = waveform(Sine(440).take(0.01), Saw(440).take(0.01), labels=["sine", "saw"])
    fig = v.figure()
    assert len([l for l in fig.axes[0].lines if len(l.get_xdata()) > 2]) == 2 and {"sine", "saw"} <= {t.get_text() for t in fig.axes[0].texts}


def test_spectrum_numbers_the_first_harmonics():
    fig = spectrum(Saw(220).take(0.5), f0=220, harmonics=5).figure()
    assert [t.get_text() for t in fig.axes[0].texts if t.get_text().isdigit()] == ["1", "2", "3", "4", "5"]


def test_stems_of_several_sources_are_small_multiples():
    assert len(spectrum(Sine(220).take(0.5), Saw(220).take(0.5), f0=220).figure().axes) == 2


def test_defaulted_clip_says_so():
    fig = default(Sine(440).take()).figure()
    assert any(t.get_text() == "1 s (default)" for ax in fig.axes for t in ax.texts)


def test_default_view_has_audio_and_two_panels_when_long():
    v = default(Pluck(220).take(1.0))
    assert v.audio is not None and len(v.figure().axes) == 2


def test_unit_view_is_the_default_view():
    data, _ = Pluck(220)._repr_mimebundle_()
    assert "image/svg+xml" in data and "audio/mpeg" in data


def test_methods_are_one_source_shorthands():
    assert isinstance(Saw(220).spectrum(f0=220), type(spectrum(Saw(220), f0=220)))
    assert Saw(220).take(0.2).waveform(span=(0, 0.01)).figure() is not None


@pytest.mark.parametrize("clip", [Pan(Pluck(220), 0.5).take(0.3), Clip(np.zeros(4800))])
@pytest.mark.parametrize("view", [waveform, default, spectrum, spectrogram, level])
def test_stereo_and_silence_draw_cleanly(clip, view):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _svg(view(clip))


@pytest.mark.parametrize("view", [spectrum, spectrogram, level])
def test_every_view_marks_the_default_length(view):
    fig = view(Sine(440)).figure()
    assert any(t.get_text() == "1 s (default)" for ax in fig.axes for t in ax.texts)


from euterpe.sound import Biquad, OnePole, Saturator, Shaper
from euterpe.view import curve, figure, response, row


def test_response_of_a_resonant_lowpass_peaks_near_its_cutoff():
    v = response(Biquad(Sine(1), "lowpass", cutoff=800, q=12))
    line = v.figure().axes[0].lines[0]
    f, db = line.get_xdata(), line.get_ydata()
    assert 700 < f[np.argmax(db)] < 900 and db.max() > 15


def test_response_method_and_labels():
    fig = OnePole(Sine(1), cutoff=500).response().figure()
    assert any("500 Hz" in t.get_text() for t in fig.axes[0].texts)


def test_response_refuses_a_moving_filter():
    with pytest.raises(ValueError, match="fixed"):
        response(Biquad(Sine(1), "lowpass", cutoff=Sine(1) * 100 + 500)).figure()


def test_curve_of_a_hard_clipper_is_flat_beyond_its_knee():
    # at drive 4, hard is 0.891 * min(2x, 1): a straight line up to x = 0.5, flat after
    line = curve(Shaper(Sine(1), "hard", drive=4)).figure().axes[0].lines[-1]
    x, y = line.get_xdata(), line.get_ydata()
    at = lambda v: y[np.argmin(np.abs(x - v))]
    assert at(0.25) == pytest.approx(0.4455, abs=0.01)
    assert at(0.75) == pytest.approx(0.891, abs=0.01) and at(1.0) == pytest.approx(0.891, abs=0.01)


def test_row_puts_views_side_by_side_with_one_caption():
    v = row(waveform(Sine(440).take(0.01)), spectrum(Saw(220).take(0.3), f0=220), caption="two")
    root = ET.fromstring(v.svg())
    assert len([e for e in root if e.tag.endswith("svg")]) == 2
    assert v._repr_mimebundle_()[1] == {"caption": "two"}


def test_row_takes_audio_from_the_first_view_that_has_it():
    assert row(waveform(Sine(440).take(0.01)), Pluck(220).take(0.5).view()).audio is not None


def test_figure_wraps_a_drawing_in_the_house_style():
    import matplotlib.pyplot as plt

    def draw():
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        return fig

    v = figure(draw, caption="hand-made")
    assert b"<svg" in v.svg() and v._repr_mimebundle_()[1] == {"caption": "hand-made"}


def test_a_notebook_shows_svg_and_audio():
    nbformat = pytest.importorskip("nbformat")
    from nbclient import NotebookClient

    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("from euterpe.sound import Pluck\nPluck(220)")])
    NotebookClient(nb, timeout=120, kernel_name="python3").execute()
    html = nb.cells[0].outputs[0]["data"]["text/html"]
    assert "<svg" in html and "<audio" in html


def test_row_panels_do_not_overlap():
    v = row(waveform(Sine(440).take(0.01)), waveform(Sine(440).take(0.01)))
    inner = [e for e in ET.fromstring(v.svg()) if e.tag.endswith("svg")]
    w0 = float(inner[0].get("width"))
    assert float(inner[1].get("x")) >= w0 and not inner[0].get("width").endswith("pt")


def test_waveform_separate_draws_one_panel_per_source():
    fig = waveform(Sine(220).take(0.01), Saw(220).take(0.01), separate=True, labels=["sine", "saw"]).figure()
    assert len(fig.axes) == 2


def test_waveform_reference_is_drawn_in_grey_under_each_panel():
    from euterpe.view.style import RULE
    fig = waveform(Sine(220).take(0.01), Sine(330).take(0.01), separate=True, reference=Saw(220).take(0.01)).figure()
    assert all(any(l.get_color() == RULE and len(l.get_xdata()) > 2 for l in ax.lines) for ax in fig.axes)


def test_waveform_marks_name_moments_in_time():
    fig = waveform(Pluck(220).take(0.5), marks=[(0.2, "gate ends")]).figure()
    assert any(t.get_text() == "gate ends" for t in fig.axes[0].texts)
