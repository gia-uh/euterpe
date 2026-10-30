import numpy as np
import pytest
from euterpe.instruments import Accent, Instrument, Note, Staccato, play
from euterpe.pitch import A4, C4
from tests.helpers import Theremin
from euterpe.instruments import PluckedString
from euterpe.lint import lint_audio
from euterpe.pitch import B2, B3, E2, E3, E4, Gs3
from euterpe.sound.core import RATE


def test_tuples_and_notes_are_the_same_note():
    a = Theremin().play([(0.0, A4, 0.5, 0.6)]).take(0.6)
    b = Theremin().play([Note(0.0, A4, 0.5, 0.6)]).take(0.6)
    assert np.array_equal(np.asarray(a), np.asarray(b))


def test_hz_and_pitch_mix():
    notes = Theremin().play([(0.0, 440.0, 0.2), (0.3, C4, 0.2)]).notes
    assert notes[0].freq == 440.0 and notes[1].freq == pytest.approx(261.6256, abs=1e-3)


@pytest.mark.parametrize("bad", [(0.0, A4, 0.0), (0.0, A4, -1.0), (0.0, A4, 1.0, 1.5), (-0.1, A4, 1.0)])
def test_bad_notes_are_refused(bad):
    with pytest.raises(ValueError, match="note"):
        Theremin().play([bad])


def test_articulations_act_on_the_note():
    staccato, accent = Theremin().play([Note(0.0, A4, 1.0, 0.8, Staccato()), Note(2.0, A4, 1.0, 0.9, Accent())]).notes
    assert staccato.duration == 0.5 and accent.velocity == 1.0


def test_protocol_without_inheriting():
    class Beep:
        polyphony = 1
        def voice(self, note):
            return Theremin().voice(note)
    assert play(Beep(), [(0.0, A4, 0.2)]).take(0.3).seconds == pytest.approx(0.3)


def test_same_seed_same_samples_other_seed_other_rng():
    a, b = (Theremin().play([(0.0, A4, 0.2)], seed=s).notes[0].rng.random() for s in (1, 1))
    c = Theremin().play([(0.0, A4, 0.2)], seed=2).notes[0].rng.random()
    assert a == b != c


def test_note_is_one_note():
    assert len(Theremin().note(A4, 0.5).notes) == 1


def test_a_full_strum_stays_under_full_scale():
    chord = [E2, B2, E3, Gs3, B3, E4]
    clip = PluckedString().play([(0.015 * i, p, 1.6, 1.0) for i, p in enumerate(chord)]).take()
    assert np.abs(np.asarray(clip)).max() < 1.0 and not lint_audio(np.asarray(clip)).errors


def test_high_partials_die_first():
    x = np.asarray(PluckedString(position=0.0, brightness=1.0).note(A4, 2.0).take(2.0))
    def share_above(seg, hz):
        spec = np.abs(np.fft.rfft(seg)); f = np.fft.rfftfreq(len(seg), 1 / RATE)
        return spec[f > hz].sum() / spec.sum()
    early, late = x[: RATE // 10], x[RATE: RATE + RATE // 10]
    assert share_above(late, 2000) < share_above(early, 2000)


def test_the_finger_mutes_the_string():
    x = np.asarray(PluckedString(damping=0.999).note(A4, 0.5).take(1.0))
    assert np.abs(x[int(0.7 * RATE):]).max() < 1e-3

@pytest.mark.parametrize("bad", [Note(0.0, A4, 0.5, articulation=Staccato(0.0)), Note(0.0, A4, 0.5, 0.5, Accent(-1.0)),
                                 (0.0, A4, float("nan")), (float("inf"), A4, 1.0), (0.0, A4, 1.0, float("nan"))])
def test_bad_notes_after_articulation_or_not_finite_are_refused(bad):
    with pytest.raises(ValueError, match="note"):
        Theremin().play([bad])


def test_play_leaves_the_callers_notes_alone():
    n = Note(0.0, A4, 0.5)
    rng = n.rng
    a, b = Theremin().play([n], seed=1), Theremin().play([n], seed=2)
    assert n.rng is rng and a.notes[0].rng is not b.notes[0].rng


def test_play_warns_about_an_unplayable_note():
    from euterpe.pitch import B7
    with pytest.warns(UserWarning, match="B7"):
        Theremin().play([(0.0, B7, 0.5)])


def _vibrato_note(seed=0):
    note = Note(0.0, A4, 1.0)
    note.rng = np.random.default_rng(seed)
    return note


def test_vibrato_moves_the_pitch_by_its_cents_after_its_delay_and_not_before():
    from euterpe.instruments import Vibrato
    from euterpe.sound import render

    f = render(Vibrato(cents=18, delay=0.25, rise=0.3, variation=0.0).of(440.0, _vibrato_note()), 1.0)
    assert np.all(f[: round(0.25 * RATE)] == np.float32(440.0))
    swing = 1200 * np.log2(f[round(0.55 * RATE):] / 440.0)
    assert swing.max() == pytest.approx(18, abs=0.1) and swing.min() == pytest.approx(-18, abs=0.1)


def test_vibrato_varies_per_note_and_follows_a_moving_freq():
    from euterpe.instruments import Vibrato
    from euterpe.sound import Segments, render

    v = Vibrato(delay=0.0, rise=0.0)
    a, b = (render(v.of(440.0, _vibrato_note(s)), 0.5) for s in (1, 2))
    assert not np.array_equal(a, b)
    assert np.abs(1200 * np.log2(a / 440.0)).max() <= 18 * 1.1 + 1e-3
    slur = render(Vibrato(cents=12).of(Segments([(0.0, 440.0), (0.1, 440.0), (0.1, 493.88)]), _vibrato_note()), 0.2)
    assert slur[100] == np.float32(440.0) and slur[-1] == np.float32(493.88)


def test_no_vibrato_is_the_frequency_itself():
    from euterpe.instruments import Vibrato

    assert Vibrato(cents=0).of(440.0, _vibrato_note()) == 440.0
