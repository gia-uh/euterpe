import numpy as np
import pytest
from euterpe.instruments import BassGuitar, Guitar, Harp, PizzicatoStrings, Shape
from euterpe.lint import lint_audio, lint_notes

PRESETS = [Guitar, BassGuitar, Harp, PizzicatoStrings]


@pytest.mark.parametrize("cls", PRESETS)
def test_a_preset_plays_its_range_cleanly(cls):
    inst = cls()
    lo, hi = inst.comfortable
    mid = lo + (hi - lo) // 2
    phrase = inst.play([(0.0, lo, 0.5, 1.0), (0.4, mid, 0.5, 1.0), (0.8, hi, 0.5, 1.0), (0.8, mid + 4, 0.5, 1.0)])
    assert not lint_audio(np.asarray(phrase.take())).errors and not lint_notes(phrase).errors


@pytest.mark.parametrize("cls", PRESETS)
def test_a_preset_names_its_limit(cls):
    assert "Limit:" in cls.__doc__


def test_a_full_strum_at_full_velocity_stays_under_full_scale():
    g = Guitar()
    x = np.asarray(g.play(g.strum(Shape(0, 2, 2, 1, 0, 0), at=0.0, length=2.0, velocity=1.0)).take())
    assert np.abs(x).max() < 1.0
