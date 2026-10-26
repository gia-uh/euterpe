"""Helpers for the book's executed code blocks.

A block calls listen() or show() with a caption; the helper writes the file under build/ in
the working directory and prints the Markdown line that puts it on the page. The file is named
after the caption plus a short hash of its content, so two sounds never share a file and the
same sound always gets the same one.
"""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

from collections.abc import Callable

import numpy as np

from euterpe.io import write
from euterpe.sound.core import Unit, render
from euterpe.sound.osc import Sine


def _name(caption: str, data: bytes) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", caption.lower()).strip("-")[:60].rstrip("-")
    return f"{slug}-{hashlib.sha256(data).hexdigest()[:8]}"


def listen(unit: Unit, seconds: float, caption: str, *, id: str | None = None) -> None:
    """Render unit for seconds, write it to build/audio/ as MP3, and print the line that puts a
    player with this caption on the page. With id, a reference @aud-{id} points at it."""
    samples = render(unit, seconds)
    path = Path("build/audio") / f"{_name(caption, samples.tobytes())}.mp3"
    write(samples, path)
    print(f"![{caption}]({path.as_posix()})" + (f"{{#aud-{id}}}" if id else ""))


def show(fig, caption: str) -> None:
    """Save a matplotlib figure as SVG under build/img/ and print the image line with this caption."""
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    with plt.rc_context({"svg.fonttype": "none"}):
        fig.savefig(buf, format="svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)
    path = Path("build/img") / f"{_name(caption, buf.getvalue())}.svg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buf.getvalue())
    print(f"![{caption}]({path.as_posix()})")


def gain_db(filter: Callable[[Unit], Unit], freq: float) -> float:
    """The gain, in dB rounded to 0.1, that filter (a function from a source to the filtered
    source) gives a sine at freq Hz: peak out over peak in, after the first 0.1 s."""
    dry = render(Sine(freq), 0.5)[4800:]
    wet = render(filter(Sine(freq)), 0.5)[4800:]
    return round(float(20 * np.log10(np.abs(wet).max() / np.abs(dry).max())), 1) + 0.0
