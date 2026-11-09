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


def test_claves_ring_at_their_tune_with_a_free_bar_overtone_and_die_fast():
    from euterpe.instruments import Claves
    from euterpe.sound.core import render
    from tests.helpers import band_db, peak_hz
    claves = Claves(tune=2500.0, variation=0.0)
    x = render(claves.play(claves.hit(0.0)), 0.6)
    assert abs(peak_hz(x) - 2500.0) < 25
    assert band_db(x, 6800, 6980) > band_db(x, 4900, 5100) + 15   # the 2.756 overtone, not a harmonic 2
    assert np.abs(x[len(x) // 2:]).max() < 0.01 * np.abs(x).max()   # 40 dB down after 0.3 s


def test_bongo_macho_sounds_above_hembra_and_a_muted_stroke_dies_sooner():
    from euterpe.instruments import Bongo, Muted
    from euterpe.sound.core import render
    from tests.helpers import peak_hz
    bongo = Bongo(variation=0.0)
    macho = render(bongo.play(bongo.hit(0.0, drum="macho")), 0.8)
    hembra = render(bongo.play(bongo.hit(0.0, drum="hembra")), 0.8)
    muted = render(bongo.play(bongo.hit(0.0, drum="macho", articulation=Muted())), 0.8)
    assert abs(peak_hz(macho) - 420) < 10 and abs(peak_hz(hembra) - 290) < 10
    ring = lambda x: np.abs(np.asarray(x)[int(0.1 * 48000):int(0.2 * 48000)]).max() / np.abs(x).max()
    assert ring(muted) < ring(macho) / 4


def test_bongo_refuses_a_third_drum():
    from euterpe.instruments import Bongo
    with pytest.raises(ValueError, match="macho and a hembra"):
        Bongo().hit(0.0, drum="tumba")


def test_cajon_bass_is_low_and_slap_is_a_short_bright_crack():
    from euterpe.instruments import Bass, Cajon, Slap
    from euterpe.sound.core import render
    from tests.helpers import band_db, peak_hz
    cajon = Cajon(variation=0.0)
    bass = render(cajon.play(cajon.hit(0.0, velocity=1.0, articulation=Bass())), 0.6)
    slap = render(cajon.play(cajon.hit(0.0, velocity=1.0, articulation=Slap())), 0.6)
    edge = lambda x: band_db(x, 2000, 12000) - band_db(x, 40, 250)
    assert peak_hz(bass) < 150 and peak_hz(slap) > 1000  # the centre's low thump, the edge's crack
    assert edge(slap) > edge(bass) + 25  # the slap carries its energy high, the bass low
    ring = lambda x: np.abs(np.asarray(x)[int(0.05 * 48000):int(0.15 * 48000)]).max() / np.abs(x).max()
    assert ring(slap) < ring(bass) / 5  # the crack dies, the bass goes on ringing


def test_a_cajon_slap_does_not_cut_a_bass_still_ringing():
    from euterpe.instruments import Bass, Cajon, Slap
    cajon = Cajon()
    assert cajon.resource(cajon.hit(0.0, articulation=Bass())[0]) == "bajo"
    assert cajon.resource(cajon.hit(0.0, articulation=Slap())[0]) == "slap"


def test_tumbadora_four_strokes_sound_unlike_each_other_and_its_drums_rise():
    from euterpe.instruments import Bass, Muted, Slap, Tumbadora
    from euterpe.sound.core import render
    from tests.helpers import band_db, peak_hz
    tumbadora = Tumbadora(variation=0.0)
    open_tone = render(tumbadora.play(tumbadora.hit(0.0, velocity=1.0)), 0.8)
    muted = render(tumbadora.play(tumbadora.hit(0.0, velocity=1.0, articulation=Muted())), 0.8)
    slap = render(tumbadora.play(tumbadora.hit(0.0, velocity=1.0, articulation=Slap())), 0.8)
    bass = render(tumbadora.play(tumbadora.hit(0.0, velocity=1.0, articulation=Bass())), 0.8)
    high = lambda x: band_db(x, 2000, 12000)
    mid = lambda x: band_db(x, 200, 800)
    ring = lambda x: np.abs(np.asarray(x)[int(0.08 * 48000):int(0.18 * 48000)]).max() / np.abs(x).max()
    assert peak_hz(bass) < 130 and peak_hz(open_tone) < 130  # both keep the low fundamental
    assert mid(open_tone) > mid(bass) + 6  # the open tone's upper modes, which the palm damps
    assert high(slap) > high(open_tone) + 10  # the slap's bright crack
    assert ring(muted) < ring(open_tone) / 3 and ring(slap) < ring(open_tone) / 3  # both die fast
    low, mid_drum, high_drum = (render(tumbadora.play(tumbadora.hit(0.0, drum=d)), 0.8)
                                for d in ("tumba", "tres-dos", "quinto"))
    assert peak_hz(low) < peak_hz(mid_drum) < peak_hz(high_drum)


def test_tumbadora_refuses_a_fourth_drum_and_an_unknown_one():
    from euterpe.instruments import Tumbadora
    with pytest.raises(ValueError, match="one to three drums"):
        Tumbadora(drums={"a": 100.0, "b": 150.0, "c": 200.0, "d": 250.0})
    with pytest.raises(ValueError, match="no drum 'requinto'"):
        Tumbadora().hit(0.0, drum="requinto")


def test_tambora_heads_sound_their_own_pitch_and_a_muted_stroke_dies_sooner():
    from euterpe.instruments import Muted, Tambora
    from euterpe.sound.core import render
    from tests.helpers import peak_hz
    tambora = Tambora(variation=0.0, coupling=0.0)
    palo = render(tambora.play(tambora.hit(0.0, drum="palo")), 0.8)
    mano = render(tambora.play(tambora.hit(0.0, drum="mano")), 0.8)
    muted = render(tambora.play(tambora.hit(0.0, drum="mano", articulation=Muted())), 0.8)
    assert abs(peak_hz(palo) - 170) < 10 and abs(peak_hz(mano) - 110) < 10
    ring = lambda x: np.abs(np.asarray(x)[int(0.1 * 48000):int(0.2 * 48000)]).max() / np.abs(x).max()
    assert ring(muted) < ring(mano) / 4


def test_the_other_tambora_head_answers_through_the_air():
    from euterpe.instruments import Tambora
    from euterpe.sound.core import render
    from tests.helpers import band_db
    hit = lambda t: np.asarray(render(t.play(t.hit(0.0, velocity=1.0, drum="palo")), 0.6))
    closed, coupled = Tambora(variation=0.0, coupling=0.0), Tambora(variation=0.0, coupling=0.4)
    # The stick head alone has no mode near the hand head's 110 Hz; with the coupling it does.
    assert band_db(hit(coupled), 100, 120) > band_db(hit(closed), 100, 120) + 10


def test_tambora_refuses_a_third_head_and_a_coupling_outside_zero_and_one():
    from euterpe.instruments import Tambora
    with pytest.raises(ValueError, match="palo and a mano"):
        Tambora().hit(0.0, drum="aro")
    with pytest.raises(ValueError, match="coupling"):
        Tambora(coupling=1.5)


def test_maracas_seeds_make_a_broadband_rattle_and_not_a_knock():
    from euterpe.instruments import Maracas
    from euterpe.sound.core import render
    from tests.helpers import band_db
    maracas = Maracas(variation=0.0)
    x = np.asarray(render(maracas.play(maracas.hit(0.0, velocity=1.0)), 0.3))
    assert band_db(x, 3000, 12000) > -20  # the seeds: broadband, where the bare shell is nearly silent
    assert np.sum(np.diff(np.sign(x)) != 0) > 400  # a train of impacts, not one low tone


def test_maracas_macho_and_hembra_each_sound_their_own_gourd():
    from euterpe.instruments import Maracas
    from euterpe.sound.core import render
    from tests.helpers import band_db
    maracas = Maracas(variation=0.0)
    left = np.asarray(render(maracas.play(maracas.hit(0.0, velocity=1.0, hand="izq")), 0.2))
    right = np.asarray(render(maracas.play(maracas.hit(0.0, velocity=1.0, hand="der")), 0.2))
    assert band_db(left, 200, 260) > band_db(right, 200, 260) + 10
    assert band_db(right, 280, 350) > band_db(left, 280, 350) + 10


def test_maracas_refuses_a_third_hand():
    from euterpe.instruments import Maracas
    with pytest.raises(ValueError, match="left and a right hand"):
        Maracas().hit(0.0, hand="centro")


def test_a_faster_scrape_is_brighter_and_crosses_more_ridges():
    from euterpe.instruments import Guiro
    from euterpe.sound.core import render
    from tests.helpers import band_db
    guiro = Guiro(variation=0.0)
    slow = np.asarray(render(guiro.play(guiro.scrape(0.0, length=0.4, speed=0.2, velocity=1.0)), 0.8))
    fast = np.asarray(render(guiro.play(guiro.scrape(0.0, length=0.4, speed=1.0, velocity=1.0)), 0.8))
    crosses = lambda x: int(np.sum(np.diff(np.sign(x)) != 0))
    assert band_db(fast, 4000, 16000) > band_db(slow, 4000, 16000) + 4.5
    assert crosses(fast) > 1.8 * crosses(slow)


def test_the_metal_guira_is_brighter_than_the_gourd_guiro():
    from euterpe.instruments import GOURD, STEEL, Guiro
    from euterpe.sound.core import render
    from tests.helpers import band_db
    gourd = Guiro(material=GOURD, variation=0.0)
    steel = Guiro(material=STEEL, variation=0.0)
    scrape = lambda g: np.asarray(render(g.play(g.scrape(0.0, length=0.4, speed=0.5, velocity=1.0)), 0.8))
    assert band_db(scrape(steel), 4000, 16000) > band_db(scrape(gourd), 4000, 16000) + 4.0


def test_a_new_scrape_stops_the_one_still_sounding_on_the_guiro():
    from euterpe.instruments import Guiro
    from euterpe.sound.core import RATE
    g = Guiro()
    p = g.play(g.scrape(0.0, length=0.5) + g.scrape(0.3, length=0.5))
    assert p.stops[0] <= round(0.3 * RATE) + round(0.005 * RATE) < p.ends[0]


def test_a_scrape_refuses_a_speed_of_zero():
    from euterpe.instruments import Guiro
    with pytest.raises(ValueError, match="speed above 0"):
        Guiro().scrape(0.0, speed=0.0)
