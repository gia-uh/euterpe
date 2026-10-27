import pytest
import numpy as np
from euterpe.instruments import Finger, GuitarBody, Note, Plucked, Staccato, Steel
from euterpe.pitch import A2, A3
from euterpe.sound.core import RATE
from tests.helpers import band_db
from euterpe.instruments import Guitar, Harp, PizzicatoStrings
from euterpe.pitch import C1, C4, E4, G4, G7


def share_above(x, hz):
    spec = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / RATE)
    return spec[f > hz].sum() / spec.sum()


def test_a_plucked_note_rings_past_its_written_duration():
    assert Plucked().note(A3, 0.2).duration > 1.0


def test_staccato_and_let_ring_false_mute_the_string():
    assert Plucked().play([Note(0.0, A3, 0.4, articulation=Staccato())]).duration < 0.5
    assert Plucked(let_ring=False).note(A3, 0.2).duration < 0.5


def test_harder_is_brighter():
    soft, hard = (np.asarray(Plucked().note(A3, 0.5, v).take(0.3)) for v in (0.3, 1.0))
    assert share_above(hard, 2000) > share_above(soft, 2000)


def test_the_body_adds_its_air_mode():
    bare, boxed = (np.asarray(Plucked(body=b).note(A2, 1.0).take(1.0)) for b in (None, GuitarBody()))
    assert band_db(boxed, 80, 130) > band_db(bare, 80, 130)


def test_parts_are_classes_with_values():
    assert GuitarBody(dry=0.8).dry == 0.8 and GuitarBody().freqs[0] == 100.0


def test_same_seed_same_samples():
    a, b, c = (np.asarray(Plucked().play([(0.0, A3, 0.5)], seed=s).take(0.3)) for s in (1, 1, 2))
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_harp_replucking_a_string_stops_it():
    p = Harp().play([(0.0, C4, 1.0), (0.5, C4, 1.0)])
    assert p.stops[0] == round(0.5 * RATE) + round(0.005 * RATE)


def test_a_harp_arpeggio_is_left_ringing():
    p = Harp().play([(0.0, C4, 0.3), (0.3, E4, 0.3), (0.6, G4, 0.3)])
    s = round(1.5 * RATE)
    assert sum(a <= s < b for a, b in zip(p.starts, p.stops)) == 3
    assert Harp().playable == (C1, G7)


def test_a_pizzicato_is_short():
    assert PizzicatoStrings().note(A3, 0.5).duration < Guitar().note(A3, 0.5).duration / 2


def test_a_section_is_not_one_player():
    one, three = (np.asarray(PizzicatoStrings(players=k).note(A3, 0.5).take(0.3)) for k in (1, 3))
    assert not np.allclose(one, three)

def test_a_section_needs_a_player():
    import pytest
    with pytest.raises(ValueError, match="players"):
        PizzicatoStrings(players=0)


def test_variation_spreads_identical_notes_but_repeats_with_the_seed():
    from euterpe.instruments import BassGuitar
    from euterpe.pitch import E2
    def spread(bass):
        x = np.asarray(bass.play([(1.0 * k, E2, 0.5) for k in range(8)], seed=3).take(8.0))
        rms = [np.sqrt(np.mean(x[k * RATE: k * RATE + RATE // 2] ** 2)) for k in range(8)]
        return np.std(rms) / np.mean(rms)
    assert spread(BassGuitar()) > 2 * spread(BassGuitar(exciter=Finger(position=0.15, brightness=0.5, variation=0.0)))
    a, b = (np.asarray(BassGuitar().play([(0.0, E2, 0.5)], seed=3).take(0.5)) for _ in range(2))
    assert np.array_equal(a, b)


def test_a_bass_player_damps_each_note():
    from euterpe.instruments import BassGuitar
    from euterpe.pitch import E2
    assert BassGuitar().note(E2, 0.5).duration < 1.0


def test_each_bass_note_stands_out_from_the_last():
    from euterpe.instruments import BassGuitar
    from euterpe.pitch import A1, D2
    notes = [(0.5 * k, (D2, A1)[k % 2], 0.45) for k in range(4)]
    x = np.asarray(BassGuitar().play(notes, seed=1).take(2.0)).astype(np.float64)
    def rms(a, b):
        return np.sqrt(np.mean(x[a:b] ** 2))
    for k in range(1, 4):
        s = round(0.5 * k * RATE)
        attack, before = rms(s, s + RATE // 20), rms(s - RATE // 20, s)
        assert 20 * np.log10(attack / before) > 6



def test_each_string_keeps_its_character_and_a_seed_is_another_instrument():
    from euterpe.instruments import Guitar
    g7, again, g8 = Guitar(seed=7), Guitar(seed=7), Guitar(seed=8)
    assert g7.traits(1) == again.traits(1) and g7.traits(1) != g7.traits(2) and g7.traits(1) != g8.traits(1)
    cents, level, decay = g7.traits(1)
    assert abs(cents) <= 3.0 and abs(level) <= 0.05 and abs(decay) <= 0.1


def test_a_string_without_tolerance_is_exact():
    from euterpe.instruments import Guitar, Tolerance
    assert Guitar(string=Steel(tolerance=Tolerance())).traits(1) == (0.0, 0.0, 0.0)


def test_a_string_sounds_its_detuned_pitch_on_every_note():
    from euterpe.instruments import Guitar
    from euterpe.pitch import E5
    from tests.helpers import peak_hz
    dark = Finger(position=0.0, brightness=0.0, variation=0.0)
    g = next(g for g in (Guitar(seed=s, body=None, exciter=dark) for s in range(50)) if abs(g.traits(1)[0]) > 2)
    expected = E5.freq * 2 ** (g.traits(1)[0] / 1200)
    for at in (0.0, 1.0):
        x = np.asarray(g.play(g.pick(1, 12, at=at, length=1.0)).take(at + 1.0))
        assert peak_hz(x[round((at + 0.1) * RATE):]) == pytest.approx(expected, abs=0.3)
