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
