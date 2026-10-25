import numpy as np
import pytest

from euterpe.io import FORMATS, read, write
from euterpe.sound import Sine, render


@pytest.mark.parametrize("ext", sorted(FORMATS))
def test_every_format_round_trips(tmp_path, ext):
    x = render(Sine(440.0) * 0.5, 1.0)
    y, rate = read(write(x, tmp_path / f"t{ext}"))
    assert rate == 48_000 and abs(len(y) - len(x)) <= 2_304   # an MP3 pads by up to two frames


def test_clipping_and_resampling(tmp_path):
    y, rate = read(write(np.full(48_000, 2.0, np.float32), tmp_path / "c.wav", rate=44_100))
    assert rate == 44_100 and len(y) == 44_100 and y.max() <= 1.0


def test_an_unknown_extension_names_the_supported_ones(tmp_path):
    with pytest.raises(ValueError, match=r"\.flac.*\.mp3.*\.ogg.*\.wav"):
        write(np.zeros(10, np.float32), tmp_path / "x.aiff")


def test_render_to_returns_the_path(tmp_path):
    p = render(Sine(440.0), 0.1, to=tmp_path / "s.mp3")
    assert p == tmp_path / "s.mp3" and p.is_file()
