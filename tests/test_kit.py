import pytest
from euterpe.instruments import Clap, Kit, Open
from euterpe.sound.core import RATE, render
from tests.helpers import peak_hz


def test_pattern_reads_each_row_as_steps():
    kit = Kit()
    notes = kit.pattern({kit.kick: "x...x...", kit.snare: "....X..."}, step=0.125)
    assert [(n.time, n.velocity) for n in notes if n.resource is kit.kick] == [(0.0, 0.8), (0.5, 0.8)]
    assert [(n.time, n.velocity) for n in notes if n.resource is kit.snare] == [(0.5, 1.0)]


def test_pattern_repeats_by_the_longest_row():
    kit = Kit()
    notes = kit.pattern({kit.kick: "x...", kit.snare: "..x....."}, step=0.25, repeat=2)
    assert [n.time for n in notes if n.resource is kit.kick] == [0.0, 2.0]


def test_open_steps_open_the_hihat():
    kit = Kit()
    (n,) = kit.pattern({kit.hihat: "..o."}, step=0.1)
    assert isinstance(n.articulation, Open) and n.time == pytest.approx(0.2)


def test_an_unknown_step_names_itself():
    kit = Kit()
    with pytest.raises(ValueError, match="'k' at step 2"):
        kit.pattern({kit.kick: "x.k."}, step=0.1)


def test_each_note_sounds_on_its_own_drum():
    kit = Kit()
    x = render(kit.play(kit.pattern({kit.kick: "x"}, step=0.5)), 0.4)
    assert abs(peak_hz(x[RATE // 10 : 3 * RATE // 10]) - kit.kick.tune) < 0.15 * kit.kick.tune


def test_a_bar_with_every_drum_renders():
    kit = Kit()
    grid = {kit.kick: "x...x...", kit.snare: "..x...x.", kit.hihat: "xxxo xxx", kit.crash: "x.......",
            kit.ride: ".x.x.x.x", kit.toms[0]: "......x.", kit.toms[2]: ".......x", Clap(): "....x..."}
    x = render(kit.play(kit.pattern(grid, step=0.125)), 3.0)
    assert x.shape[0] == 3 * RATE and abs(x).max() > 0.1


def test_the_kit_shares_the_hihat_pedal():
    kit = Kit()
    p = kit.play(kit.pattern({kit.hihat: "o.x."}, step=0.1))
    assert p.stops[0] < p.ends[0]
