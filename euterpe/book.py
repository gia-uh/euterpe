"""Helpers for the book's executed code blocks.

A block calls listen() or show(); the helper writes the file under build/ in the
working directory and prints the Markdown line that puts it on the page.
"""

from __future__ import annotations

from pathlib import Path

from euterpe.sound.core import Unit, render


def listen(unit: Unit, seconds: float, name: str, caption: str, *, id: str | None = None) -> None:
    """Render unit to build/audio/{name}.mp3 and print the audio line that plays it."""
    path = Path("build/audio") / f"{name}.mp3"
    render(unit, seconds, to=path)
    print(f"![{caption}]({path.as_posix()})" + (f"{{#aud-{id}}}" if id else ""))


def show(fig, name: str, caption: str) -> None:
    """Save a matplotlib figure as build/img/{name}.svg and print the image line."""
    import matplotlib.pyplot as plt

    path = Path("build/img") / f"{name}.svg"
    path.parent.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"svg.fonttype": "none"}):
        fig.savefig(path, format="svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)
    print(f"![{caption}]({path.as_posix()})")
