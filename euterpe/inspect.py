"""Inspect a piece without ears: a directory of drawings and a summary.txt of one fact per line, the written score
beside what its audio measures. Drawing needs matplotlib (euterpe[view]). Spec 2026-10-30, section 09."""

from __future__ import annotations

import math
import re
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from scipy.signal import resample_poly

from euterpe.lint import Report, lint_audio, lint_score
from euterpe.score.model import Hit, Note
from euterpe.sound.clip import Clip
from euterpe.theory import Key
from euterpe.view.signal import _HOP, chromagram

if TYPE_CHECKING:
    from euterpe.score.model import Score
    from euterpe.view.base import View

# Krumhansl and Kessler's key profiles (1982), from C upward: how well each pitch class fits the key.
_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
# Each tonic in the spelling with the fewest accidentals, as (major, minor).
_TONICS = (("C", "C"), ("Db", "C#"), ("D", "D"), ("Eb", "Eb"), ("E", "E"), ("F", "F"), ("F#", "F#"), ("G", "G"),
           ("Ab", "G#"), ("A", "A"), ("Bb", "Bb"), ("B", "B"))
# Chord qualities the audio can name, as pitch classes over the root. Chroma has no octave, so no inversion.
_QUALITIES = {"": (0, 4, 7), "m": (0, 3, 7), "dim": (0, 3, 6), "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11),
              "m7": (0, 3, 7, 10)}
_CHORD_DECAY, _KEY_DECAY = 0.4, 0.6  # each harmonic's weight over the last's, the values measured to read best
_FITS = 0.75  # cosine to a template. Measured: a chord under a melody on harp and strings 0.80, one rich note 0.64
_SEVENTH = 0.05  # a seventh must beat its triad by this. Measured: a melody's harmonic fakes 0.04, a real one gains 0.07
_PRESENT = 0.05  # each chord tone's least share of the unit chroma, so a bare fifth or third names no chord


def _heard(tones: np.ndarray, decay: float) -> np.ndarray:
    """Weights on the 12 pitch classes as a chroma hears them: each with its first six harmonics, which fall on the
    tone itself, its fifth and its major third, at decay to the power of the harmonic's number."""
    return sum(decay ** n * np.roll(tones, over) for n, over in enumerate((0, 0, 7, 0, 4, 7)))


def _template(tones: tuple[int, ...]) -> np.ndarray:
    """A chord's chroma with each tone's harmonics, so an organ's F does not read as Fmaj7 through the E of its A's
    third harmonic."""
    template = _heard(np.isin(np.arange(12), tones).astype(float), _CHORD_DECAY)
    return template / np.linalg.norm(template)


_TEMPLATES = {quality: (tones, _template(tones)) for quality, tones in _QUALITIES.items()}


def estimate_key(chroma: np.ndarray) -> tuple[Key, float]:
    """The key whose Krumhansl-Kessler profile, heard with its tones' harmonics, correlates best with the chroma, shape
    (12,) or (12, frames), and that correlation. Bare profiles read a rich instrument's major key as its dominant, since
    every tone's third harmonic sounds a fifth up. A chroma with no differences to read, such as silence, gives C major
    at 0."""
    x = np.asarray(chroma, float)
    x = x.mean(axis=1) if x.ndim == 2 and x.size else x
    if not x.size or x.std() == 0:
        return Key("C major"), 0.0
    found = [(float(np.corrcoef(x, np.roll(profile, tonic))[0, 1]), tonic, mode)
             for mode, profile in ((0, _heard(_MAJOR, _KEY_DECAY)), (1, _heard(_MINOR, _KEY_DECAY))) for tonic in range(12)]
    r, tonic, mode = max(found)
    return Key(f"{_TONICS[tonic][mode]} {('major', 'minor')[mode]}"), r


def chords_per_beat(clip: Clip, score: Score) -> list[tuple[int, Fraction, str | None]]:
    """The chord the audio holds on each beat as played, a repeat's beats once per pass: (bar, beat counted from 1, its
    symbol spelled in the key in force, or None where no triad or common seventh fits). It reads the middle half of
    each beat, where the 8192-point window leans least on the beats beside it. A seventh on a fast-decaying instrument
    may read as its triad."""
    chroma = chromagram(clip)
    tempo = score.tempo_map()
    read = []
    for bar in tempo.played:
        position = Fraction(0)
        for number, size in enumerate(bar.meter.groups, 1):
            end = position + Fraction(size, bar.meter.denominator)
            first, last = max(position, bar.lead) - bar.lead, min(end - bar.lead, bar.length)
            if last > first:
                start, stop = tempo.seconds(bar.start + first), tempo.seconds(bar.start + last)
                span = (stop - start) * clip.rate / _HOP
                low = int(start * clip.rate / _HOP + span / 4)
                frames = chroma[:, low:max(low + 1, math.ceil(low + span / 2))]
                read.append((bar.bar, Fraction(number), _chord_name(frames, score.key_at(bar.bar))))
            position = end
    return read


def _chord_name(frames: np.ndarray, key: Key) -> str | None:
    if not frames.size or not frames.any():
        return None
    x = frames.mean(axis=1)
    x = x / np.linalg.norm(x)
    fit, root, quality = 0.0, 0, ""
    for name, (tones, template) in _TEMPLATES.items():
        for tonic in range(12):
            score = float(x @ np.roll(template, tonic)) - (_SEVENTH if len(tones) > 3 else 0.0)
            if score > fit and min(x[(tonic + tone) % 12] for tone in tones) >= _PRESENT:
                fit, root, quality = score, tonic, name
    if fit < _FITS:
        return None
    pitch = key.spell(60 + root)
    return f"{pitch.letter}{'#' * pitch.alter or 'b' * -pitch.alter}{quality}"


def inspect(score: Score, out: str | Path, seed: int = 0) -> list[Path]:
    """Render the score from seed and write into out, made if missing: roll-<part>.png per part, spectrogram.png,
    chroma.png, loudness.png and summary.txt. Returns their paths, summary.txt last. ImportError without matplotlib,
    before anything is written; ValueError for a score that cannot play or has nothing written."""
    try:
        import matplotlib  # noqa: F401
    except ImportError as e:
        raise ImportError("inspect draws its PNGs with matplotlib: pip install 'euterpe[view]'") from e
    audio = score.play(seed)
    clip = audio.take()
    if not len(clip):
        raise ValueError("inspect: the score has nothing written, so there is nothing to measure")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    report = Report(lint_score(score).findings + lint_audio(clip.samples, clip.rate).findings)
    names = _file_names(score)
    drawings = [(f"roll-{names[part]}.png", score.roll(part)) for part in score.parts]
    drawings += [("spectrogram.png", clip.spectrogram()), ("chroma.png", clip.chroma()), ("loudness.png", clip.level())]
    paths = [_png(view, out / name) for name, view in drawings]
    summary = out / "summary.txt"
    summary.write_text("\n".join(_summary(score, clip, report)) + "\n")
    return [*paths, summary]


def _png(view: View, path: Path) -> Path:
    import matplotlib.pyplot as plt

    with view._context():
        fig = view.draw()
        fig.savefig(path, format="png", bbox_inches="tight", pad_inches=0.15, dpi=150)
        plt.close(fig)
    return path


def _file_names(score: Score) -> dict[str, str]:
    """A name safe in a path for each part, none two the same on a filesystem that ignores case."""
    names: dict[str, str] = {}
    taken: set[str] = set()
    for part in score.parts:
        base = re.sub(r"[^\w.-]+", "-", part).strip("-.") or "part"
        name, count = base, 1
        while name.lower() in taken:
            count += 1
            name = f"{base}-{count}"
        taken.add(name.lower())
        names[part] = name
    return names


def _summary(score: Score, clip: Clip, report: Report) -> list[str]:
    lufs = report.value("A-LUFS")
    peak = float(np.abs(resample_poly(clip.samples, 4, 1, axis=0)).max())  # 4x, as A-TRUEPEAK reads it
    key, r = estimate_key(chromagram(clip))
    lines = [f"length: {clip.seconds:.2f} s",
             "loudness: too short or too quiet to measure" if lufs is None else f"loudness: {lufs:.1f} LUFS",
             "true peak: silent" if peak == 0 else f"true peak: {20 * math.log10(peak):.1f} dBTP",
             f"key: {key.tonic} {key.mode} (audio {r:.2f}), written {_written_keys(score)}"]
    written = {(h.bar, h.beat): h.chord for h in score.harmony()}
    for bar, beat, name in chords_per_beat(clip, score):
        chord = written.get((bar, int(beat)))
        lines.append(f"chord {bar}.{beat}: audio {name or '?'}, written {chord.name if chord else '?'}")
    lines += [f"part {part}: {_part_facts(score, part)}" for part in score.parts]
    lines += [f"metric {f.rule}: {f.place}{f.message}" for f in report.findings if f.severity == "metric"]
    return lines


def _written_keys(score: Score) -> str:
    keys = [f"{score.key.tonic} {score.key.mode}"]
    keys += [f"{c.key.tonic} {c.key.mode} from bar {c.bar}" for c in score.changes if c.key is not None]
    return ", ".join(keys)


def _part_facts(score: Score, part: str) -> str:
    events = [placed.event for placed in score.events(part)]
    pitches = [pitch for event in events if isinstance(event, Note) for pitch in event.pitches]
    hits = sum(isinstance(event, Hit) for event in events)
    facts = [f"{_count(len(pitches), 'note')}, {min(pitches)} to {max(pitches)}"] if pitches else []
    facts += [_count(hits, "hit")] if hits else []
    return ", ".join(facts) or "no notes"


def _count(n: int, name: str) -> str:
    return f"{n} {name}" if n == 1 else f"{n} {name}s"
