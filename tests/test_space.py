import numpy as np
import pytest

from euterpe.sound.core import RATE, Unit, render
from euterpe.sound.space import ConvolutionReverb, Delay, FDNReverb, Pan
from euterpe.sound.osc import Sine


class Click(Unit):
    channels = 1
    def __init__(self): self.reset()
    def reset(self): self.i = 0
    def block(self, n):
        out = np.zeros(n, np.float32)
        if self.i == 0: out[0] = 1.0
        self.i += n
        return out


def test_delay_echo_lands_on_time():
    x = render(Delay(Click(), time=0.1, feedback=0.0, mix=1.0), 0.3)
    assert abs(int(np.argmax(np.abs(x[100:]))) + 100 - int(0.1 * RATE)) <= 1


def rt60(x):
    e = np.cumsum((x ** 2)[::-1])[::-1]
    db = 10 * np.log10(e / e[0] + 1e-12)
    return np.argmax(db < -60) / RATE


def test_fdn_decay_matches_its_setting():
    x = render(FDNReverb(Click(), decay=1.5, mix=1.0), 4.0)
    assert abs(rt60(x.mean(axis=1)) - 1.5) / 1.5 < 0.2


def test_convolution_reverb_block_size_invariant():
    f = lambda: ConvolutionReverb(Click(), decay=1.0, mix=1.0, seed=3)
    assert np.allclose(render(f(), 1.5), render(f(), 1.5, block=333), atol=1e-6)


def test_pan_is_constant_power():
    for pos in (-1.0, -0.3, 0.0, 0.6, 1.0):
        x = render(Pan(Sine(440.0), pos=pos), 0.1)
        power = (x ** 2).sum(axis=0).sum()
        assert abs(power - (render(Sine(440.0), 0.1) ** 2).sum()) / power < 0.01


# Beyond the plan's tests.

from euterpe.sound.space import Chorus, Flanger, Phaser, Width  # noqa: E402
from tests.helpers import band_db  # noqa: E402


def test_delay_feedback_repeats_each_echo_quieter():
    x = render(Delay(Click(), time=0.1, feedback=0.5, mix=1.0), 0.35)
    echoes = [x[k * 4_800] for k in (1, 2, 3)]
    assert np.allclose(echoes, [1.0, 0.5, 0.25], atol=1e-6)


def test_delay_mix_keeps_the_dry_signal():
    x = render(Delay(Click(), time=0.1, feedback=0.0, mix=0.3), 0.2)
    assert np.isclose(x[0], 0.7) and np.isclose(x[4_800], 0.3)


def test_flanger_puts_peaks_at_multiples_of_its_delay():
    from euterpe.sound.noise import WhiteNoise

    # depth 0: a fixed delay of 0.5 ms, so peaks at multiples of 2000 Hz and dips halfway
    x = render(Flanger(WhiteNoise(seed=2) * 0.3, depth=0.0, feedback=0.5, mix=0.5), 2.0)
    assert band_db(x, 1_900, 2_100) > band_db(x, 900, 1_100) + 10


def test_phaser_with_no_mix_is_its_source():
    assert np.array_equal(render(Phaser(Sine(440.0), mix=0.0), 0.1), render(Sine(440.0), 0.1))


def test_phaser_cuts_somewhere_and_keeps_level_elsewhere():
    from euterpe.sound.noise import WhiteNoise

    # rate at its minimum: the notches barely move during the render
    x = render(Phaser(WhiteNoise(seed=4) * 0.3, rate=0.01, stages=4, mix=0.5), 2.0)
    dry = render(WhiteNoise(seed=4) * 0.3, 2.0)
    bands = [(lo, lo * 1.25) for lo in np.geomspace(100, 15_000, 20)]
    drops = [band_db(x, lo, hi) - band_db(dry, lo, hi) for lo, hi in bands]
    assert min(drops) < -6 and max(drops) > -1


def test_width_zero_is_mono_and_one_changes_nothing():
    left_right = lambda: Pan(Sine(440.0), pos=-0.8) + Pan(Sine(660.0), pos=0.8)
    narrow = render(Width(left_right(), width=0.0), 0.1)
    assert np.array_equal(narrow[:, 0], narrow[:, 1])
    assert np.allclose(render(Width(left_right(), width=1.0), 0.1), render(left_right(), 0.1), atol=1e-7)


def test_reverbs_turn_mono_into_stereo():
    for unit in (FDNReverb(Click(), mix=1.0), ConvolutionReverb(Click(), mix=1.0)):
        x = render(unit, 0.5)
        assert x.shape == (24_000, 2) and not np.allclose(x[:, 0], x[:, 1])


def test_convolution_reverb_decays_by_its_setting():
    x = render(ConvolutionReverb(Click(), decay=1.0, mix=1.0), 2.0)
    assert abs(rt60(x.mean(axis=1)) - 1.0) < 0.15


@pytest.mark.parametrize(
    "make",
    [
        lambda: Delay(Sine(220.0), time=Sine(0.5) * 0.01 + 0.2, feedback=0.6, mix=0.5),
        lambda: Chorus(Sine(220.0), rate=1.5),
        lambda: Flanger(Sine(220.0), rate=0.7, feedback=-0.7),
        lambda: Phaser(Sine(220.0), rate=2.0, stages=6),
        lambda: FDNReverb(Sine(220.0) * Sine(1.0), decay=1.0, damping=0.6),
        lambda: Pan(Sine(220.0), pos=Sine(1.0)),
        lambda: Width(Pan(Sine(220.0), pos=0.5), width=Sine(1.0) + 1),
    ],
)
def test_block_size_does_not_change_the_samples(make):
    assert np.array_equal(render(make(), 1.0), render(make(), 1.0, block=37))


def test_phaser_stages_must_be_a_number():
    with pytest.raises(TypeError):
        Phaser(Sine(220.0), stages=Sine(1.0))


def test_convolution_reverb_of_a_click_is_its_impulse_response():
    unit = ConvolutionReverb(Click(), decay=0.3, mix=1.0, seed=5)
    x = render(unit, 0.5, block=100)
    t = np.arange(round(0.45 * RATE)) / RATE
    h = np.random.Generator(np.random.PCG64(5)).standard_normal((len(t), 2)) * np.exp(-3 * np.log(10) * t / 0.3)[:, None]
    h /= np.sqrt((h ** 2).sum(axis=0))
    assert np.allclose(x[: len(h)], h, atol=1e-6) and np.abs(x[len(h):]).max() < 1e-6
