import numpy as np
import pytest

from euterpe.instruments import Note
from euterpe.pitch import A2, A4, E1
from euterpe.sound.core import RATE, render


def share_above(x, hz):
    spec = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / RATE)
    return spec[f > hz].sum() / spec.sum()


def _harmonic_db(x, f0, k):
    x = x.astype(np.float64)
    mag = np.abs(np.fft.rfft(x * np.hanning(len(x)))); f = np.fft.rfftfreq(len(x), 1 / RATE)
    near = np.abs(f - k * f0) < f0 / 4
    return 20 * np.log10(mag[near].max())


def test_neck_is_darker_than_bridge():
    from euterpe.instruments import Bridge, ElectricGuitar, Neck

    neck = render(ElectricGuitar(pickup=Neck()).play(ElectricGuitar().pick(5, 0, 0.0, 1.0)), 1.0)
    bridge = render(ElectricGuitar(pickup=Bridge()).play(ElectricGuitar().pick(5, 0, 0.0, 1.0)), 1.0)
    assert share_above(neck, 2000) < share_above(bridge, 2000)


def test_a_quarter_pickup_removes_the_4th_and_8th():
    from euterpe.instruments import ElectricGuitar, Pickup, Plectrum

    g = ElectricGuitar(pickup=Pickup(position=0.25, resonance=20_000.0, q=0.707),
                       exciter=Plectrum(position=0.13, variation=0.0))
    x = render(g.play(g.pick(5, 0, 0.0, 1.0)), 1.0)
    f0 = A2.freq
    for k in (4, 8):
        neighbours = (_harmonic_db(x, f0, k - 1) + _harmonic_db(x, f0, k + 1)) / 2
        assert _harmonic_db(x, f0, k) <= neighbours - 20


def test_the_fraction_grows_with_the_fret_and_stops_at_half():
    from euterpe.instruments import ElectricGuitar, Neck

    g = ElectricGuitar(pickup=Neck())
    assert g.fraction(5, A2.freq) == pytest.approx(0.25)
    assert g.fraction(5, 2 * A2.freq) == pytest.approx(0.5)
    assert g.fraction(1, 2000.0) == 0.5


def test_a_plain_pitch_gets_a_string_and_a_fret():
    from euterpe.instruments import ElectricGuitar

    x = render(ElectricGuitar().play([Note(0.0, A4, 0.5)]), 0.5)
    assert np.all(np.isfinite(x)) and np.abs(x).max() > 0.01


def test_palm_mute_dies_fast():
    from euterpe.instruments import ElectricBass, ElectricGuitar, PalmMute

    g = ElectricGuitar()
    open_ = render(g.play([Note(0.0, A2, 1.0, resource=5)]), 1.0)
    muted = render(g.play([Note(0.0, A2, 1.0, resource=5, articulation=PalmMute())]), 1.0)

    def level(x):
        seg = x[int(0.3 * RATE):int(0.35 * RATE)].astype(np.float64)
        return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)

    assert level(muted) <= level(open_) - 20

    bass = ElectricBass()
    open_ = render(bass.play([Note(0.0, E1, 1.0, resource=4)]), 1.0)
    muted = render(bass.play([Note(0.0, E1, 1.0, resource=4, articulation=PalmMute())]), 1.0)
    assert level(muted) <= level(open_) - 20


def test_electric_instruments_have_no_body():
    from euterpe.instruments import ElectricBass, ElectricGuitar

    assert ElectricGuitar().body is None and ElectricBass().body is None
    assert ElectricBass().tuning[0] == E1


def test_the_same_seed_gives_the_same_samples():
    from euterpe.instruments import ElectricBass, ElectricGuitar

    for make in (ElectricGuitar, ElectricBass):
        a = render(make(seed=4).play([Note(0.0, A2, 0.5)]), 0.5)
        b = render(make(seed=4).play([Note(0.0, A2, 0.5)]), 0.5)
        assert np.array_equal(a, b)


def _level(x, t0, t1):
    seg = x[int(t0 * RATE):int(t1 * RATE)].astype(np.float64)
    return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)


def test_feedback_holds():
    from euterpe.instruments import ElectricGuitar

    g = ElectricGuitar()
    x = render(g.play(g.feedback(3, 4, 0.0, 4.0)), 4.0)
    assert abs(_level(x, 2.9, 3.1) - _level(x, 0.4, 0.6)) <= 6


def test_feedback_blooms_into_its_harmonic():
    from euterpe.instruments import ElectricGuitar

    g = ElectricGuitar()
    note = g.feedback(3, 4, 0.0, 4.0)
    f0 = note[0].freq
    x = render(g.play(note), 4.0)[int(3.5 * RATE):int(4.0 * RATE)]
    partials = {k: _harmonic_db(x, f0, k) for k in range(1, 7)}
    assert max(partials, key=partials.get) == 2


def test_feedback_ends_with_its_note():
    from euterpe.instruments import ElectricGuitar

    g = ElectricGuitar()
    assert g.play(g.feedback(3, 4, 0.0, 2.0)).duration < 2.5


def test_a_later_note_takes_the_string():
    from euterpe.instruments import ElectricGuitar

    g = ElectricGuitar()
    f0 = g.feedback(3, 4, 0.0, 4.0)[0].freq
    alone = render(g.play(g.feedback(3, 4, 0.0, 4.0)), 4.0)[int(3.0 * RATE):int(3.5 * RATE)]
    taken = render(g.play(g.feedback(3, 4, 0.0, 4.0) + g.pick(3, 0, 1.0, 0.2)), 4.0)[int(3.0 * RATE):int(3.5 * RATE)]
    assert _harmonic_db(taken, f0, 2) < _harmonic_db(alone, f0, 2) - 20


def test_a_feedback_note_keeps_its_strings_detuning():
    from euterpe.instruments import ElectricGuitar

    seed = next(k for k in range(50) if abs(ElectricGuitar(seed=k).traits(2)[0]) > 2.0)
    g = ElectricGuitar(seed=seed, pickup=None)
    note = g.feedback(2, 0, 0.0, 6.0)
    f0 = note[0].freq
    x = render(g.play(note), 6.0).astype(np.float64)
    mag = np.abs(np.fft.rfft(x * np.hanning(len(x)), 4 * len(x)))
    f = np.fft.rfftfreq(4 * len(x), 1 / RATE)
    near = np.abs(f - f0) < 3.0
    heard = f[near][np.argmax(mag[near])]
    assert heard == pytest.approx(f0 * 2 ** (g.traits(2)[0] / 1200), abs=0.1)


def test_a_feedback_note_on_the_bass_is_gated_once():
    from euterpe.instruments import ElectricBass

    b = ElectricBass()
    x = render(b.play(b.feedback(4, 0, 0.0, 1.0)), 1.0)
    held = x[int(0.85 * RATE):int(0.95 * RATE)].astype(np.float64)
    start = x[int(0.10 * RATE):int(0.20 * RATE)].astype(np.float64)
    assert np.sqrt(np.mean(held ** 2)) > 0.3 * np.sqrt(np.mean(start ** 2))


def test_the_pickup_takes_stereo():
    from euterpe.instruments import Pickup
    from euterpe.sound import Pan
    from euterpe.sound.osc import Saw

    assert render(Pickup()(Pan(Saw(110.0) * 0.3, 0.5), 110.0, 0.2), 0.1).shape[1] == 2
