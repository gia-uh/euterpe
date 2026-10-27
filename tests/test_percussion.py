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


from euterpe.instruments import Clap, Kick, Snare, Stomp, Tom  # noqa: E402
from euterpe.sound.core import RATE, render  # noqa: E402
from tests.helpers import band_db, peak_hz  # noqa: E402


def one(drum, seconds=0.5, **hit):
    return render(drum.play(drum.hit(0.0, **hit)), seconds)


def test_the_kick_falls_in_pitch():
    x = one(Kick(tune=50.0), 0.4, velocity=1.0)
    assert peak_hz(x[: RATE // 50]) > 75.0
    assert abs(peak_hz(x[RATE // 10 : 3 * RATE // 10]) - 50.0) < 7.5


def test_the_snare_wires_add_the_highs():
    wet, dry = one(Snare(snappy=1.0), 0.3), one(Snare(snappy=0.0), 0.3)
    assert band_db(wet, 3000, 20000) - band_db(dry, 3000, 20000) > 10.0


def test_a_tom_sounds_its_pitch():
    x = one(Tom(tune=110.0), 0.6)
    assert peak_hz(x[RATE // 20 :]) == pytest.approx(110.0, rel=0.03)


def test_two_claps_close_together_both_sound():
    c = Clap()
    assert c.resource(c.hit(0.0)[0]) is None
    one_clap = np.abs(render(c.play(c.hit(0.0)), 0.3)).sum()
    two = np.abs(render(c.play(c.hit(0.0) + c.hit(0.005)), 0.3)).sum()
    assert two > 1.25 * one_clap  # uncorrelated noise adds in power: about 1.41; a stolen clap gives about 1


@pytest.mark.parametrize("cls", [Kick, Stomp, Snare, Tom, Clap])
def test_each_hit_ends(cls):
    d = cls()
    v = d.voice(d.hit(0.0)[0])
    assert v.duration is not None and 0.05 < v.duration < 3.0
