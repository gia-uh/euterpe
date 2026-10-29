import numpy as np

from euterpe.instruments import Accent, AcidBass, Lead, Legato, Note, Pad, Supersaw, SynthPluck
from euterpe.pitch import A1, A2, A3, A4, D2
from euterpe.sound.core import RATE, render
from tests.helpers import band_db, peak_hz


def test_every_patch_renders_finite_and_below_full_scale():
    for patch, pitch in ((Lead(), A4), (Pad(), A3), (Supersaw(), A3), (SynthPluck(), A4), (AcidBass(), A1)):
        y = render(patch.play([(0.0, pitch, 0.6)]), 1.0)
        assert np.all(np.isfinite(y)) and 0.01 < np.abs(y).max() < 1.0


def test_a_pluck_darkens_fast():
    y = render(SynthPluck().play([(0.0, A3, 1.0)]), 0.6).astype(np.float64)
    early, late = y[: int(0.03 * RATE)], y[int(0.27 * RATE) : int(0.3 * RATE)]
    high = lambda x: np.sum(x**2) * 10 ** (band_db(x, 2_000, 20_000) / 10)
    assert 10 * np.log10(high(early) / high(late)) > 20


def test_the_supersaw_is_wide_and_one_saw_is_not():
    wide = render(Supersaw().play([(0.0, A3, 0.5)]), 0.5)
    one = render(Supersaw(voices=1).play([(0.0, A3, 0.5)]), 0.5)
    assert not np.allclose(wide[:, 0], wide[:, 1]) and np.allclose(one[:, 0], one[:, 1])


def test_an_acid_slide_glides_and_an_accent_is_louder_and_brighter():
    notes = [Note(0.0, A2, 0.25), Note(0.25, D2, 0.25, articulation=Legato())]
    assert len(AcidBass().play(notes).voices) == 1 and AcidBass.glide == 0.06  # one voice slides on
    plain = render(AcidBass().play([Note(0.0, A1, 0.2)]), 0.2).astype(np.float64)
    hit = render(AcidBass().play([Note(0.0, A1, 0.2, articulation=Accent())]), 0.2).astype(np.float64)
    assert np.sqrt(np.mean(hit**2)) > 1.2 * np.sqrt(np.mean(plain**2))
    assert band_db(hit, 1_000, 20_000) > band_db(plain, 1_000, 20_000)


def test_patches_do_not_depend_on_the_block_size():
    for patch in (Lead(), Pad(), AcidBass()):
        line = [(0.0, A2, 0.3), (0.2, A3, 0.3)]
        assert np.array_equal(render(patch.play(line), 0.8), render(patch.play(line), 0.8, block=100))
