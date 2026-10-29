import numpy as np
import pytest
from euterpe.instruments import Instrument, Legato, Note, play
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


def test_detached_notes_stay_apart_despite_float_noise():
    p = Theremin().play([(0.0, C4, 0.1), (0.1, E4, 0.1), (0.2, G4, 0.1), (0.3, C4, 0.1)])
    assert len(p.starts) == 4


def test_a_fast_run_reaches_its_last_pitch_before_it_ends():
    from euterpe.instruments.phrase import _slurred
    notes = [Note(0.01 * i, C4 + i, 0.012) for i in range(10)]
    [run] = _slurred(notes)
    assert run._freq.times[-1] <= run.duration and run._freq.levels[-1] == (C4 + 9).freq


def test_a_voice_that_never_ends_fades_at_the_note_end():
    class Drone(Instrument):
        def voice(self, note):
            return Sine(note.freq) * 0.5
    p = Drone().play([(0.0, A4, 0.5)])
    x = np.asarray(p.take())
    assert np.abs(x[-5:]).max() < 0.01


def test_a_plain_function_is_a_voice():
    p = play(lambda n: Sine(n.freq) * ADSR(release=0.01, gate=n.duration) * 0.2,
             [(0.0, C4, 0.5), (0.0, E4, 0.5), (0.0, G4, 0.5), (0.5, A4, 0.5)])
    assert sounding(p, 0.1) == 3 and p.starts[3] == round(0.5 * RATE)
    x = np.asarray(p.take(1.2))
    assert np.abs(x[: round(0.4 * RATE)]).max() > 0.3 and np.abs(x[round(1.1 * RATE):]).max() == 0


def test_an_instruments_glide_sets_how_long_a_slur_takes():
    from euterpe.sound.core import render
    from tests.helpers import peak_hz

    class Slow(Theremin):
        glide = 0.1

    notes = [Note(0.0, 440.0, 0.5), Note(0.5, 880.0, 0.5, articulation=Legato())]
    window = slice(int(0.53 * RATE), int(0.57 * RATE))
    assert abs(peak_hz(render(Theremin().play(notes), 1.0)[window]) - 880.0) < 30
    assert abs(peak_hz(render(Slow().play(notes), 1.0)[window]) - 660.0) < 40
