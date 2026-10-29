import numpy as np
import pytest

from euterpe.sound.core import RATE, Const, Unit, render
from euterpe.sound.space import ConvolutionReverb, Delay, FDNReverb, Pan
from euterpe.sound.osc import Saw, Sine
from euterpe.sound.noise import WhiteNoise
from euterpe.sound.space import Chorus, Flanger, Phaser, Width
from tests.helpers import band_db, peak_hz


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
    assert np.array_equal(render(f(), 1.5), render(f(), 1.5, block=333))


def test_pan_is_constant_power():
    for pos in (-1.0, -0.3, 0.0, 0.6, 1.0):
        x = render(Pan(Sine(440.0), pos=pos), 0.1)
        power = (x ** 2).sum(axis=0).sum()
        assert abs(power - (render(Sine(440.0), 0.1) ** 2).sum()) / power < 0.01


# Beyond the plan's tests.


def test_delay_feedback_repeats_each_echo_quieter():
    x = render(Delay(Click(), time=0.1, feedback=0.5, mix=1.0), 0.35)
    echoes = [x[k * 4_800] for k in (1, 2, 3)]
    assert np.allclose(echoes, [1.0, 0.5, 0.25], atol=1e-6)


def test_delay_mix_keeps_the_dry_signal():
    x = render(Delay(Click(), time=0.1, feedback=0.0, mix=0.3), 0.2)
    assert np.isclose(x[0], 0.7) and np.isclose(x[4_800], 0.3)


def test_flanger_puts_peaks_at_multiples_of_its_delay():
    # depth 0: a fixed delay of 0.5 ms, so peaks at multiples of 2000 Hz and dips halfway
    x = render(Flanger(WhiteNoise(seed=2) * 0.3, depth=0.0, feedback=0.5, mix=0.5), 2.0)
    assert band_db(x, 1_900, 2_100) > band_db(x, 900, 1_100) + 10


def test_flanger_negative_feedback_moves_the_peaks_to_odd_multiples():
    # 0.5 ms with feedback -0.5: peaks at 1000, 3000 Hz, dips at 2000, 4000 Hz
    x = render(Flanger(WhiteNoise(seed=2) * 0.3, depth=0.0, feedback=-0.5, mix=0.5), 2.0)
    assert band_db(x, 900, 1_100) > band_db(x, 1_900, 2_100) + 10


def test_phaser_with_no_mix_is_its_source():
    assert np.array_equal(render(Phaser(Sine(440.0), mix=0.0), 0.1), render(Sine(440.0), 0.1))


def test_phaser_cuts_somewhere_and_keeps_level_elsewhere():
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
        lambda: Delay(Sine(220.0), time=Sine(0.5) * 0.01 + 0.2, feedback=0.6, mix=0.5, max_time=0.21),
        lambda: Chorus(Sine(220.0), rate=1.5),
        lambda: Flanger(Sine(220.0), rate=0.7, feedback=-0.7),
        lambda: Phaser(Sine(220.0), rate=2.0, stages=6),
        lambda: FDNReverb(Sine(220.0) * Sine(1.0), decay=1.0, damping=0.6),
        lambda: ConvolutionReverb(Sine(220.0) * Sine(1.0), decay=0.5, mix=Sine(0.5) * 0.5 + 0.5),
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


def test_chorus_without_depth_is_a_20_ms_delay():
    a = render(Chorus(Sine(220.0), depth=0.0, mix=0.5), 0.2)
    b = render(Delay(Sine(220.0), time=0.02, feedback=0.0, mix=0.5), 0.2)
    assert np.allclose(a, b, atol=1e-6)


def test_chorus_shifts_the_pitch_by_the_rate_of_change_of_its_delay():
    # delay 0.02 + 0.005 sin(2 pi t): it shrinks fastest at t = 0.5 s (pitch up) and grows
    # fastest at t = 1 s (pitch down), by 0.005 * 2 pi = 3.14 % of 1000 Hz
    x = render(Chorus(Sine(1000.0), rate=1.0, depth=0.005, mix=1.0), 1.1)
    up, down = peak_hz(x[21_600:26_400]), peak_hz(x[45_600:50_400])
    assert abs(up - 1031.4) < 5 and abs(down - 968.6) < 5


def test_flanger_sweep_moves_its_comb():
    # rate 0.25: the delay is 2.5 ms at t = 1 s (a peak at 1200 Hz = 3 / 2.5 ms) and 0.5 ms at
    # t = 3 s (1200 Hz is near the dip at 1000 Hz)
    x = render(Flanger(WhiteNoise(seed=6) * 0.3, rate=0.25, depth=0.002, feedback=0.5, mix=0.5), 3.2)
    long, short = x[43_200:52_800], x[139_200:148_800]
    assert band_db(long, 1_150, 1_250) > band_db(short, 1_150, 1_250) + 10


def _notches(stages):
    """Count the bands below 24 kHz where a click through the phaser is 20 dB down. An odd
    count of stages also cancels at 24 kHz itself; that band reaches the top and is not counted."""
    x = render(Phaser(Click(), rate=0.01, stages=stages, mix=0.5), 0.5)
    low = np.abs(np.fft.rfft(x)) < 0.1
    return int(np.sum(low[1:] & ~low[:-1])) - int(low[-1])


@pytest.mark.parametrize("stages, notches", [(1, 0), (2, 1), (4, 2), (8, 4), (7, 3)])
def test_phaser_has_half_its_stages_as_notches_below_nyquist(stages, notches):
    assert _notches(stages) == notches


def test_phaser_sweep_moves_its_notch():
    # rate 0.5, 2 stages: one notch at the turning frequency, 2000 Hz at t = 0.5 s, 200 Hz at 1.5 s
    x = render(Phaser(WhiteNoise(seed=8) * 0.3, rate=0.5, stages=2, mix=0.5), 1.6)
    high, low = x[21_600:26_400], x[69_600:74_400]
    assert band_db(high, 1_800, 2_200) < band_db(low, 1_800, 2_200) - 10


def test_fdn_damping_shortens_the_high_frequencies():
    def slopes(damping):
        x = render(FDNReverb(Click(), decay=1.5, damping=damping, mix=1.0), 1.0).mean(axis=1)
        frames = x[: 48_000].reshape(10, 4_800)
        power = np.abs(np.fft.rfft(frames, axis=1)) ** 2   # bins 10 Hz apart
        high = 10 * np.log10(power[:, 400:].sum(axis=1))    # above 4 kHz
        low = 10 * np.log10(power[:, 5:50].sum(axis=1))     # 50 to 500 Hz
        return high[2] - high[8], low[2] - low[8]           # dB lost from 0.2 s to 0.8 s

    high, low = slopes(0.6)
    assert high > 1.5 * low
    high, low = slopes(0.0)
    assert abs(high - low) < 0.25 * low


def test_width_two_doubles_the_side_and_keeps_the_mid():
    src = lambda: Pan(Sine(440.0), pos=-0.8) + Pan(Sine(660.0), pos=0.8)
    x, y = render(Width(src(), width=2.0), 0.1), render(src(), 0.1)
    assert np.allclose(x[:, 0] - x[:, 1], 2 * (y[:, 0] - y[:, 1]), atol=1e-6)
    assert np.allclose(x[:, 0] + x[:, 1], y[:, 0] + y[:, 1], atol=1e-6)


@pytest.mark.parametrize(
    "make",
    [
        lambda rate: Chorus(Sine(220.0), rate=rate),
        lambda rate: Flanger(Sine(220.0), rate=rate),
        lambda rate: Phaser(Sine(220.0), rate=rate),
    ],
)
def test_a_fast_modulating_rate_stays_finite(make):
    x = render(make(Sine(1.0) * 500.0), 0.3)
    assert np.all(np.isfinite(x)) and np.abs(x).max() < 2


def test_a_moving_delay_time_needs_max_time():
    with pytest.raises(TypeError, match="max_time"):
        Delay(Sine(220.0), time=Sine(0.5) * 0.01 + 0.2)


def test_a_delay_time_beyond_max_time_is_clipped_to_it():
    a = render(Delay(Click(), time=Const(0.3), feedback=0.0, mix=1.0, max_time=0.1), 0.3)
    b = render(Delay(Click(), time=0.1, feedback=0.0, mix=1.0), 0.3)
    assert np.array_equal(a, b)


@pytest.mark.parametrize("decay", [0.5, 2.0, 20.0])
def test_fdn_response_has_energy_one_per_side(decay):
    x = render(FDNReverb(Click(), decay=decay, mix=1.0), decay * 1.1)
    energy_db = 10 * np.log10((x.astype(np.float64) ** 2).sum(axis=0))
    assert np.all(np.abs(energy_db) < 1.5), energy_db


@pytest.mark.parametrize("decay", [0.5, 8.0])
def test_fdn_without_damping_decays_in_its_setting(decay):
    x = render(FDNReverb(Click(), decay=decay, damping=0.0, mix=1.0), decay * 1.3)
    assert abs(rt60(x.mean(axis=1)) - decay) / decay < 0.1


def _swirl_hz(speed: float) -> float:
    """The rate at which a Leslie's level swings, from the spectrum of its left channel's envelope."""
    from euterpe.sound.space import Leslie

    y = render(Leslie(Sine(2_000.0) * 0.5, speed=speed), 6.0)[RATE:, 0].astype(np.float64)
    env = np.abs(y).reshape(-1, 480).max(axis=1)  # 100 values a second
    spec = np.abs(np.fft.rfft((env - env.mean()) * np.hanning(len(env))))
    return float(np.fft.rfftfreq(len(env), 0.01)[np.argmax(spec[1:]) + 1])


def test_leslie_swirls_at_its_rotor_rate():
    assert abs(_swirl_hz(1.0) - 6.7) < 0.4
    assert abs(_swirl_hz(0.0) - 0.8) < 0.3


def test_leslie_is_stereo_and_its_horn_spins_up_within_a_second_and_a_half():
    from euterpe.sound.env import Segments
    from euterpe.sound.space import Leslie

    les = Leslie(Sine(2_000.0) * 0.5, speed=Segments([(0.0, 0.0), (0.5, 0.0), (0.501, 1.0)]))
    y = render(les, 2.0)
    assert not np.allclose(y[:, 0], y[:, 1])
    assert les._rate[0] > 0.8 + 0.9 * (6.7 - 0.8)


def test_leslie_does_not_depend_on_the_block_size():
    from euterpe.sound.space import Leslie

    f = lambda: Leslie(Saw(220.0) * 0.3, speed=Sine(0.5) * 0.5 + 0.5)
    assert np.array_equal(render(f(), 0.5), render(f(), 0.5, block=100))


def test_leslie_does_not_depend_on_the_block_size_over_seconds():
    from euterpe.sound.space import Leslie

    f = lambda: Leslie(Saw(220.0) * 0.3, speed=Sine(0.3) * 0.5 + 0.5)
    ref = render(f(), 3.0)
    for block in (1, 7, 4096):
        assert np.array_equal(render(f(), 3.0, block=block), ref)


def test_leslie_starts_at_the_speed_it_is_given():
    from euterpe.sound.env import Segments
    from euterpe.sound.space import Leslie

    les = Leslie(Sine(2_000.0) * 0.5, speed=Segments([(0.0, 1.0), (5.0, 1.0)]))
    render(les, 0.01)
    assert les._rate[0] > 6.5
