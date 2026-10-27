import numpy as np
import pytest
from euterpe.instruments import (Celesta, Clap, Crash, Glockenspiel, HiHat, Kick, Kit, Marimba, Open, Ride,
                                 Snare, Stomp, Timpani, Tom, Xylophone)
from euterpe.lint import lint_audio, lint_notes

DRUMS = [Kick, Stomp, Snare, Tom, Clap, HiHat, Crash, Ride]
PITCHED = [Timpani, Marimba, Xylophone, Glockenspiel, Celesta]


@pytest.mark.parametrize("cls", DRUMS)
def test_a_drum_plays_a_bar_cleanly(cls):
    d = cls()
    notes = [n for i in range(8) for n in d.hit(i * 0.25, velocity=0.5 + 0.5 * (i % 2))]
    assert not lint_audio(np.asarray(d.play(notes).take(seconds=4.0))).errors


@pytest.mark.parametrize("cls", PITCHED)
def test_a_pitched_preset_plays_its_range_cleanly(cls):
    inst = cls()
    lo, hi = inst.comfortable
    mid = lo + (hi - lo) // 2
    notes = [n for i, p in enumerate((lo, mid, hi, mid + 4)) for n in inst.hit(i * 0.3, velocity=1.0, pitch=p)]
    phrase = inst.play(notes)
    assert not lint_audio(np.asarray(phrase.take(seconds=4.0))).errors and not lint_notes(phrase).errors


@pytest.mark.parametrize("cls", DRUMS + PITCHED + [Kit])
def test_a_preset_names_its_limit(cls):
    assert "Limit:" in cls.__doc__


def test_a_full_kit_hit_stays_under_full_scale():
    kit = Kit()
    grid = {kit.crash: "X", kit.kick: "X", kit.snare: "X", kit.hihat: "o", kit.toms[2]: "X"}
    x = np.asarray(kit.play(kit.pattern(grid, step=0.5)).take(seconds=3.0))
    assert np.abs(x).max() < 1.0


@pytest.mark.parametrize("make", [
    lambda: (Kit(), lambda k: k.pattern({k.kick: "x.x.", k.snare: ".x.x", k.hihat: "xoxx"}, step=0.2)),
    lambda: (Timpani(), lambda t: t.roll(0.0, 0.5, pitch=110.0)),
    lambda: (Marimba(), lambda m: m.roll(0.0, 0.5, pitch=440.0)),
])
def test_the_same_seed_gives_the_same_samples(make):
    inst, notes = make()
    a = np.asarray(inst.play(notes(inst), seed=3).take(seconds=1.0))
    b = np.asarray(inst.play(notes(inst), seed=3).take(seconds=1.0))
    c = np.asarray(inst.play(notes(inst), seed=4).take(seconds=1.0))
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_open_is_ignored_off_the_hihat():
    s = Snare()
    assert np.array_equal(np.asarray(s.play(s.hit(0.0, articulation=Open())).take(seconds=0.5)),
                          np.asarray(s.play(s.hit(0.0)).take(seconds=0.5)))
