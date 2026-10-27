import numpy as np
import pytest

from euterpe.sound import (
    ADSR, RATE, Comb, Compressor, ConvolutionReverb, Delay, FDNReverb, Formant, Modal,
    LowPass, OnePoleLowPass, Pan, Pluck, Saw, Segments, Sine, Tanh, WhiteNoise, Width, render,
)

FINITE = {
    "adsr": lambda: Saw(220) * ADSR(gate=0.5, release=0.3),
    "segments": lambda: Saw(110) * Segments([(0, 0), (0.1, 1), (0.6, 0)]),
    "pluck": lambda: Pluck(220),
    "pluck long": lambda: Pluck(110, damping=0.998),
    "modal": lambda: Modal([440, 1214], decays=[1.2, 0.5], amps=[1, 0.5]),
    "lowpass q12": lambda: LowPass(Saw(110) * ADSR(gate=0.3, release=0.1), cutoff=800, q=12),
    "onepole": lambda: OnePoleLowPass(WhiteNoise(seed=1) * ADSR(gate=0.2, release=0.05), cutoff=200),
    "formant": lambda: Formant(Saw(110) * ADSR(gate=0.3, release=0.1), "a"),
    "comb": lambda: Comb(Pluck(220), delay=0.01, feedback=0.9),
    "delay": lambda: Delay(Pluck(220), time=0.3, feedback=0.45, mix=0.5),
    "fdn": lambda: FDNReverb(Pluck(220), decay=1.5),
    "convolution": lambda: ConvolutionReverb(Pluck(220), decay=1.0),
    "compressor": lambda: Compressor(Pluck(220), threshold=-30, ratio=4),
    "shaper": lambda: Tanh(Pluck(220), drive=4),
    "mix": lambda: Pluck(220) + Pluck(330) * 0.5,
    "stereo": lambda: Pan(Pluck(220), 0.5),
    "width": lambda: Width(FDNReverb(Pluck(220), decay=0.8), 1.5),
}


@pytest.mark.parametrize("name", FINITE)
def test_output_is_silent_after_duration(name):
    u = FINITE[name]()
    d = u.duration
    assert d is not None and d < 60
    x = render(u, d + 0.5)
    assert np.abs(x[round(d * RATE):]).max() < 1e-3


@pytest.mark.parametrize("make", [
    lambda: Sine(440),
    lambda: Pluck(220) + Sine(1),
    lambda: Saw(220) * ADSR(gate=Sine(1)),
    lambda: Saw(110) * Segments([(0, 0), (0.1, 1)]),
    lambda: Delay(Sine(220)),
])
def test_endless_units_report_none(make):
    assert make().duration is None


def test_durations_are_not_wildly_long():
    assert Pluck(220).duration < 10
    assert (Saw(220) * ADSR(gate=0.5, release=0.3)).duration == pytest.approx(0.8)
    assert (Saw(110) * Segments([(0, 0), (0.1, 1), (0.6, 0)])).duration == pytest.approx(0.6)


def _burst():
    return WhiteNoise(seed=2) * Segments([(0.0, 1.0), (0.06, 1.0), (0.06, 0.0)])


@pytest.mark.parametrize("make", [
    lambda: Comb(_burst(), delay=0.01, feedback=0.95),
    lambda: Comb(_burst(), delay=0.01, feedback=-0.99),
    lambda: Modal([440, 1214], decays=[1.2, 0.5], amps=[1, 0.5], excite=_burst()),
])
def test_resonant_units_are_silent_after_duration(make):
    u = make()
    d = u.duration
    x = render(u, d + 0.5)
    assert np.abs(x[round(d * RATE):]).max() < 1e-3
