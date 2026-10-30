import numpy as np
import pytest

from euterpe.instruments import Bowed, Bowing, CelloBody, Gut, Legato, Note, Staccato, StringSection, Violin, ViolinBody
from euterpe.lint import lint_audio, lint_notes
from euterpe.pitch import A4, B4, C2
from euterpe.sound import WhiteNoise
from euterpe.sound.core import RATE, render
from tests.helpers import band_db

PRESETS = [Violin, StringSection]


def _db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.square(x, dtype=np.float64))))


def _centroid(x):
    power = np.abs(np.fft.rfft(np.asarray(x, np.float64) * np.hanning(len(x)))) ** 2
    return float((power * np.fft.rfftfreq(len(x), 1 / RATE)).sum() / power.sum())


@pytest.mark.parametrize("cls", PRESETS)
def test_a_harder_bow_is_brighter(cls):
    held = slice(int(0.15 * RATE), int(0.35 * RATE))
    soft, hard = (render(cls().note(A4, 0.4, v), 0.35)[held] for v in (0.4, 1.0))
    assert _centroid(hard) > _centroid(soft)


def test_a_legato_pair_on_the_violin_is_one_voice():
    phrase = Violin().play([Note(0.0, A4, 0.3), Note(0.3, B4, 0.3, articulation=Legato())])
    assert len(phrase.voices) == 1


def test_a_section_of_one_player_without_detune_is_the_solo_model():
    section = StringSection(players=1, detune=0.0)
    solo = Bowed(bowing=section.bowing, string=section.string, body=section.body, vibrato=section.vibrato,
                 level=section.level, seed=section.seed)
    assert np.array_equal(render(section.note(A4, 0.1), 0.1), render(solo.note(A4, 0.1), 0.1))


def test_a_section_plays_its_low_notes_through_a_cello_body():
    assert isinstance(StringSection().soundboard(C2.freq), CelloBody)
    assert isinstance(StringSection().soundboard(A4.freq), ViolinBody)


def test_a_cello_body_rings_near_100_200_and_400_hz():
    cello, violin = (render(body(WhiteNoise(seed=1)), 1.0) for body in (CelloBody(), ViolinBody()))
    near = lambda x, hz: band_db(x, 0.9 * hz, 1.1 * hz)  # noqa: E731
    assert near(cello, 100) - near(violin, 100) > 6 and near(cello, 200) - near(violin, 200) > 4
    assert near(cello, 400) - near(cello, 300) > 3


def test_the_bow_lifts_at_the_end_and_the_string_rings_out():
    y = render(Violin().note(A4, 0.2, 1.0), 1.0)
    voice = Violin().note(A4, 0.2, 1.0)
    assert 0.2 + Bowing().release < voice.duration < 1.0
    assert np.abs(y[int(voice.duration * RATE):]).max() < 1e-3


def test_a_staccato_stroke_is_shorter_and_bites_harder():
    v = Violin()
    long = v.play([Note(0.0, A4, 0.4)])
    short = v.play([Note(0.0, A4, 0.4, articulation=Staccato())])
    assert short.duration < long.duration
    bite = slice(0, int(0.02 * RATE))
    assert _db(render(short, 0.02)[bite]) - _db(render(long, 0.02)[bite]) > 3


@pytest.mark.parametrize("cls", PRESETS)
def test_a_preset_plays_its_range_cleanly(cls):
    inst = cls()
    lo, hi = inst.comfortable
    mid = lo + (hi - lo) // 2
    phrase = inst.play([(0.0, lo, 0.3, 1.0), (0.3, mid, 0.3, 1.0), (0.6, hi, 0.3, 1.0), (0.6, mid + 4, 0.3, 1.0)])
    assert not lint_audio(np.asarray(phrase.take())).errors and not lint_notes(phrase).errors


@pytest.mark.parametrize("cls", PRESETS)
def test_a_preset_names_its_limit(cls):
    assert "Limit:" in cls.__doc__


def test_a_full_section_chord_stays_under_full_scale():
    chord = [(0.0, p, 0.4, 1.0) for p in (C2, C2 + 12, C2 + 19, C2 + 24, C2 + 28, C2 + 31, C2 + 36, C2 + 40)]
    assert np.abs(render(StringSection().play(chord), 0.4)).max() < 1.0


@pytest.mark.parametrize("cls", PRESETS)
def test_renders_do_not_depend_on_block_size(cls):
    phrase = cls(seed=3).play([(0.0, A4, 0.03, 0.9)])
    assert np.array_equal(render(phrase, 0.03, block=1), render(phrase, 0.03))


def test_the_violin_keeps_its_parts():
    v = Violin()
    assert isinstance(v.string, Gut) and isinstance(v.body, ViolinBody) and v.polyphony == 1
    assert (v.vibrato.rate, v.vibrato.cents) == (5.5, 18.0)
