import math

import numpy as np
import pytest

from euterpe.instruments import (
    SAW, TRIANGLE, ClassicChip, Fade, Kit, Legato, ModernChip, Note, NoiseChannel, NoiseDrum, PulseChannel,
    WaveChannel,
)
from euterpe.lint import lint_audio
from euterpe.pitch import A4, B4, C4, C5, C8, E4, G4
from euterpe.sound.core import RATE, render
from tests.helpers import band_db, peak_hz


def _cents(f, g):
    return 1200 * math.log2(f / g)


def _harmonic_db(x, f, k):
    return band_db(x, k * f * 0.97, k * f * 1.03)


PHRASE = [(0.0, C4, 0.1), (0.1, E4, 0.1), (0.2, G4, 0.1), (0.3, C5, 0.2)]


def test_a_duty_outside_the_four_raises_with_steps():
    with pytest.raises(ValueError, match="0.3"):
        PulseChannel(duty=0.3)
    PulseChannel(duty=0.3, steps=False)
    for duty in (0.125, 0.25, 0.5, 0.75):
        PulseChannel(duty=duty)


def test_duty_half_has_no_even_harmonic():
    f = 750.0  # a whole number of cycles in the window, and exactly a divider's pitch
    x = render(PulseChannel(quantize=False).note(f, 0.3, 1.0), 0.25)[RATE // 20:]
    odd = _harmonic_db(x, f, 1)
    for k in (2, 4, 6, 8):
        assert _harmonic_db(x, f, k) < odd - 40


def test_duty_quarter_has_the_even_harmonics():
    f = 750.0
    x = render(PulseChannel(duty=0.25, quantize=False).note(f, 0.3, 1.0), 0.25)[RATE // 20:]
    assert _harmonic_db(x, f, 2) > _harmonic_db(x, f, 1) - 10
    assert _harmonic_db(x, f, 4) < _harmonic_db(x, f, 3) - 30  # every 4th is missing


def test_quantize_puts_high_notes_off_by_the_divider():
    pulse = PulseChannel()
    c8 = pulse.quantized(C8.freq)
    n = 2048 - 131_072 / c8
    assert n == round(n) and 0 <= n <= 2047
    assert abs(_cents(c8, C8.freq)) > 10  # 131 072 / 31 Hz: 17 cents sharp
    assert abs(_cents(pulse.quantized(A4.freq), A4.freq)) < 1
    wave = 2048 - 65_536 / WaveChannel().quantized(C8.freq)
    assert wave == pytest.approx(round(wave)) and 0 <= wave <= 2047


def test_a_quantized_note_sounds_at_the_divider_pitch():
    x = render(PulseChannel().note(C8, 0.2, 1.0), 0.2)[RATE // 20:]
    assert abs(_cents(peak_hz(x), 131_072 / 31)) < 5
    exact = render(PulseChannel(quantize=False).note(C8, 0.2, 1.0), 0.2)[RATE // 20:]
    assert abs(_cents(peak_hz(exact), C8.freq)) < 5


def test_fade_falls_in_sixteen_steps():
    x = render(Fade(15, pace=1).of(), 0.3)
    levels = np.unique(np.round(x * 15, 4))
    assert len(levels) == 16 and levels.min() == 0 and levels.max() == 15
    first_zero = int(np.argmax(x == 0))
    assert abs(first_zero - 15 / 64 * RATE) <= 1
    assert Fade(15, pace=1).of().duration == pytest.approx(15 / 64)


def test_fade_up_and_held():
    up = render(Fade(0, pace=2, up=True).of(), 0.6)
    assert up[0] == 0 and up[-1] == pytest.approx(1.0)
    assert np.all(np.diff(up) >= 0)
    held = render(Fade(9).of(), 0.05)
    assert np.allclose(held, 9 / 15)


def test_fade_checks_its_numbers():
    for bad in (dict(start=16), dict(start=-1), dict(pace=8), dict(pace=-1)):
        with pytest.raises(ValueError):
            Fade(**bad)


def test_velocity_picks_the_starting_step():
    loud, soft = (np.abs(render(PulseChannel(quantize=False).note(750.0, 0.1, v), 0.1)).max() for v in (1.0, 0.4))
    assert soft / loud == pytest.approx(6 / 15, rel=0.05)


def test_a_table_value_of_sixteen_raises():
    with pytest.raises(ValueError, match="16"):
        WaveChannel(table=[16] + [0] * 31)
    with pytest.raises(ValueError, match="32"):
        WaveChannel(table=[0] * 16)
    with pytest.raises(ValueError):
        WaveChannel(shift=3)


def test_wave_shift_halves_the_level():
    peaks = [np.abs(render(WaveChannel(table=SAW, shift=s).note(A4, 0.1), 0.1)).max() for s in (0, 1, 2)]
    assert peaks[1] / peaks[0] == pytest.approx(0.5, rel=0.02)
    assert peaks[2] / peaks[0] == pytest.approx(0.25, rel=0.02)


def test_wave_table_is_centred():
    x = render(WaveChannel(table=TRIANGLE, quantize=False).note(750.0, 0.2), 0.2)
    assert abs(x.mean()) < 0.01 * np.abs(x).max()


def test_the_short_noise_repeats_every_127_steps():
    hold = 4  # samples per clock step
    drum = NoiseDrum(RATE / hold, short=True, fade=Fade(15))
    noise = NoiseChannel()
    x = render(noise.play(noise.hit(0.0, drum, 1.0)), 0.05)
    period = 127 * hold
    assert np.array_equal(x[:period], x[period:2 * period])
    assert not np.array_equal(x[:period // 2], x[period // 2:period])


def test_noise_drums_are_dark_and_bright():
    noise = NoiseChannel()
    kick, hat = (render(noise.play(noise.hit(0.0, d, 1.0)), 0.05) for d in (noise.kick, noise.hat))
    assert band_db(kick, 0, 2_000) - band_db(kick, 8_000, 20_000) > band_db(hat, 0, 2_000) - band_db(hat, 8_000, 20_000)


def test_noise_pattern_reads_the_grid_as_kit_pattern():
    noise, kit = NoiseChannel(), Kit()
    grid = "x...X.g.x..."
    a = noise.pattern({noise.snare: grid}, step=0.125, repeat=2)
    b = kit.pattern({kit.snare: grid}, step=0.125, repeat=2)
    assert [(n.time, n.velocity) for n in a] == [(n.time, n.velocity) for n in b]
    assert all(n.resource is noise.snare for n in a)
    with pytest.raises(ValueError, match="'k'"):
        noise.pattern({noise.kick: "x.k."}, step=0.1)


def test_a_sweep_moves_the_pitch():
    pulse = PulseChannel(sweep=-24.0, quantize=False)
    x = render(pulse.note(800.0, 0.5, 1.0), 0.5)
    early, late = peak_hz(x[:RATE // 10]), peak_hz(x[int(0.4 * RATE):])
    assert _cents(early, late) == pytest.approx(0.4 * 2400, abs=30)  # window centres 0.4 s apart


def test_a_legato_pair_is_one_voice():
    for channel in (PulseChannel(), WaveChannel()):
        phrase = channel.play([Note(0.0, A4, 0.2), Note(0.2, B4, 0.2, articulation=Legato())])
        assert len(phrase.voices) == 1


def test_classic_is_mono_and_modern_stereo():
    for chip, channels in ((ClassicChip(), 1), (ModernChip(), 2)):
        x = render(_song(chip), 0.6)
        assert x.ndim == channels
        assert not lint_audio(x).errors


def test_modern_pans_the_pulses_apart():
    chip = ModernChip(echo=0.0, room=0.0)
    x = render(chip.play(pulse1=[(0.0, A4, 0.2)]), 0.2)
    y = render(chip.play(pulse2=[(0.0, A4, 0.2)]), 0.2)
    left, right = (np.sqrt(np.mean(np.square(x[:, k]))) for k in (0, 1))
    assert left > right
    left, right = (np.sqrt(np.mean(np.square(y[:, k]))) for k in (0, 1))
    assert right > left


def test_modern_plays_exact_pitch_and_detunes_pulse2():
    chip = ModernChip()
    assert not chip.pulse1.quantize and not chip.pulse1.steps and chip.pulse2.detune == 6.0
    x = render(chip.pulse1.note(C8, 0.2, 1.0), 0.2)[RATE // 20:RATE // 5]
    assert abs(_cents(peak_hz(x), C8.freq)) < 5


def test_classic_channels_have_steps_and_no_effects():
    chip = ClassicChip()
    for c in (chip.pulse1, chip.pulse2, chip.wave):
        assert c.steps and c.quantize and c.vibrato is None and c.glide == 0.0
    assert chip.noise.steps


def _song(chip):
    noise = chip.noise
    return chip.play(pulse1=PHRASE, pulse2=[(0.0, G4, 0.5)], wave=[(0.0, C4.freq / 2, 0.5)],
                     noise=noise.pattern({noise.kick: "x...", noise.hat: "..x."}, step=0.1))


@pytest.mark.parametrize("make", [ClassicChip, ModernChip])
def test_block_size_independence_and_determinism(make):
    a = render(_song(make()), 0.02, block=1)
    b = render(_song(make()), 0.02)
    assert np.array_equal(a, b)
