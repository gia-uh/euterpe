import pytest
from euterpe.instruments import BassGuitar, Guitar, Note, Shape
from euterpe.pitch import A2, A3, A4, B2, B3, B5, C2, C3, C4, Cs4, D2, D3, D5, Ds4, E1, E2, E3, E4, E5, F2, F3, F4, Fs3, Fs4, G2, G3, G4
from euterpe.sound.core import RATE

A = Shape(None, 0, 2, 2, 2, 0)


def test_a_shape_gives_its_pitches():
    assert Guitar().pitches(A) == [A2, E3, A3, Cs4, E4]


def test_a_capo_raises_every_string():
    assert Guitar(capo=2).pitches(A) == [B2, Fs3, B3, Ds4, Fs4]


def test_ranges_come_from_the_tuning():
    assert Guitar().playable == (E2, B5) and Guitar().comfortable == (E2, E5)
    assert BassGuitar().playable == (E1, Ds4)


def test_a_shape_must_match_the_strings():
    with pytest.raises(ValueError, match="5.*6|6.*5"):
        Guitar().pitches(Shape(0, 2, 2, 2, 0))


def test_strum_down_goes_low_to_high_a_few_ms_apart():
    notes = Guitar().strum(A, at=1.0, length=0.5)
    assert [n.resource for n in notes] == [5, 4, 3, 2, 1] and [n.pitch for n in notes] == [A2, E3, A3, Cs4, E4]
    assert notes[0].time == 1.0 and notes[1].time == pytest.approx(1.012)


def test_strum_up_hits_the_top_strings_high_to_low():
    assert [n.resource for n in Guitar().strum(A, at=0.0, length=0.2, up=True, strings=3)] == [1, 2, 3]


def test_pick_reads_a_tab():
    [n] = Guitar().pick(5, 2, at=0.0, length=0.5)
    assert n.pitch == B2 and n.resource == 5


def test_pitches_find_their_shape_and_strum():
    assert Guitar().shape([A2, E3, A3, Cs4, E4]) == A
    assert [n.resource for n in Guitar().strum([A2, E3, A3, Cs4, E4], at=0.0, length=0.5)] == [5, 4, 3, 2, 1]


def test_a_line_of_pitches_stays_near_the_hand():
    p = Guitar().play([(0.0, A3, 0.3), (0.3, B3, 0.3), (0.6, Cs4, 0.3)])
    assert [n.resource for n in p.notes] == [3, 2, 2]


def test_notes_together_get_different_strings():
    p = Guitar().play([(0.0, E3, 1.0), (0.0, A3, 1.0)])
    assert len({n.resource for n in p.notes}) == 2


def test_an_unreachable_pitch_warns_and_strum_refuses_it():
    with pytest.warns(UserWarning, match="C2"):
        assert Guitar().play([(0.0, C2, 0.5)]).notes[0].resource is None
    with pytest.raises(ValueError, match="C2"):
        Guitar().strum([C2, E2], at=0.0, length=0.5)


def test_an_up_strum_stops_the_strings_it_hits():
    g = Guitar()
    p = g.play(g.strum(A, at=0.0, length=0.5) + g.strum(A, at=0.25, length=0.25, up=True, strings=3))
    first_e4 = next(i for i, n in enumerate(p.notes) if n.resource == 1 and n.time < 0.1)
    assert p.stops[first_e4] == round(0.25 * RATE) + round(0.005 * RATE)


@pytest.mark.parametrize("pitches, shape", [
    ([B2, Fs3, B3, Ds4, Fs4], Shape(None, 2, 4, 4, 4, 2)),
    ([C3, E3, G3, C4, E4], Shape(None, 3, 2, 0, 1, 0)),
    ([G2, B2, D3, G3, B3, G4], Shape(3, 2, 0, 0, 0, 3)),
    ([F2, C3, F3, A3, C4, F4], Shape(1, 3, 3, 2, 1, 1)),
])
def test_common_chords_find_their_shape(pitches, shape):
    assert Guitar().shape(pitches) == shape


def test_plain_pitches_avoid_a_string_a_tab_already_holds():
    g = Guitar()
    p = g.play(g.pick(1, 0, 0.0, 1.0) + [Note(0.0, E4, 1.0), Note(0.0, B3, 1.0)])
    assert len({n.resource for n in p.notes}) == 3


def test_tuning_is_a_constructor_argument():
    drop_d = Guitar(tuning=(D2, A2, D3, G3, B3, E4))
    assert drop_d.pitches(Shape(0, 0, 0, None, None, None)) == [D2, A2, D3] and drop_d.playable[0] == D2


@pytest.mark.parametrize("bad", [dict(strings=0), dict(strings=-1)])
def test_strum_refuses_no_strings(bad):
    with pytest.raises(ValueError, match="strings"):
        Guitar().strum(A, at=0.0, length=0.5, **bad)


def test_a_shape_must_stay_on_the_fingerboard():
    with pytest.raises(ValueError, match="fret"):
        Guitar().pitches(Shape(None, 0, 2, 2, 2, 25))


def test_strum_keeps_hz_pitches():
    notes = Guitar().strum([110.0, 445.0], at=0.0, length=0.5)
    assert sorted(n.pitch for n in notes) == [110.0, 445.0]


def test_the_tres_strums_its_three_courses_in_c():
    from euterpe.instruments import Tres
    notes = Tres().strum(Shape(0, 0, 0), at=0.0, length=0.5)
    assert [n.resource for n in notes] == [3, 2, 1] and [n.pitch for n in notes] == [G4, C4, E4]


def test_the_tres_g_course_sounds_its_lower_octave_and_the_c_course_does_not():
    from euterpe.instruments import Tres
    from tests.helpers import band_db, peak_hz
    tres = Tres(body=None)
    g = tres.play(tres.pick(3, 0, at=0.0, length=1.0)).take(1.0)
    c = tres.play(tres.pick(2, 0, at=0.0, length=1.0)).take(1.0)
    assert band_db(g, 190, 202) > band_db(g, 150, 180) + 20   # G3 at 196 Hz
    assert band_db(c, 125, 137) < band_db(c, 255, 268) - 20   # no C3 at 131 Hz under C4


def test_the_tres_wants_one_ratio_per_course():
    from euterpe.instruments import Tres
    with pytest.raises(ValueError, match="2 course ratios for 3"):
        Tres(courses=(0.5, 1.0))


def test_the_laud_strums_its_six_doubled_courses_in_d():
    from euterpe.instruments import Laud
    notes = Laud().strum(Shape(0, 0, 0, 0, 0, 0), at=0.0, length=0.5)
    assert [n.resource for n in notes] == [6, 5, 4, 3, 2, 1]
    assert [n.pitch for n in notes] == [D3, Fs3, B3, E4, A4, D5]


def test_the_laud_sounds_both_strings_of_a_course():
    """The defining trait: six courses, each of two strings. A course tuned in octaves must
    carry its lower octave; plucking one string per note would leave that band empty."""
    from euterpe.instruments import Laud
    from tests.helpers import band_db
    laud = Laud(body=None, courses=(1.0, 1.0, 1.0, 0.5, 1.0, 1.0))
    x = laud.play(laud.pick(3, 0, at=0.0, length=1.0)).take(1.0)
    assert band_db(x, 160, 170) > band_db(x, 180, 190) + 40   # E3 under E4, beyond its neighbours


def test_the_laud_has_six_courses_and_sixteen_frets():
    from euterpe.instruments import Laud
    laud = Laud()
    assert laud.tuning == (D3, Fs3, B3, E4, A4, D5) and laud.frets == 16
    with pytest.raises(ValueError, match="5 course ratios for 6"):
        Laud(courses=(1.0,) * 5)
