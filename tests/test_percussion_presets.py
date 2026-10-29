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
    notes = [n for i in range(8) for n in d.hit(i * 0.15, velocity=0.5 + 0.5 * (i % 2))]
    assert not lint_audio(np.asarray(d.play(notes).take(seconds=1.5))).errors


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


@pytest.mark.parametrize("cls", DRUMS)
def test_a_drum_alone_at_full_velocity_stays_under_full_scale(cls):
    d = cls()
    # the peak is in the hit, not the tail, so half a second of each of 10 seeds
    peaks = [np.abs(np.asarray(d.play(d.hit(0.0, 1.0), seed=s).take(seconds=0.5))).max() for s in range(10)]
    assert max(peaks) < 1.0


def test_four_limbs_on_one_step_stay_under_full_scale():
    kit = Kit()
    grid = {kit.crash: "X", kit.kick: "X", kit.snare: "X", kit.hihat: "o"}
    peaks = [np.abs(np.asarray(kit.play(kit.pattern(grid, step=0.5), seed=s).take(seconds=0.5))).max() for s in range(10)]
    assert max(peaks) < 1.0


def test_a_stomp_lets_the_hall_ring_under_the_next():
    s = Stomp()
    p = s.play(s.hit(0.0) + s.hit(0.5))
    assert p.stops == p.ends


@pytest.mark.parametrize("cls", [Marimba, Timpani])
def test_a_tuned_bar_or_kettle_keeps_its_pitch_from_hit_to_hit(cls):
    from tests.helpers import peak_hz
    inst = cls()
    p = 220.0 if cls is Marimba else 110.0
    hz = [peak_hz(np.asarray(inst.play(inst.hit(0.0, pitch=p), seed=s).take(seconds=1.0))) for s in range(12)]
    cents = 1200 * np.log2(np.array(hz) / np.median(hz))
    assert np.ptp(cents) < 1.0


def test_one_kettle_rolls():
    t = Timpani(kettles=1)
    t.play(t.roll(0.0, 0.5, pitch=110.0)).take(seconds=1.0)


def test_no_kettles_is_refused():
    with pytest.raises(ValueError, match="kettle"):
        Timpani(kettles=0)
