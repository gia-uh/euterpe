import numpy as np
import pytest
from euterpe.instruments import Struck
from euterpe.sound import ADSR, Sine


class Block(Struck):
    tune = 800.0

    def voice(self, note):
        return Sine(note.freq) * ADSR(attack=0.0, decay=0.05, sustain=0.0, release=0.0, gate=0.05) * note.velocity


def test_hit_is_one_note_at_the_tuning_on_the_drum():
    b = Block()
    (n,) = b.hit(0.5, velocity=0.9)
    assert (n.time, n.pitch, n.velocity) == (0.5, 800.0, 0.9)
    assert b.resource(n) is b


def test_roll_spaces_strokes_and_ramps_velocity():
    notes = Block().roll(0.0, 1.0, velocity=0.2, end=0.8, rate=10.0)
    times = [n.time for n in notes]
    assert len(notes) == 10 and np.allclose(np.diff(times), 0.1)
    assert notes[0].velocity == pytest.approx(0.2) and notes[-1].velocity == pytest.approx(0.8, abs=0.07)


def test_flam_puts_a_soft_grace_before_the_stroke():
    grace, main = Block().flam(1.0, velocity=0.8)
    assert main.time == 1.0 and grace.time == pytest.approx(0.975)
    assert grace.velocity == pytest.approx(0.4)


def test_flam_at_zero_clamps_the_grace():
    grace, main = Block().flam(0.0)
    assert grace.time == 0.0 and main.time > grace.time
