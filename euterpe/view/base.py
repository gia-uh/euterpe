"""A View: what to draw and play, from which sources, with its caption and id. It draws nothing
until a host asks for its bundle (IPython's rich display, which scriptorium also reads)."""

from __future__ import annotations

import base64
import html
import io
import tempfile
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import Unit


def sources(*xs: Unit | Clip) -> list[Clip]:
    """Clips for units and clips alike: a unit is taken for its duration, or the 1 s default."""
    return [x if isinstance(x, Clip) else x.take() for x in xs]


class View:
    """Subclasses implement draw() and may set audio. caption and id travel as display metadata."""

    audio: Clip | None = None
    width: float = 7.0  # inches; row() narrows its panels so the whole row keeps this width

    def __init__(self, *, caption: str | None = None, id: str | None = None):
        self.caption = caption
        self.id = id
        self._svg: bytes | None = None

    def draw(self):
        """A matplotlib Figure, or None for a view that only plays."""
        return None

    def _context(self):
        try:
            import matplotlib
        except ImportError as e:  # the view extra is missing
            raise ImportError("drawing a view needs matplotlib: pip install 'euterpe[view]'") from e
        from euterpe.view.style import fonts, rc

        fonts()
        return matplotlib.rc_context(rc())

    def figure(self):
        """The drawn matplotlib Figure in the house style, or None; the caller closes it."""
        with self._context():
            return self.draw()

    def svg(self) -> bytes | None:
        if self._svg is None:
            import matplotlib.pyplot as plt

            with self._context():
                fig = self.draw()
                if fig is None:
                    return None
                buf = io.BytesIO()
                fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.06,
                            metadata={"Date": None}, dpi=200)
                plt.close(fig)
            self._svg = buf.getvalue()
        return self._svg

    def mp3(self) -> bytes | None:
        if self.audio is None:
            return None
        from euterpe.io import write

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "view.mp3"
            write(self.audio.samples, path)
            return path.read_bytes()

    def _repr_mimebundle_(self, include=None, exclude=None):
        data, parts = {}, []
        svg = self.svg()
        if svg is not None:
            data["image/svg+xml"] = svg.decode()
            parts.append(f'<div style="background:#fff">{svg.decode()}</div>')
        mp3 = self.mp3()
        if mp3 is not None:
            b64 = base64.b64encode(mp3).decode()
            data["audio/mpeg"] = b64
            parts.append(f'<audio controls src="data:audio/mpeg;base64,{b64}"></audio>')
        if self.caption:
            parts.append(f"<div><em>{html.escape(self.caption)}</em></div>")
        data["text/html"] = "\n".join(parts)
        data["text/plain"] = repr(self)
        meta = {k: v for k, v in (("caption", self.caption), ("id", self.id)) if v}
        return data, meta

    def __repr__(self) -> str:
        what = repr(self.audio) if self.audio is not None else ""
        return f"{type(self).__name__}({what})"


class Player(View):
    """Audio only: an MP3 in the book, an audio tag in a notebook."""

    def __init__(self, x: Unit | Clip, seconds: float | None = None, caption: str | None = None, *,
                 id: str | None = None):
        super().__init__(caption=caption, id=id)
        self.audio = x.take(seconds) if isinstance(x, Unit) and seconds is not None else sources(x)[0]


def listen(x: Unit | Clip, seconds: float | None = None, caption: str | None = None, *,
           id: str | None = None) -> Player:
    """The player alone: a unit for seconds (or its duration), or a clip."""
    return Player(x, seconds, caption, id=id)
