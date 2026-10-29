import numpy as np
import pytest

from euterpe.instruments import ElectricPiano, Note, Organ
from euterpe.pitch import A3, C4, E4
from euterpe.sound.core import RATE, render
from tests.helpers import band_db, peak_hz


def _line_db(x, hz):
    return band_db(x, hz - 5, hz + 5)


def test_one_drawbar_is_one_sine_at_the_note():
    y = render(Organ(drawbars="008000000", click=0.0).play([(0.0, A3, 1.0)]), 1.0)
    assert abs(peak_hz(y) - 220.0) < 1 and _line_db(y, 220.0) > -0.5


def test_each_drawbar_step_is_3_db():
    a = render(Organ(drawbars="808000000", click=0.0).play([(0.0, A3, 1.0)]), 1.0)
    b = render(Organ(drawbars="608000000", click=0.0).play([(0.0, A3, 1.0)]), 1.0)
    drop = (_line_db(a, 110.0) - _line_db(a, 220.0)) - (_line_db(b, 110.0) - _line_db(b, 220.0))
    assert abs(drop - 6.0) < 0.5


def test_percussion_strikes_only_when_no_key_is_held():
    organ = Organ(percussion=3)
    first, second = Note(0.0, C4, 1.0), Note(0.5, E4, 0.5)
    organ.play([first, second]).voices
    assert len(organ._struck) == 1


def test_bad_drawbars_are_refused():
    with pytest.raises(ValueError):
        Organ(drawbars="999")
    with pytest.raises(ValueError):
        Organ(percussion=4)


def test_a_hard_electric_piano_note_rings_a_tine_a_soft_one_does_not():
    ep = ElectricPiano()
    hard = render(ep.play([(0.0, A3, 1.0, 1.0)]), 1.0)
    soft = render(ep.play([(0.0, A3, 1.0, 0.2)]), 1.0)
    attack = slice(0, int(0.05 * RATE))
    assert band_db(hard[attack], 2_200, 8_000) - band_db(soft[attack], 2_200, 8_000) > 10
    tail = slice(int(0.5 * RATE), int(0.9 * RATE))
    assert abs(band_db(hard[tail], 150, 300) - band_db(soft[tail], 150, 300)) < 3


def test_keys_stay_below_full_scale_and_renders_do_not_depend_on_block_size():
    for inst in (Organ(drawbars="888888888", percussion=2), ElectricPiano()):
        chord = [(0.0, p, 0.5, 1.0) for p in (A3, C4, E4)]
        a, b = render(inst.play(chord), 0.8), render(inst.play(chord), 0.8, block=100)
        assert np.array_equal(a, b) and np.abs(a).max() < 1.0
