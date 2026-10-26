"""Views: every Euterpe sound can show itself, in Jupyter and in the book.

display(x) shows a unit's or clip's default view; x.spectrum() and the other methods return
other views; listen(x) gives the player alone. Drawing needs matplotlib (euterpe[view])."""

from euterpe.view.base import Player, View, listen, sources
from euterpe.view.signal import default, level, spectrogram, spectrum, waveform

__all__ = ["Player", "View", "default", "level", "listen", "sources", "spectrogram", "spectrum", "waveform"]
