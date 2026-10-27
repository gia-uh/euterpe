import numpy as np
import pytest
from euterpe.instruments import Accent, Instrument, Note, Staccato, play
from euterpe.pitch import A4, C4
from tests.helpers import Theremin


def test_tuples_and_notes_are_the_same_note():
    a = Theremin().play([(0.0, A4, 0.5, 0.6)]).take(0.6)
    b = Theremin().play([Note(0.0, A4, 0.5, 0.6)]).take(0.6)
    assert np.array_equal(np.asarray(a), np.asarray(b))


def test_hz_and_pitch_mix():
    notes = Theremin().play([(0.0, 440.0, 0.2), (0.3, C4, 0.2)]).notes
    assert notes[0].freq == 440.0 and notes[1].freq == pytest.approx(261.6256, abs=1e-3)


@pytest.mark.parametrize("bad", [(0.0, A4, 0.0), (0.0, A4, -1.0), (0.0, A4, 1.0, 1.5), (-0.1, A4, 1.0)])
def test_bad_notes_are_refused(bad):
    with pytest.raises(ValueError, match="note"):
        Theremin().play([bad])


def test_articulations_act_on_the_note():
    staccato, accent = Theremin().play([Note(0.0, A4, 1.0, 0.8, Staccato()), Note(2.0, A4, 1.0, 0.9, Accent())]).notes
    assert staccato.duration == 0.5 and accent.velocity == 1.0


def test_protocol_without_inheriting():
    class Beep:
        polyphony = 1
        def voice(self, note):
            return Theremin().voice(note)
    assert play(Beep(), [(0.0, A4, 0.2)]).take(0.3).seconds == pytest.approx(0.3)


def test_same_seed_same_samples_other_seed_other_rng():
    a, b = (Theremin().play([(0.0, A4, 0.2)], seed=s).notes[0].rng.random() for s in (1, 1))
    c = Theremin().play([(0.0, A4, 0.2)], seed=2).notes[0].rng.random()
    assert a == b != c


def test_note_is_one_note():
    assert len(Theremin().note(A4, 0.5).notes) == 1
