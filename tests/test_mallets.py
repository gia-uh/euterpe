import numpy as np
import pytest
from euterpe.instruments import Glockenspiel, Mallet, Marimba, Steelpan
from euterpe.pitch import C4, E4, G5
from euterpe.sound.core import RATE, render
from tests.helpers import band_db, peak_hz


def strike(inst, pitch, seconds=1.0, **kw):
    return render(inst.play(inst.hit(0.0, pitch=pitch, **kw)), seconds)


def near(x, hz):
    return band_db(x, hz * 0.97, hz * 1.03)


def test_the_marimba_bar_is_tuned_to_two_octaves():
    x = strike(Marimba(), C4)[: RATE // 5]
    assert near(x, 4 * C4.freq) > near(x, 3 * C4.freq) + 10


def test_the_glockenspiel_bar_is_free():
    x = strike(Glockenspiel(), G5)[: RATE // 5]
    assert near(x, 2.76 * G5.freq) > near(x, 2.0 * G5.freq) + 10


def test_a_harder_mallet_is_brighter():
    soft = strike(Marimba(mallet=Mallet(0.1)), C4, 0.3)
    hard = strike(Marimba(mallet=Mallet(0.9)), C4, 0.3)
    assert band_db(hard, 2000, 20000) > band_db(soft, 2000, 20000) + 3


def test_each_bar_keeps_its_own_detuning():
    def pitch_of(seed):
        m = Marimba(seed=seed, variation=0.0)
        return [peak_hz(render(m.play(m.hit(0.0, pitch=C4)), 0.5)) for _ in range(2)]
    a, b = pitch_of(1), pitch_of(2)
    assert a[0] == pytest.approx(a[1], abs=0.01) and abs(a[0] - b[0]) > 0.05


def test_the_steelpan_tunes_the_octave_and_the_twelfth():
    """A pan note is not a free bar: its octave and twelfth are tuned over the fundamental,
    where a free bar puts its first partial at 2.76 times the fundamental."""
    x = strike(Steelpan(), E4)[: RATE // 5]
    free = near(x, 2.756 * E4.freq)
    assert near(x, 2 * E4.freq) > free + 10
    assert near(x, 3 * E4.freq) > free + 10


def test_the_steelpan_note_keeps_its_pitch_and_its_fundamental_leads():
    def pitch_of(seed):
        pan = Steelpan(seed=seed, variation=0.0)
        return peak_hz(render(pan.play(pan.hit(0.0, pitch=E4)), 0.5))
    a, b = pitch_of(1), pitch_of(2)
    assert a == pytest.approx(E4.freq, abs=2.0) and b == pytest.approx(E4.freq, abs=2.0)
    x = strike(Steelpan(), E4)[: RATE // 5]
    assert near(x, E4.freq) > near(x, 2 * E4.freq) + 6
