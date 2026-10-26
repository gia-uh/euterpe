import json

import numpy as np
import pytest

from euterpe.lint import Finding, Report, lint_audio
from euterpe.sound import Sine, render

RATE = 48_000


def sine(seconds=1.0, amp=0.5, freq=1_000.0):
    return render(Sine(freq) * amp, seconds)


def found(report, rule):
    return [f for f in report.findings if f.rule == rule]


def test_peak_of_a_half_scale_sine():
    (f,) = found(lint_audio(sine()), "A-PEAK")
    assert f.severity == "metric" and f.value == pytest.approx(-6.02, abs=0.05)


def test_peak_of_silence_has_no_value():
    (f,) = found(lint_audio(np.zeros(RATE, np.float32)), "A-PEAK")
    assert f.value is None


def test_true_peak_between_samples():
    # a sine at a quarter of the rate, sampled 45 degrees off its crests: the samples peak at
    # 0.707 of the wave, so a wave reaching 1.2 has samples at 0.85 (-1.4 dBFS) and a true peak of +1.6 dBTP
    t = np.arange(RATE)
    x = (1.2 * np.sin(np.pi / 2 * t + np.pi / 4)).astype(np.float32)
    (f,) = found(lint_audio(x), "A-TRUEPEAK")
    assert f.severity == "warn" and f.value == pytest.approx(1.58, abs=0.2)
    assert not found(lint_audio(sine()), "A-TRUEPEAK")


def test_clipping_is_an_error_at_the_first_clipped_sample():
    x = np.clip(render(Sine(1_000.0) * 2.0, 1.0), -1, 1)
    x[: RATE // 2] *= 0.25
    (f,) = found(lint_audio(x), "A-CLIP")
    assert f.severity == "error" and f.at == pytest.approx(0.5, abs=0.002)
    assert not found(lint_audio(sine(amp=0.99)), "A-CLIP")


def test_two_samples_at_full_scale_are_not_clipping():
    x = sine()
    x[100:102] = 1.0
    assert not found(lint_audio(x), "A-CLIP")


def test_loudness_of_a_half_scale_sine():
    (f,) = found(lint_audio(sine()), "A-LUFS")
    assert f.severity == "metric" and f.value == pytest.approx(-9.03, abs=0.1)


def test_loudness_is_skipped_under_0_4_seconds():
    assert not found(lint_audio(sine(0.3)), "A-LUFS")


def test_dc_offset_on_one_channel():
    x = np.stack([sine(), sine() + 0.01], axis=1)
    (f,) = found(lint_audio(x), "A-DC")
    assert f.severity == "warn" and f.value == pytest.approx(0.01, abs=1e-4)
    assert not found(lint_audio(sine()), "A-DC")


def test_a_note_cut_mid_sound_has_a_tail():
    (f,) = found(lint_audio(sine()), "A-TAIL")
    assert f.severity == "warn" and f.value == pytest.approx(-6.02, abs=0.05)
    x = np.concatenate([sine(), np.zeros(RATE // 10, np.float32)])
    assert not found(lint_audio(x), "A-TAIL")


def test_a_tail_at_minus_40_dbfs_still_sounds():
    x = np.concatenate([sine(), sine(0.1, amp=0.01)])
    (f,) = found(lint_audio(x), "A-TAIL")
    assert f.value == pytest.approx(-40.0, abs=0.1)


def test_a_gap_of_three_seconds_between_two_notes():
    x = np.concatenate([sine(), np.zeros(3 * RATE, np.float32), sine()])
    (f,) = found(lint_audio(x), "A-SILENCE")
    assert f.severity == "warn" and f.at == pytest.approx(1.0, abs=0.02)
    assert f.value == pytest.approx(3.0, abs=0.02)


def test_a_gap_filled_at_minus_40_dbfs_is_not_silence():
    x = np.concatenate([sine(), sine(3.0, amp=0.01), sine()])
    assert not found(lint_audio(x), "A-SILENCE")


def test_a_short_gap_and_trailing_silence_are_not_silence_findings():
    x = np.concatenate([sine(), np.zeros(RATE, np.float32), sine(), np.zeros(5 * RATE, np.float32)])
    assert not found(lint_audio(x), "A-SILENCE")


def test_balance_of_a_low_tone():
    report = lint_audio(sine(freq=100.0))
    low, mid, high = found(report, "A-BALANCE")
    assert all(f.severity == "metric" for f in (low, mid, high))
    assert low.value > 0.99 and mid.value + high.value < 0.01
    assert low.value + mid.value + high.value == pytest.approx(1.0)


@pytest.mark.parametrize("freq, band", [(200.0, 0), (300.0, 1), (1_000.0, 1), (3_500.0, 1), (5_000.0, 2), (8_000.0, 2)])
def test_balance_puts_a_tone_in_its_band(freq, band):
    shares = [f.value for f in found(lint_audio(sine(freq=freq)), "A-BALANCE")]
    assert shares[band] > 0.99


def test_a_loop_whose_ends_do_not_meet():
    x = sine(0.5 + 0.25 / 1_000)          # ends a quarter cycle late: at the crest
    (f,) = found(lint_audio(x, loop=True), "A-SEAM")
    assert f.severity == "warn" and f.value == pytest.approx(0.5, abs=0.01)
    assert not found(lint_audio(x), "A-SEAM")
    assert not found(lint_audio(sine(0.5), loop=True), "A-SEAM")


def test_errors_lists_only_errors():
    x = np.clip(render(Sine(1_000.0) * 2.0, 1.0), -1, 1)
    report = lint_audio(x)
    assert [f.rule for f in report.errors] == ["A-CLIP"]
    assert lint_audio(sine()).errors == []


def test_report_json_round_trips():
    report = lint_audio(np.clip(render(Sine(1_000.0) * 2.0, 1.0), -1, 1))
    data = json.loads(report.to_json())
    assert Report([Finding(**f) for f in data["findings"]]) == report


def test_text_has_one_line_per_finding():
    report = Report([Finding("A-PEAK", "metric", "sample peak -6.0 dBFS", -6.02)])
    assert report.to_text() == "metric A-PEAK      sample peak -6.0 dBFS"
    assert len(lint_audio(sine()).to_text().splitlines()) == len(lint_audio(sine()).findings)
