# Pitch and loudness

Chapter 1 described a sound as a list of numbers. This chapter connects two properties of those numbers to what you hear. Frequency becomes *pitch*, how high or low a note sounds. Amplitude becomes *loudness*. In both cases the ear does not follow the numbers themselves. It follows their ratios, and that is why music and audio measure both with logarithms. This is where it ends up:

```python {run echo=false}
# The teaser: the start of the finale, built by the code of this chapter's last sections, which
# it reads from this file so the two never differ.
import re
from pathlib import Path

from euterpe.view import listen

text = Path("chapters/02-pitch-and-loudness.md").read_text()
for name in ("tune", "finale"):
    exec(re.search(r"```python \{[^}\n]*name=" + name + r"\b[^}\n]*\}\n(.*?)\n```", text, re.S).group(1))
listen(song, 10.0, "The first 10 s of the chapter's finale")
```

A song you probably know, sung as a round by three different waves. A *round* is a tune sung by voices that start it at staggered times. Its notes are computed from one frequency, 220 Hz, and one rule, the subject of the first half; the three waves are made equally loud with the measurement of the second half.

## Octaves: pitch follows ratios

As in chapter 1, a *unit* is anything that produces samples over time. Units combine: `a * 0.5` multiplies every sample of `a` by 0.5, which is called applying a *gain* of 0.5, and `a + b` adds two units sample by sample. A unit can also be another unit's parameter, and then it is read again at every sample.

The sound below uses that to alternate between two sines, half a second each: 440 Hz, then 220 Hz. `Square(1.0)` is a unit that is +1 for half a second and −1 for the next half. So `Square(1.0) * 110 + 330` is 440 for half a second and 220 for the next, and as the frequency of a `Sine` it makes the sine jump between the two.

```python {run}
from euterpe.sound import Sine, Square

display((Sine(Square(1.0) * 110 + 330) * 0.5).take(4.0, "440 Hz and 220 Hz in turn"))
```

(The player's caption measures loudness in LUFS, defined in the second half of this chapter; every player brings its sound to the same loudness.) The two tones sound like the same note, one higher than the other. The higher one has exactly twice the frequency. This distance, a ratio of 2, is called an *octave*, and it is the reason the same note name repeats: every note shares its name with the notes at twice and half its frequency.

Now keep the difference the same, 220 Hz, but move up: 1 980 Hz and 1 760 Hz. Then keep the ratio instead: 3 520 Hz and 1 760 Hz.

```python {run}
from euterpe.sound import Sine, Square
from euterpe.view import listen

display((Sine(Square(1.0) * 110 + 1_870) * 0.5).take(4.0, "1 980 Hz and 1 760 Hz in turn: 220 Hz apart"))
listen(Sine(Square(1.0) * 880 + 2_640) * 0.5, 4.0, "3 520 Hz and 1 760 Hz in turn: an octave")
```

The first pair is 220 Hz apart, like the octave above, but it sounds like a small step: its ratio is 1 980 / 1 760 = 1.125, close to what the next section calls two semitones. The second pair is 1 760 Hz apart and sounds like the same leap as 440 and 220. What the ear hears as the distance between two pitches is the ratio of their frequencies, not the difference. Equal ratios sound like equal steps, so pitch is the logarithm of frequency: each octave adds the same amount to the pitch, while the frequency doubles.

The plot shows the 88 keys of a piano, from the lowest, A0 at 27.5 Hz (four octaves below 440 Hz, 440 / 2⁴), to the highest, a little above 4 000 Hz. On a linear axis the low half of the keyboard is squeezed against the bottom. On a logarithmic axis, where each doubling takes the same height, the keys lie on a straight line.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.view import figure

def draw():
    key = np.arange(1, 89)
    freq = 440.0 * 2 ** ((key - 49) / 12)
    fig, axes = plt.subplots(1, 2, figsize=(8, 3))
    for ax, scale in zip(axes, ["linear", "log"]):
        ax.plot(key, freq, ".", markersize=3)
        ax.set_yscale(scale)
        ax.set_xlabel("piano key", fontstyle="italic")
        ax.set_title(f"{scale} frequency axis", fontstyle="italic", fontsize=9.5)
    axes[0].set_ylabel("frequency (Hz)", fontstyle="italic")
    return fig

figure(draw, caption="The 88 piano keys: a doubling per octave, a straight line on a log axis")
```

## Twelve equal steps

Western music divides the octave into twelve steps. Each step is called a *semitone*, and two semitones make a *whole tone*. Twelve steps must multiply the frequency by 2, and each step should sound the same size, so each step multiplies the frequency by the same number r, with r to the twelfth power equal to 2. That number is the twelfth root of 2, `2 ** (1 / 12)` in Python, about 1.0595. Tuning every step to exactly this ratio is called *equal temperament*, and nearly all music you hear today uses it.

The steps need a fixed point to start from. The modern standard is A4 = 440 Hz: the note called A in octave 4, the sine at the top of chapter 1. Here is A4 raised by 0, 1, 2 and 12 steps:

```python {run}
from euterpe.sound import Sine
from euterpe.view import listen

semitone = 2 ** (1 / 12)
for steps in (0, 1, 2, 12):
    freq = 440.0 * semitone ** steps
    display(listen(Sine(freq) * 0.5, 1.5, f"A4 raised by {steps} steps: {freq:.2f} Hz"))
```

One step is the smallest distance in most music: the two tones are clearly different, but close. Two steps sound like the step between neighbouring notes of a simple tune. Twelve steps land at 880 Hz, A5, one octave up.

The twelve notes of an octave have seven letter names, A to G, and five names with a sharp (♯, one step up) or a flat (♭, one step down). The same key can have two names: A♯ and B♭ are the same note in equal temperament. This loop prints one octave from A4: the number of steps n, the ratio 2^(n/12) and the frequency 440 × 2^(n/12).

```python {run output=code}
import numpy as np

names = ["A4", "A♯4", "B4", "C5", "C♯5", "D5", "D♯5", "E5", "F5", "F♯5", "G5", "G♯5", "A5"]
for n, name in enumerate(names):
    print(f"{n:2}  {name:4}  {2 ** (n / 12):.4f}  {440 * 2 ** (n / 12):7.2f} Hz")
print("from 440 to 466.16 Hz:", round(1200 * np.log2(466.16 / 440), 1), "cents")
```

There is no sharp between B and C, or between E and F. The seven letters come from an older scale of seven notes, the white keys of a piano, whose steps are not all the same size: five of them are whole tones and two, B to C and E to F, are semitones. The five sharps fill the five whole-tone gaps, the black keys. So in equal temperament B♯ is simply another name for C, and E♯ for F.

The octave number goes up at C, not at A, for historical reasons: B4 is followed by C5. The C just below A4 is C4, called *middle C*, nine steps below A4. MIDI, the standard for sending notes between instruments and programs, numbers the notes by semitone with A4 = 69 and middle C = 60. Musicians also split each semitone into 100 *cents*, to talk about notes that are slightly out of tune, so one cent is a ratio of 2^(1/1200). Going the other way, a logarithm turns a ratio back into steps: the distance from f1 to f2 is 1200 × log₂(f2 / f1) cents, as the last line of the table computes for A4 and A♯4, and a frequency f lies 12 × log₂(f / 440) semitones above A4. Middle C is 440 × 2^(−9/12) = 261.63 Hz.

### A tune from the rule

With the rule, a tune is a list of steps. Here is *Frère Jacques*, a French children's song, as semitones above A3 (220 Hz) and lengths in beats, half a second each:

```python {run name=tune}
from euterpe.instruments import play
from euterpe.sound import Sine

TUNE = ([(0, 1), (2, 1), (4, 1), (0, 1)] * 2 + [(4, 1), (5, 1), (7, 2)] * 2
        + [(7, 0.5), (9, 0.5), (7, 0.5), (5, 0.5), (4, 1), (0, 1)] * 2 + [(0, 1), (-5, 1), (0, 2)] * 2)


def notes(start):
    """(time, frequency, duration) of each note of the tune, from start, each held 90 % of its length."""
    out, t = [], start
    for steps, beats in TUNE:
        out.append((t, 220 * 2 ** (steps / 12), 0.9 * beats * 0.5))
        t += beats * 0.5
    return out


play(lambda n: Sine(n.freq) * 0.5, notes(0)).take(16.0, "Frère Jacques on a sine, in equal steps from A3")
```

`play` (from `euterpe.instruments`) takes a function that makes the sound of one note and a list of notes, each a start time, a frequency and a duration. It starts that sound at each note's time and fades it out over 5 ms at its end; `play` turns each `(time, frequency, duration)` tuple into a note with `.time`, `.freq` and `.duration`, so the function reads the note's frequency as `n.freq`. Chapter 9 looks inside it. Most moves of the tune are one or two steps; its last line drops 5 steps below the first note and comes back.

## Amplitude and decibels

The amplitude of a sound is how far its samples swing from 0. Loudness follows amplitude the way pitch follows frequency: by ratios. Halving the amplitude sounds like the same drop whether you start loud or quiet. So levels are measured on a logarithmic scale, in *decibels* (dB). The level of an amplitude a against a reference a₀ is

20 × log₁₀(a / a₀) dB.

Audio software takes full scale, 1.0, as the reference, and writes the result as dBFS, decibels relative to full scale. Full scale is 0 dBFS, and every level below it is negative.

Half the amplitude is 20 × log₁₀(0.5) = −6.02 dB, a tenth is −20 dB and a thousandth −60 dB. But −6 dB does not sound half as loud. A sound must drop by about 10 dB, to about a third of the amplitude, before most listeners hear it as half as loud. Here is the 440 Hz sine, halved twice. Every other player in this book brings its sound to the same loudness; these three pass `normalize=False`, which plays each at the level it was made at, since the level is what they show:

```python {run continue}
from euterpe.sound import Sine
from euterpe.view import listen

for gain in (0.5, 0.25, 0.125):
    display(listen(Sine(440.0) * gain, 1.5, f"The 440 Hz sine at gain {gain}", normalize=False))
```

Each player is 6 dB quieter than the one before it, and each drop sounds about as large as the last.

Why 20 and not 10? The decibel was defined for power, as 10 × log₁₀ of a power ratio, and the power a wave carries grows with the square of its amplitude. Squaring inside a logarithm doubles it, so the factor for amplitudes is 20. Half the amplitude is a quarter of the power, and both are −6 dB.

Your ear covers a huge range of levels. The quietest sound you can hear and the loudest you can bear differ by about 120 dB, a factor of a million in amplitude. On that scale a step of 1 dB is about the smallest change in level most people notice.

### Measuring a sound

A sample cannot go beyond full scale. When a computation asks for more, a file or a sound card stores ±1 instead, and the top of the wave is cut flat. This is called *clipping*, and it adds harsh new frequencies to the sound. Euterpe's `lint_audio` measures rendered samples and reports such mistakes, along with measurements, one line per finding. Here is the report for two seconds of the 440 Hz sine at gain 0.25:

```python {run continue output=code}
from euterpe.lint import lint_audio
from euterpe.sound import Sine, render

report = lint_audio(render(Sine(440.0) * 0.25, 2.0))
print(report.to_text())
```

Each line has a severity (a `metric` is a measurement, a `warn` may be a mistake, an `error` is one), a rule and a message. The one error rule is `A-CLIP`: three or more samples in a row at full scale. `A-PEAK` is the sample peak, −12.0 dBFS for a gain of 0.25, and `A-LUFS` a measure of loudness, the subject of the next section; the other rules matter in chapters 3 and 4. `report.value("A-PEAK")` returns one number from the report.

## Loudness is not level

Two sounds with the same peak do not always sound equally loud. Here are four sines, each at gain 0.5, so each peaks at −6 dBFS: 100 Hz, 1 000 Hz, 3 000 Hz and 12 000 Hz.

```python {run continue}
from euterpe import display
from euterpe.sound import Sine

for freq in (100.0, 1_000.0, 3_000.0, 12_000.0):
    display((Sine(freq) * 0.5).take(1.5, f"A {freq:.0f} Hz sine at gain 0.5"), normalize=False)
```

On most loudspeakers and headphones the 3 000 Hz sine sounds the loudest and the 100 Hz sine much quieter, although their samples swing equally far. The ear is most sensitive between about 2 000 and 5 000 Hz, where the ear canal resonates, and grows less sensitive towards low frequencies, and again above about 10 000 Hz. (Small loudspeakers also play 100 Hz weakly, which adds to the effect.)

*Loudness* is how loud a sound seems, and it can be estimated from the samples. The standard method, ITU-R BS.1770, does it in two steps. First it weights the frequencies roughly the way the ear does: a filter called K-weighting weakens the low frequencies, gently from a few hundred hertz and strongly below about 40 Hz, and strengthens everything above about 2 000 Hz by up to 4 dB. Then it averages the power of the weighted samples, leaving out the quiet parts, so that the pauses in a piece do not lower its loudness. (The average runs over short overlapping blocks, and a block counts only if it is not far quieter than the rest.)

The result is expressed in *LUFS*, loudness units relative to full scale. A loudness unit is one decibel, and the reference, 0 LUFS, is full scale, as in dBFS. The standard sets its offset so that a 1 000 Hz sine reads in LUFS the level of its average power in dBFS: a sine's average power is half the square of its peak, 3 dB below it, so a full-scale 1 000 Hz sine reads −3 LUFS. `A-LUFS` is this measurement. This line measures a sine at gain 0.5 at frequencies across the range of hearing, and the plot below draws the result:

```python {run continue}
from euterpe.lint import lint_audio
from euterpe.sound import Sine, render

freqs = [20, 30, 50, 100, 200, 500, 1_000, 2_000, 3_000, 5_000, 8_000, 12_000, 16_000, 20_000]
lufs = [lint_audio(render(Sine(float(f)) * 0.5, 1.0)).value("A-LUFS") for f in freqs]
```

```python {run continue echo=false}
import matplotlib.pyplot as plt

from euterpe.view import figure

def draw():
    fig, ax = plt.subplots(figsize=(7, 2.8))
    ax.semilogx(freqs, lufs, "o-", markersize=3)
    ax.axhline(-6.02, color="#9aa0a8", linewidth=0.5)
    ax.text(25, -5.6, "sample peak, −6 dBFS", fontsize=8, color="#9aa0a8", fontstyle="italic")
    ax.set_xlabel("frequency (Hz)", fontstyle="italic")
    ax.set_ylabel("loudness (LUFS)", fontstyle="italic")
    return fig

figure(draw, caption="The loudness of a sine at gain 0.5, by frequency, as A-LUFS measures it")
```

The measurement follows the ear at the bottom: a 100 Hz sine measures about 2 dB quieter than a 1 000 Hz one, and a 30 Hz sine 9 dB quieter. It does not follow the ear at the top: a 12 000 Hz sine measures as loud as a 3 000 Hz one, but it sounds quieter, and to many adults not at all. LUFS was designed for music and speech, which carry most of their energy below 5 000 Hz, and for those it agrees well with listeners. Broadcasters use it to keep programmes at the same loudness: the European broadcast standard, EBU R 128, sets every programme to −23 LUFS.

### The same peak, different shapes

The shape of a wave changes its loudness too. Here are four basic waveforms, `Sine`, `Triangle`, `Square` and `Saw`, at 220 Hz, all at gain 0.5. A triangle rises and falls in straight lines. A saw rises in a straight line and drops back at once, as in chapter 1. A square jumps between its high and its low value and stays at each for half a cycle. Chapter 3 looks at their shapes and what they contain.

```python {run continue}
from euterpe import display
from euterpe.sound import Saw, Sine, Square, Triangle

for wave in (Sine, Triangle, Square, Saw):
    display((wave(220.0) * 0.5).take(1.5, f"{wave.__name__} at 220 Hz, gain 0.5"), normalize=False)
```

The square sounds the loudest. It spends almost all of its time at +0.5 or −0.5, so it carries more power than the others, which pass through the values in between. *RMS*, the root of the mean of the squared samples, is that average power expressed as an amplitude. This block measures the peak, the RMS and the loudness of each wave:

```python {run continue output=code}
import numpy as np

from euterpe.lint import lint_audio
from euterpe.sound import Saw, Sine, Square, Triangle, render

for wave in (Sine, Triangle, Square, Saw):
    x = render(wave(220.0) * 0.5, 2.0)
    peak, rms = np.abs(x).max(), np.sqrt(np.mean(x ** 2))
    lufs = lint_audio(x).value("A-LUFS")
    print(f"{wave.__name__:8}  peak {20 * np.log10(peak):5.1f} dBFS  RMS {20 * np.log10(rms):5.1f} dBFS  {lufs:5.1f} LUFS")
```

A square's samples sit at its peak, so its RMS equals its peak. A sine's RMS is its peak divided by √2, 3 dB lower. A triangle's and a saw's are the peak divided by √3, 4.8 dB lower, because they pass evenly through every value from −peak to +peak. Three numbers read −6.1 instead of −6.0 because of the band-limiting correction of chapter 1: it rounds the triangle's corners and the saw's drop, so neither quite reaches 0.5, and the square spends a few samples of each cycle on the way between its two values.

The loudness spans 5 dB, from the triangle to the square, although the peaks are equal to within 0.1 dB. The saw has about the same RMS as the triangle but measures 0.5 dB louder, because more of its energy sits at high harmonics, which K-weighting strengthens. The sine reads about 1 dB below its RMS: at 1 000 Hz LUFS and RMS agree, by the offset above, and at 220 Hz the weighting has already started to weaken it.

To make the square as loud as the sine, lower it by the difference, 3.4 dB. That is a gain of 10^(−3.4/20) = 0.68 on top of the 0.5, so about 0.34:

```python {run continue}
from euterpe import display
from euterpe.sound import Sine, Square

display((Sine(220.0) * 0.5).take(1.5, "Sine at 220 Hz, gain 0.5"), normalize=False)
display((Square(220.0) * 0.34).take(1.5, "Square at 220 Hz, gain 0.34: as loud as the sine"), normalize=False)
```

```python {run continue echo=false}
# Check that the gain compensates: the square at 0.34 measures within 0.2 dB of the sine.
from euterpe.lint import lint_audio
from euterpe.sound import Sine, Square, render

sine, square = (lint_audio(render(u, 2.0)).value("A-LUFS") for u in (Sine(220.0) * 0.5, Square(220.0) * 0.34))
assert abs(sine - square) < 0.2, (sine, square)
```

The square still sounds brighter and buzzier than the sine, because it has harmonics the sine lacks (chapter 3). But neither one now stands out as louder. Matching loudness rather than peaks is how a mix keeps every part audible.

## Putting it all together

A *round* is a song sung by several voices that start the same tune at different times, each one entering when the one before it reaches the end of a line. *Frère Jacques* is the classic one: every 4 seconds (8 beats, one line of the song sung twice) a new voice enters, and the lines fit on top of each other. Here three voices sing it, each a different wave from the last section, and each gain comes from its loudness: the square at 0.34, as just measured, and the triangle, which measured 1.7 dB below the sine, at 0.5 × 10^(1.7/20) = 0.61. Those were measured at 220 Hz; the tune runs from 165 to 370 Hz, where the weighting changes the three by about the same amount.

```python {run continue name=finale}
from euterpe.sound import Square, Triangle

song = (play(lambda n: Sine(n.freq) * 0.5, notes(0))
        + play(lambda n: Triangle(n.freq) * 0.61, notes(4))
        + play(lambda n: Square(n.freq) * 0.34, notes(8)))
song.take(24.0, "Frère Jacques as a round: a sine, then a triangle, then a square")
```

Listen for each voice entering: the triangle sounds like a softer, rounder sine, and the square buzzes, but none of the three drowns the others, and their notes fit because all of them come from 220 × 2^(n/12). The voices still differ in more than loudness: why a square buzzes and a triangle does not is chapter 3.

## Summary

- Pitch follows the ratio of frequencies. A ratio of 2 is an octave, and notes an octave apart share a name.
- Equal temperament splits the octave into twelve semitones, each a ratio of 2^(1/12) ≈ 1.0595. A4 = 440 Hz, and a note n semitones above it has 440 × 2^(n/12) Hz. A semitone is 100 cents.
- Levels are measured in decibels, 20 × log₁₀ of an amplitude ratio. Half the amplitude is −6 dB; about −10 dB sounds half as loud. dBFS uses full scale as the reference.
- Loudness depends on frequency and shape, not only on the peak. LUFS estimates it by weighting the frequencies like the ear and averaging the power of the sounding parts.
- `lint_audio` measures peak, loudness and common mistakes such as clipping.
- `play` starts a sound for each note of a list, at its time; a tune is a list of steps.

## Exercises

1. In the first example, change `Square(1.0) * 110 + 330` so that the two tones are 440 Hz and 660 Hz. Their ratio is 3/2, an interval called a *fifth*. Then raise A4 by 7 steps in the semitone example: how far, in cents, is equal temperament's fifth from 660 Hz? Use the cents formula from the table of note names.
2. In the `lint_audio` example, change the gain from `0.25` to `0.1`. Predict `A-PEAK` and `A-LUFS` before you run it. Then try `2.0`: which rules fire, and with what severity?
3. In the example that matches the square to the sine (gain 0.34), replace `Square` with `Saw` and find the gain that makes it as loud as the sine, using the measurements of the four waves. Check your answer with `lint_audio`.

### Answers

1. `Square(1.0) * 110 + 550` alternates 660 and 440 Hz. Seven steps above A4 is 659.26 Hz, and `1200 * np.log2(660 / 659.26)` is about 1.94 cents: equal temperament's fifth is 2 cents narrow, too little for most listeners to hear.
2. At gain 0.1, `A-PEAK` is −20.0 dBFS, 8 dB below −12.0, and `A-LUFS` drops by the same 8 dB, to −23.7 LUFS. At gain 2.0 the samples reach 2, so `A-CLIP` fires as an error. Two warnings come with it: `A-TRUEPEAK`, the *true peak*, the highest point of the smooth wave playback draws between the samples (chapter 1), measured in dBTP and flagged above −1, and `A-TAIL`, which chapter 4 explains.
3. The saw measures −11.2 LUFS and the sine −10.0, so the saw needs about 1.2 dB more: 0.5 × 10^(1.2/20) ≈ 0.57. `Saw(220.0) * 0.57` measures −10.1 LUFS, within 0.1 dB of the sine.

```python {run echo=false}
# Level check: lint every sound in build/audio, this chapter's and any written before it.
# It prints nothing unless one has an error.
# A failure prints on the page as a block error; it stops the build only once scriptorium
# can refuse block errors.
from pathlib import Path

from euterpe.io import read
from euterpe.lint import lint_audio

failures = [
    f"{path.name}: {finding.message}"
    for path in sorted(Path("build/audio").glob("*.mp3"))
    for finding in lint_audio(*read(path)).errors
]
if failures:
    raise SystemExit("level check failed: " + "; ".join(failures))
```
