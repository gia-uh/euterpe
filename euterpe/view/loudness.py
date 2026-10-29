"""The gain a view plays a clip at: every sound at the same perceived loudness, unless asked
for its rendered level. Spec 2026-10-28, section 05."""

from __future__ import annotations

import numpy as np

from euterpe.sound.clip import Clip

TARGET = -16.0  # LUFS, integrated (BS.1770)
CEILING = -1.0  # dBFS: the gain never lifts the sample peak above this
GATE_SECONDS = 0.4  # BS.1770 measures in 400 ms blocks; a shorter clip is padded with silence


def loudness(clip: Clip) -> float:
    """Integrated loudness in LUFS, -inf for silence."""
    import pyloudnorm

    x = np.asarray(clip.samples, np.float64)
    short = round(GATE_SECONDS * clip.rate) - len(x)
    if short > 0:  # the absolute gate drops the padding
        x = np.concatenate([x, np.zeros((short,) + x.shape[1:])])
    if not np.any(x):
        return float("-inf")
    return float(pyloudnorm.Meter(clip.rate).integrated_loudness(x))


def gain(clip: Clip, normalize: bool = True) -> tuple[float, float]:
    """(gain, loudness): the factor that brings the clip to TARGET, capped so its sample peak
    stays at CEILING, and the clip's loudness as rendered. 1 without normalize or for silence."""
    lufs = loudness(clip)
    if not normalize or not np.isfinite(lufs):
        return 1.0, lufs
    peak = float(np.abs(clip.samples).max())
    return min(10 ** ((TARGET - lufs) / 20), 10 ** (CEILING / 20) / peak), lufs
