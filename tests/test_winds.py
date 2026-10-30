import numpy as np
import pytest

from euterpe.instruments import Blown, BrassSection, Breath, Clarinet, Flute, Legato, Note, Staccato
from euterpe.lint import lint_audio, lint_notes
from euterpe.pitch import A2, A4, B4, C4
from euterpe.sound import Jet, Lips, Reed
from euterpe.sound.core import RATE, render
from tests.helpers import peak_hz

PRESETS = [Flute, Clarinet, BrassSection]


def _db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.square(x, dtype=np.float64))))


def _centroid(x):
    power = np.abs(np.fft.rfft(np.asarray(x, np.float64) * np.hanning(len(x)))) ** 2
    return float((power * np.fft.rfftfreq(len(x), 1 / RATE)).sum() / power.sum())


@pytest.mark.parametrize("cls", PRESETS)
def test_a_harder_breath_is_brighter(cls):
    held = slice(int(0.15 * RATE), int(0.35 * RATE))
    soft, hard = (render(cls().note(A4, 0.4, v), 0.35)[held] for v in (0.4, 1.0))
    assert _centroid(hard) > _centroid(soft)


def test_velocity_is_the_breath_not_a_gain():
    soft, hard = (Breath().draw(Note(0.0, A4, 0.1, v)) for v in (0.0, 1.0))
    assert 0.3 < soft < Breath().pressure < hard <= 1.0


@pytest.mark.parametrize("cls", [Flute, Clarinet])
def test_a_legato_pair_is_one_voice(cls):
    phrase = cls().play([Note(0.0, A4, 0.3), Note(0.3, B4, 0.3, articulation=Legato())])
    assert len(phrase.voices) == 1


def test_a_section_of_one_player_without_detune_is_the_solo_model():
    section = BrassSection(players=1, detune=0.0)
    solo = Blown(mouth=section.mouth, breath=section.breath, vibrato=section.vibrato, bell=section.bell,
                 level=section.level, seed=section.seed)
    assert np.array_equal(render(section.note(A4, 0.1), 0.1), render(solo.note(A4, 0.1), 0.1))


def test_a_flute_blown_hard_overblows_to_the_octave():
    held = slice(int(0.2 * RATE), int(0.4 * RATE))
    played = render(Flute().note(A4, 0.4, 1.0), 0.4)[held]
    overblown = render(Flute(breath=Breath(pressure=1.0, noise=0.06)).note(A4, 0.4, 1.0), 0.4)[held]
    assert abs(1200 * np.log2(peak_hz(played) / A4.freq)) < 30
    assert abs(1200 * np.log2(peak_hz(overblown) / (2 * A4.freq))) < 30


def test_the_breath_stops_at_the_end_and_the_tube_rings_out():
    voice = Clarinet().note(A4, 0.2, 1.0)
    y = render(voice, 0.6)
    assert 0.2 + Breath().release < voice.duration < 0.6
    assert np.abs(y[int(voice.duration * RATE):]).max() < 1e-3


def test_a_staccato_note_is_tongued_short():
    c = Clarinet()
    long = c.play([Note(0.0, A4, 0.4)])
    short = c.play([Note(0.0, A4, 0.4, articulation=Staccato())])
    assert short.duration < long.duration


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


def test_a_full_brass_chord_stays_under_full_scale():
    chord = [(0.0, p, 0.3, 1.0) for p in (A2, A2 + 7, A2 + 12, A2 + 16, A2 + 19, A2 + 24, A2 + 28, A2 + 31)]
    assert np.abs(render(BrassSection().play(chord), 0.3)).max() < 1.0


@pytest.mark.parametrize("cls", PRESETS)
def test_renders_do_not_depend_on_block_size(cls):
    phrase = cls(seed=3).play([(0.0, C4, 0.03, 0.9)])
    assert np.array_equal(render(phrase, 0.03, block=1), render(phrase, 0.03))


def test_the_presets_keep_their_parts():
    f, c, b = Flute(), Clarinet(), BrassSection()
    assert isinstance(f.mouth, Jet) and f.breath.noise == 0.06 and (f.vibrato.rate, f.vibrato.cents) == (5.0, 12.0)
    assert isinstance(c.mouth, Reed) and c.breath.noise == 0.02 and c.vibrato.cents == 0
    assert isinstance(b.mouth, Lips) and b.players == 3 and b.vibrato.cents == 6.0 and b.polyphony == 8
    assert f.polyphony == c.polyphony == 1
