import numpy as np
import pytest
from euterpe.instruments import Instrument, Legato, Note
from euterpe.pitch import A4, C4, E4, G4
from euterpe.sound import ADSR, Pan, Sine
from euterpe.sound.core import RATE
from tests.helpers import Theremin


class Organ(Instrument):
    polyphony = 2
    def voice(self, note):
        return Sine(note.freq) * ADSR(attack=0.005, release=0.01, gate=note.duration) * 0.2


def sounding(phrase, t):
    """Voices sounding at t, not counting one in its 5 ms fade after being stopped early."""
    s, fade = round(t * RATE), round(0.005 * RATE)
    return sum(a <= s < (b - fade if b < end else b) for a, b, end in zip(phrase.starts, phrase.stops, phrase.ends))


def test_polyphony_is_never_exceeded():
    p = Organ().play([(0.0, C4, 2.0), (0.1, E4, 2.0), (0.2, G4, 2.0)])
    assert max(sounding(p, t) for t in np.arange(0, 2.5, 0.01)) == 2
    assert p.stops[0] == round(0.2 * RATE) + round(0.005 * RATE)


def test_steal_fades_without_a_jump():
    x = np.asarray(Organ().play([(0.0, C4, 2.0), (0.1, E4, 2.0), (0.2, G4, 2.0)]).take(0.5))
    assert np.abs(np.diff(x)).max() < 0.05


def test_same_resource_stops_the_old_note():
    p = Organ().play([Note(0.0, C4, 2.0, resource=1), Note(0.5, E4, 2.0, resource=1)])
    assert p.stops[0] == round(0.5 * RATE) + round(0.005 * RATE)


def test_mono_overlap_is_one_slurred_voice():
    p = Theremin().play([(0.0, C4, 0.6), (0.5, E4, 0.5)])
    assert len(p.starts) == 1 and p.duration == pytest.approx(1.0 + 0.05, abs=0.02)
    assert len(Theremin().play([(0.0, C4, 0.4), Note(0.4, E4, 0.4, articulation=Legato())]).starts) == 1


def test_out_of_order_late_start_and_tail():
    p = Organ().play([(1.5, E4, 0.5), (1.0, C4, 0.5)])
    assert [n.time for n in p.notes] == [1.0, 1.5]
    x = np.asarray(p.take())
    assert np.abs(x[: RATE // 2]).max() == 0.0 and p.duration == pytest.approx(2.01, abs=0.01)


def test_empty_phrase():
    p = Organ().play([])
    assert p.duration == 0.0 and len(p.take()) == 0


def test_stereo_voice_makes_a_stereo_phrase():
    class Wide(Organ):
        def voice(self, note):
            return Pan(super().voice(note), 0.5) if note.pitch == C4 else super().voice(note)
    p = Wide().play([(0.0, C4, 0.3), (0.0, E4, 0.3)])
    assert p.channels == 2 and np.asarray(p.take()).shape[1] == 2


def test_mono_notes_at_one_time_slur_into_the_last():
    p = Theremin().play([(0.0, C4, 1.0), (0.0, E4, 1.0), (0.0, G4, 1.0)])
    assert len(p.starts) == 1 and np.isfinite(np.asarray(p.take())).all()
