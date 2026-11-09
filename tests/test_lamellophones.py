"""The marímbula: a row of tuned metal tongues over a wooden box."""

import numpy as np
import pytest
from euterpe.instruments import Marimbula
from euterpe.lint import lint_audio, lint_notes
from euterpe.pitch import C2, C3, C4
from tests.helpers import band_db, peak_hz


def test_a_tongue_rings_at_the_pitch_it_is_given():
    m = Marimbula(body=None)
    x = np.asarray(m.play(m.hit(0.0, velocity=0.9, pitch=C3)).take(seconds=1.0))
    assert peak_hz(x) == pytest.approx(C3.freq, abs=C3.freq * 0.003)


def test_the_second_partial_is_a_cantilever_not_a_harmonic():
    """The defining trait: a clamped tongue puts its next mode at 6.267 times the pitch, so the
    octave, where a harmonic series or a marimba bar would put it, stays almost empty."""
    m = Marimbula(body=None)
    x = np.asarray(m.play(m.hit(0.0, velocity=0.9, pitch=C3)).take(seconds=0.8))
    f = C3.freq
    tine = band_db(x, 6.267 * f * 2 ** (-0.03), 6.267 * f * 2 ** 0.03)
    octave = band_db(x, 2 * f * 2 ** (-0.03), 2 * f * 2 ** 0.03)
    assert tine - octave > 20


def test_each_tongue_is_its_own_resource():
    m = Marimbula()
    together = m.play(m.hit(0.0, pitch=C2) + m.hit(0.0, pitch=C3))
    assert together.stops == together.ends
    again = m.play(m.hit(0.0, pitch=C3) + m.hit(0.2, pitch=C3))
    assert again.stops[0] < again.ends[0]


def test_a_marimbula_keeps_its_pitch_from_stroke_to_stroke():
    m = Marimbula(body=None)
    hz = [peak_hz(np.asarray(m.play(m.hit(0.0, pitch=C3), seed=s).take(seconds=1.0))) for s in range(12)]
    cents = 1200 * np.log2(np.array(hz) / np.median(hz))
    assert np.ptp(cents) < 5.0


def test_a_marimbula_plays_its_range_cleanly():
    m = Marimbula()
    notes = [n for i, p in enumerate((C2, C3, C4, C3)) for n in m.hit(i * 0.3, velocity=1.0, pitch=p)]
    phrase = m.play(notes)
    x = np.asarray(phrase.take(seconds=3.0))
    assert not lint_audio(x).errors and not lint_notes(phrase).errors
    assert np.abs(x).max() < 1.0


def test_a_marimbula_names_its_limit():
    assert "Limit:" in Marimbula.__doc__
