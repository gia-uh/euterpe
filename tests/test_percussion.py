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


from euterpe.instruments import Crash, HiHat, Open, Ride  # noqa: E402


def to_40db(x):
    m = np.abs(np.asarray(x))
    return np.nonzero(m > 0.01 * m.max())[0][-1] / RATE


def test_an_open_hihat_rings_far_longer_than_a_closed_one():
    h = HiHat()
    closed = render(h.play(h.hit(0.0)), 1.0)
    opened = render(h.play(h.hit(0.0, articulation=Open())), 1.0)
    assert to_40db(opened) > 5 * to_40db(closed)


def test_a_closed_hihat_chokes_the_open_one():
    # each note's rng depends on its order, so the pair cannot be compared by subtraction:
    # read where the phrase stops the open voice instead
    h = HiHat()
    p = h.play(h.hit(0.0, articulation=Open()) + h.hit(0.2))
    assert p.stops[0] <= round(0.2 * RATE) + round(0.005 * RATE) < p.ends[0]


def test_the_hihat_is_bright():
    assert band_db(one(HiHat(), 0.2), 6000, 24000) > 10 * np.log10(0.6)


@pytest.mark.parametrize("cls", [Crash, Ride])
def test_cymbal_hits_overlap(cls):
    c = cls()
    p = c.play(c.hit(0.0) + c.hit(0.3))
    assert p.stops == p.ends and p.ends[0] > round(0.3 * RATE)


from euterpe.instruments import Timpani  # noqa: E402
from euterpe.pitch import C2, G2  # noqa: E402


def test_a_timpano_sounds_its_pitch():
    t = Timpani()
    x = render(t.play(t.hit(0.0, pitch=G2)), 1.5)
    assert peak_hz(x[RATE // 5 :]) == pytest.approx(G2.freq, rel=0.02)


def test_a_timpani_roll_stays_on_one_kettle():
    t = Timpani()
    p = t.play(t.roll(0.0, 1.0, pitch=G2))
    starts = p.starts
    assert all(p.stops[i] <= starts[i + 1] + round(0.005 * RATE) for i in range(len(starts) - 1))


def test_below_the_timpani_warns():
    t = Timpani()
    with pytest.warns(UserWarning, match="below the bottom"):
        t.play(t.hit(0.0, pitch=C2))


def test_a_stomp_is_wood_not_hiss():
    from euterpe.sound import ConvolutionReverb
    s = Stomp()
    assert isinstance(s.voice(s.hit(0.0)[0]), ConvolutionReverb)
    x = np.asarray(s.play(s.hit(0.0, 1.0)).take(seconds=1.5)).mean(axis=1)
    m = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    assert m[f > 2000].sum() / m.sum() < 0.27  # the kick's high-passed click put 33 % up there


def test_roll_gaps_are_one_over_rate_to_a_sample():
    from euterpe.sound.core import RATE
    rate = 13.0
    p = Block().play(Block().roll(0.0, 2.0, rate=rate))
    assert all(abs(d - RATE / rate) <= 1 for d in np.diff(p.starts))


def test_a_decay_of_zero_names_the_decay():
    from euterpe.instruments import Kick
    from euterpe.instruments.percussion import fall
    with pytest.raises(ValueError, match="fall needs time60 above 0 s, got 0: a drum's decay must be above 0"):
        fall(0)
    with pytest.raises(ValueError, match="decay"):
        Kick(decay=0).play(Kick().hit(0.0)).take(0.01)
