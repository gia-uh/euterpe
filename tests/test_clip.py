import numpy as np
import pytest

from euterpe.io import write
from euterpe.sound import Clip, Pan, Sine, render


def test_take_renders_like_render():
    c = (Sine(440) * 0.5).take(0.25)
    assert isinstance(c, Clip) and c.seconds == 0.25
    assert np.array_equal(np.asarray(c), render(Sine(440) * 0.5, 0.25))


def test_take_without_seconds_uses_the_default():
    c = Sine(440).take()
    assert c.seconds == 1.0 and c.defaulted


def test_clip_read_round_trips(tmp_path):
    c = Sine(440).take(0.1)
    write(np.asarray(c), tmp_path / "a.wav")
    assert Clip.read(tmp_path / "a.wav").seconds == pytest.approx(0.1)


def test_stereo_clip_reports_channels():
    assert Pan(Sine(440), 0.3).take(0.1).channels == 2


def test_clip_length_is_its_frames():
    assert len(Sine(440).take(0.5)) == 24000


def test_take_caption_travels_to_the_default_view():
    pytest.importorskip("matplotlib")
    c = Sine(440).take(0.2, "A sine")
    assert c.caption == "A sine"
    data, meta = c._repr_mimebundle_()
    assert meta["caption"] == "A sine"
    assert "image/svg+xml" in data and "audio/mpeg" in data
    assert Sine(440).take(caption="B").caption == "B"
