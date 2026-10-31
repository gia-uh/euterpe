"""Views: every Euterpe sound can show itself, in Jupyter and in the book.

display(x) shows a unit's or clip's default view; x.spectrum() and the other methods return
other views; listen(x) gives the player alone. Drawing needs matplotlib (euterpe[view])."""

from euterpe.view.base import Player, View, listen, sources
from euterpe.view.layout import figure, row
from euterpe.view.notation import ScoreWidget
from euterpe.view.signal import chroma, chromagram, default, level, spectrogram, spectrum, waveform
from euterpe.view.system import curve, response
from euterpe.view.theory import circle, keyboard
from euterpe.view.widget import Widget, widget


def display(*xs, normalize: bool = True, caption: str | None = None, id: str | None = None) -> None:
    """Show each object's default view through the host's display (IPython's or scriptorium's),
    at -16 LUFS unless normalize is false. A view is shown as it is."""
    import builtins

    show = getattr(builtins, "display", None)
    if show is None:
        from IPython.display import display as show
    for x in xs:
        if not isinstance(x, View):
            x = x.view(normalize=normalize)
            x.caption = caption if caption is not None else x.caption
            x.id = id if id is not None else x.id
        show(x)

__all__ = [
    "Player", "ScoreWidget", "View", "Widget", "chroma", "chromagram", "circle", "curve", "default", "display", "figure", "keyboard",
    "level", "listen", "response", "row", "sources", "spectrogram", "spectrum", "waveform", "widget",
]
