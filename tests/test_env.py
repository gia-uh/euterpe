import numpy as np

from euterpe.sound.core import RATE, render
from euterpe.sound.env import ADSR, EnvelopeFollower, Segments
from euterpe.sound.osc import Sine


def at(x, t):
    return float(x[int(t * RATE)])


def test_adsr_shape():
    x = render(ADSR(attack=0.1, decay=0.1, sustain=0.5, release=0.2, gate=0.5), 1.0)
    assert abs(at(x, 0.05) - 0.5) < 0.01          # halfway up the attack
    assert abs(at(x, 0.1) - 1.0) < 0.01
    assert abs(at(x, 0.3) - 0.5) < 0.01           # sustaining
    assert abs(at(x, 0.6) - 0.25) < 0.01          # halfway down the release
    assert at(x, 0.8) == 0.0


def test_release_starts_from_the_current_level_when_the_gate_ends_early():
    x = render(ADSR(attack=0.2, decay=0.1, sustain=0.5, release=0.1, gate=0.1), 0.3)
    assert abs(at(x, 0.1) - 0.5) < 0.02 and at(x, 0.25) == 0.0


def test_release_starts_from_the_level_reached_not_from_the_sustain():
    x = render(ADSR(attack=0.2, decay=0.1, sustain=0.8, release=0.1, gate=0.05), 0.2)
    assert abs(at(x, 0.05) - 0.25) < 0.01 and abs(at(x, 0.1) - 0.125) < 0.01


def test_segments_interpolate_and_hold():
    x = render(Segments([(0.0, 0.0), (0.5, 1.0)]), 1.0)
    assert abs(at(x, 0.25) - 0.5) < 0.01 and at(x, 0.9) == 1.0


def test_a_follower_tracks_a_sine_amplitude():
    assert abs(render(EnvelopeFollower(Sine(440.0) * 0.5), 1.0)[-1] - 0.5) < 0.05


def test_a_follower_falls_after_its_source_stops():
    x = render(EnvelopeFollower(Sine(440.0) * ADSR(attack=0.0, decay=0.0, sustain=0.5, release=0.0, gate=0.5)), 0.7)
    assert at(x, 0.6) < 0.5 * np.exp(-1) + 0.05


def test_envelopes_render_the_same_in_any_block_size():
    for make in (
        lambda: ADSR(attack=0.01, decay=0.05, sustain=0.3, release=0.1, gate=0.2, curve=0.5),
        lambda: Segments([(0.0, 0.0), (0.1, 1.0), (0.3, 0.2)]),
        lambda: EnvelopeFollower(Sine(220.0) * ADSR(gate=0.1)),
    ):
        assert np.array_equal(render(make(), 0.4, block=1024), render(make(), 0.4, block=37))


def test_a_positive_curve_rises_faster_and_falls_faster_than_a_line():
    line = render(ADSR(attack=0.1, decay=0.1, sustain=0.0, release=0.1, gate=1.0), 0.3)
    bowed = render(ADSR(attack=0.1, decay=0.1, sustain=0.0, release=0.1, gate=1.0, curve=0.8), 0.3)
    assert at(bowed, 0.05) > at(line, 0.05) + 0.2     # attack: up sooner
    assert at(bowed, 0.15) < at(line, 0.15) - 0.2     # decay: down sooner
    assert at(bowed, 0.1) > 0.99 and at(bowed, 0.25) == 0.0


def test_a_positive_curve_releases_faster_than_a_line():
    line = render(ADSR(attack=0.0, decay=0.0, sustain=1.0, release=0.1, gate=0.1), 0.3)
    bowed = render(ADSR(attack=0.0, decay=0.0, sustain=1.0, release=0.1, gate=0.1, curve=0.8), 0.3)
    assert at(bowed, 0.15) < at(line, 0.15) - 0.2


def test_two_segment_points_at_one_time_make_a_jump():
    x = render(Segments([(0.25, 0.0), (0.25, 1.0), (0.75, 1.0), (0.75, 0.0)]), 1.0)
    i, j = int(0.25 * RATE), int(0.75 * RATE)
    assert x[i - 1] == 0.0 and x[i] == 1.0 and x[j - 1] == 1.0 and x[j] == 0.0


def test_a_zero_attack_starts_at_full_level():
    assert render(ADSR(attack=0.0, decay=0.1, sustain=0.5), 0.01)[0] == 1.0


def test_segments_refuse_times_that_go_backwards():
    import pytest

    with pytest.raises(ValueError, match="Segments"):
        Segments([(0.5, 1.0), (0.2, 0.0)])
    with pytest.raises(ValueError, match="Segments"):
        Segments([])
