"""Rules that measure rendered audio: level, loudness, offset, endings, gaps, balance, loops."""

from __future__ import annotations

import numpy as np
import pyloudnorm
from scipy.signal import resample_poly

from euterpe.lint.finding import Finding, Report

QUIET_DB = -60.0       # below this a stretch counts as silence
CLIP = 0.999           # a sample at or above this magnitude counts as full scale
BANDS = ((0.0, 250.0, "low"), (250.0, 4_000.0, "mid"), (4_000.0, np.inf, "high"))


def _db(x: float) -> float:
    return 20 * np.log10(x)


def _peak(x: np.ndarray) -> float:
    return float(np.abs(x).max()) if x.size else 0.0


def lint_audio(samples: np.ndarray, rate: int = 48_000, *, loop: bool = False) -> Report:
    """Measure samples, (n,) or (n, channels), and report peak, loudness and common faults.

    With loop, also check that the end joins the start without a jump.
    """
    x = np.asarray(samples, np.float64)
    chans = x if x.ndim == 2 else x[:, None]
    mono = chans.mean(axis=1)
    level = np.abs(chans).max(axis=1)        # the louder channel, sample by sample
    findings = []

    peak = _peak(x)
    if peak > 0:
        findings.append(Finding("A-PEAK", "metric", f"sample peak {_db(peak):.1f} dBFS", round(_db(peak), 2)))
    else:
        findings.append(Finding("A-PEAK", "metric", "the audio is silent"))

    if len(x) and peak > 0:
        true = _peak(resample_poly(chans, 4, 1, axis=0))
        if _db(true) > -1.0:
            findings.append(Finding(
                "A-TRUEPEAK", "warn",
                f"true peak {_db(true):+.1f} dBTP, above -1 dBTP: a converter may clip between samples",
                round(_db(true), 2),
            ))

    hot = level >= CLIP
    runs = hot[2:] & hot[1:-1] & hot[:-2]    # three consecutive samples at full scale
    if runs.any():
        first = int(np.argmax(runs))
        findings.append(Finding(
            "A-CLIP", "error",
            f"clipped: {int(hot.sum())} samples at full scale, the first at {first / rate:.3f} s",
            float(hot.sum()), round(first / rate, 4),
        ))

    if len(x) >= 0.4 * rate:
        lufs = pyloudnorm.Meter(rate).integrated_loudness(chans if chans.shape[1] > 1 else mono)
        if np.isfinite(lufs):
            findings.append(Finding("A-LUFS", "metric", f"integrated loudness {lufs:.1f} LUFS", round(float(lufs), 2)))

    if len(x):
        dc = float(np.abs(chans.mean(axis=0)).max())
        if dc > 0.001:
            findings.append(Finding("A-DC", "warn", f"DC offset {dc:.4f}: the wave is not centred on 0", round(dc, 5)))

    tail = _peak(level[-int(0.05 * rate):])
    if tail > 10 ** (QUIET_DB / 20):
        findings.append(Finding(
            "A-TAIL", "warn",
            f"still sounding when the audio ends: the last 50 ms peak at {_db(tail):.1f} dBFS",
            round(_db(tail), 2),
        ))

    findings += _silences(level, rate)

    energy = np.abs(np.fft.rfft(mono)) ** 2
    if energy.sum() > 0:
        freqs = np.fft.rfftfreq(len(mono), 1 / rate)
        for lo, hi, name in BANDS:
            share = float(energy[(freqs >= lo) & (freqs < hi)].sum() / energy.sum())
            span = f"below {hi:.0f} Hz" if lo == 0 else f"above {lo:.0f} Hz" if hi == np.inf else f"{lo:.0f}-{hi:.0f} Hz"
            findings.append(Finding("A-BALANCE", "metric", f"{name} ({span}): {100 * share:.1f} % of the energy", share))

    if loop and len(x):
        jump = float(np.abs(chans[-1] - chans[0]).max())
        if jump > 0.1:
            findings.append(Finding(
                "A-SEAM", "warn", f"the loop jumps by {jump:.2f} from its last sample to its first", round(jump, 4)
            ))

    return Report(findings)


def _silences(level: np.ndarray, rate: int) -> list[Finding]:
    """Gaps longer than 2 s below QUIET_DB with sound on both sides, measured in 10 ms steps."""
    step = rate // 100
    n = len(level) // step
    if n == 0:
        return []
    loud = level[: n * step].reshape(n, step).max(axis=1) > 10 ** (QUIET_DB / 20)
    out = []
    sounding = np.flatnonzero(loud)
    for a, b in zip(sounding[:-1], sounding[1:]):
        gap = (b - a - 1) * step / rate
        if gap > 2.0:
            start = (a + 1) * step / rate
            out.append(Finding(
                "A-SILENCE", "warn", f"{gap:.1f} s of silence between sounds, from {start:.2f} s", round(gap, 3), start
            ))
    return out
