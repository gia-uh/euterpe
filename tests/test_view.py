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
