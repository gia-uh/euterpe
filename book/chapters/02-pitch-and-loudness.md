# Pitch and loudness

Chapter 1 described a sound as a list of numbers. This chapter connects two properties of those numbers to what you hear. Frequency becomes *pitch*, how high or low a note sounds. Amplitude becomes *loudness*. In both cases the ear does not follow the numbers themselves. It follows their ratios, and that is why music and audio measure both with logarithms.

## Octaves: pitch follows ratios

The sound below alternates between two sines, half a second each: 440 Hz, then 220 Hz. The frequency is a unit, as in the sweeps of chapter 1. `Square(1.0)` is +1 for half a second and −1 for the next half, so `Square(1.0) * 110 + 330` jumps between 440 and 220.

```python {run}
from euterpe.book import listen
from euterpe.sound import Sine, Square

listen(Sine(Square(1.0) * 110 + 330) * 0.5, 4.0, "440 Hz and 220 Hz in turn")
```

The two tones sound like the same note, one higher than the other. The higher one has exactly twice the frequency. This distance, a ratio of 2, is called an *octave*, and it is the reason the same note name repeats: every note shares its name with the notes at twice and half its frequency.

Now keep the difference the same, 220 Hz, but move up: 1 980 Hz and 1 760 Hz. Then keep the ratio instead: 3 520 Hz and 1 760 Hz.

```python {run}
from euterpe.book import listen
from euterpe.sound import Sine, Square

listen(Sine(Square(1.0) * 110 + 1_870) * 0.5, 4.0, "1 980 Hz and 1 760 Hz in turn: 220 Hz apart")
listen(Sine(Square(1.0) * 880 + 2_640) * 0.5, 4.0, "3 520 Hz and 1 760 Hz in turn: an octave")
```

The first pair is 220 Hz apart, like the octave above, but it sounds like a small step: its ratio is 1 980 / 1 760 = 1.125, close to what the next section calls two semitones (1.122). The second pair is 1 760 Hz apart and sounds like the same leap as 440 and 220. What the ear hears as the distance between two pitches is the ratio of their frequencies, not the difference. Equal ratios sound like equal steps, so pitch is the logarithm of frequency: each octave adds the same amount to the pitch, while the frequency doubles.

The plot shows the 88 keys of a piano, from the lowest (27.5 Hz) to the highest (4 186 Hz). On a linear axis the low half of the keyboard is squeezed against the bottom. On a logarithmic axis, where each doubling takes the same height, the keys lie on a straight line.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show

key = np.arange(1, 89)
freq = 440.0 * 2 ** ((key - 49) / 12)

fig, axes = plt.subplots(1, 2, figsize=(8, 3))
for ax, scale in zip(axes, ["linear", "log"]):
    ax.plot(key, freq, ".", markersize=3)
    ax.set_yscale(scale)
    ax.set_xlabel("piano key")
    ax.set_title(f"{scale} frequency axis")
axes[0].set_ylabel("frequency (Hz)")
show(fig, "The 88 piano keys: a doubling per octave, a straight line on a log axis")
```

## Twelve equal steps

Western music divides the octave into twelve steps. Each step is called a *semitone*, and two semitones make a *whole tone*. Twelve steps must multiply the frequency by 2, and each step should sound the same size, so each step multiplies the frequency by the same number r, with r to the twelfth power equal to 2. That number is the twelfth root of 2, `2 ** (1 / 12)` in Python, about 1.0595. Tuning every step to exactly this ratio is called *equal temperament*, and nearly all music you hear today uses it.

The steps need a fixed point to start from. The modern standard is A4 = 440 Hz: the note called A in octave 4, the sine at the top of chapter 1. Here is A4 raised by 0, 1, 2 and 12 steps:

```python {run}
from euterpe.book import listen
from euterpe.sound import Sine

semitone = 2 ** (1 / 12)
for steps in (0, 1, 2, 12):
    freq = 440.0 * semitone ** steps
    listen(Sine(freq) * 0.5, 1.5, f"A4 raised by {steps} steps: {freq:.2f} Hz")
```

One step is the smallest distance in most music: the two tones are clearly different, but close. Two steps sound like the step between neighbouring notes of a simple tune. Twelve steps land at 880 Hz, A5, one octave up.

The twelve notes of an octave have seven letter names, A to G, and five names with a sharp (♯, one step up) or a flat (♭, one step down). The same key can have two names: A♯ and B♭ are the same note in equal temperament. On a piano the seven letters are the white keys and the other five are the black keys. Here is one octave from A4, every frequency computed as 440 Hz times the ratio to the power of the number of steps:

```python {run echo=false}
names = ["A4", "A♯4 / B♭4", "B4", "C5", "C♯5 / D♭5", "D5", "D♯5 / E♭5", "E5", "F5", "F♯5 / G♭5", "G5", "G♯5 / A♭5", "A5"]
print("| steps above A4 | note | ratio to A4 | frequency (Hz) |")
print("|---:|:---|---:|---:|")
for k, name in enumerate(names):
    print(f"| {k} | {name} | {2 ** (k / 12):.4f} | {440 * 2 ** (k / 12):.2f} |")
```

The octave number goes up at C, not at A, for historical reasons: B4 is followed by C5. The C just below A4 is C4, called *middle C*, at 261.63 Hz, nine steps below A4. In general a note n steps above A4 has the frequency 440 × 2^(n/12), and n may be negative. MIDI, the standard for sending notes between instruments and programs, numbers the notes by semitone with A4 = 69 and middle C = 60. Musicians also split each semitone into 100 *cents*, to talk about notes that are slightly out of tune. So the MIDI note m has the frequency 440 × 2^((m − 69)/12), and one cent is a ratio of 2^(1/1200):

```python {run echo=false}
for m in (60, 69, 81):
    print(f"- MIDI note {m}: {440 * 2 ** ((m - 69) / 12):.2f} Hz")
print(f"- one cent: a ratio of {2 ** (1 / 1200):.6f}, a change of 0.058 %")
```

## Amplitude and decibels

The amplitude of a sound is how far its samples swing from 0. Loudness follows amplitude in the same way pitch follows frequency: by ratios. Halving the amplitude sounds like the same drop whether you start loud or quiet. So levels are measured on a logarithmic scale, in *decibels* (dB). The level of an amplitude a against a reference a₀ is

20 × log₁₀(a / a₀) dB.

Audio software takes full scale, 1.0, as the reference, and writes the result as dBFS, decibels relative to full scale. Full scale is 0 dBFS, and every level below it is negative. Halving the amplitude gives 20 × log₁₀(0.5) = −6.02 dB, which is why "−6 dB" means "half". Each further halving takes another 6 dB away:

```python {run}
from euterpe.book import listen
from euterpe.sound import Sine

for gain in (0.5, 0.25, 0.125, 0.0625):
    listen(Sine(440.0) * gain, 1.5, f"The 440 Hz sine at gain {gain}")
```

Each player is 6 dB quieter than the one before it, and each drop sounds about as large as the last. The table gives a few more levels:

```python {run echo=false}
import math

print("| amplitude | level (dBFS) |")
print("|---:|---:|")
for a in (1.0, 0.5, 0.25, 0.1, 0.01, 0.001):
    print(f"| {a:g} | {20 * math.log10(a):.2f} |")
```

A tenth of the amplitude is −20 dB, a thousandth is −60 dB. Why 20 and not 10? The decibel was defined for power, as 10 × log₁₀ of a power ratio, and the power a wave carries grows with the square of its amplitude. Squaring inside a logarithm doubles it, so the factor for amplitudes is 20. Half the amplitude is a quarter of the power, and both are −6 dB.

Your ear covers a huge range of levels. The quietest sound you can hear and the loudest you can bear differ by about 120 dB, a factor of a million in amplitude. On that scale a step of 1 dB is about the smallest change in level most people notice, and a sound must rise by about 10 dB, three times the amplitude, before it sounds twice as loud.

### Measuring a sound

Euterpe's `lint_audio` measures rendered samples and reports what it finds, one line per finding. Here is the report for two seconds of the 440 Hz sine at gain 0.25:

```python {run output=code}
from euterpe.lint import lint_audio
from euterpe.sound import Sine, render

report = lint_audio(render(Sine(440.0) * 0.25, 2.0))
print(report.to_text())
```

Each line has a severity, a rule and a message. A `metric` is a measurement, a `warn` is something that may be a mistake, and an `error` is a mistake: samples clipped at full scale. `A-PEAK` is the sample peak, −12.0 dBFS for a gain of 0.25. `A-TAIL` warns that the sound is still going when the samples end: the file stops in the middle of the note. Chapter 4 adds envelopes that end a sound smoothly. `A-BALANCE` splits the energy into three bands; a 440 Hz sine has all of its energy in the middle one. The remaining line, `A-LUFS`, is a measure of loudness, the subject of the next section.

The same report is printed by the `euterpe` command, for an audio file (`euterpe lint tone.mp3`) or for a Python function that returns a unit (`euterpe lint piece.py:tone --seconds 2`). It exits with status 1 when the report has an error, so a script or a test can stop on a clipped sound.

## Loudness is not level

Two sounds with the same peak do not always sound equally loud. Here are four sines, each at gain 0.5, so each peaks at −6 dBFS: 100 Hz, 1 000 Hz, 3 000 Hz and 12 000 Hz.

```python {run}
from euterpe.book import listen
from euterpe.sound import Sine

for freq in (100.0, 1_000.0, 3_000.0, 12_000.0):
    listen(Sine(freq) * 0.5, 1.5, f"A {freq:.0f} Hz sine at gain 0.5")
```

On most loudspeakers and headphones the 3 000 Hz sine sounds the loudest and the 100 Hz sine much quieter, although their samples swing equally far. The ear is most sensitive between about 2 000 and 5 000 Hz, where the ear canal resonates, and grows less sensitive towards low frequencies, and again above about 10 000 Hz. (Small loudspeakers also play 100 Hz weakly, which adds to the effect.)

*Loudness* is how loud a sound seems, and it can be estimated from the samples. The standard method, ITU-R BS.1770, weights the frequencies with a filter called K-weighting: a high-pass filter cuts frequencies below about 40 Hz, and a shelf raises everything above about 2 000 Hz by up to 4 dB. Then it averages the power over blocks of 400 milliseconds, each overlapping the next by 75 %, and leaves out quiet blocks in two passes. First every block below −70 LUFS goes. Then every block more than 10 loudness units below the average of the remaining blocks goes, and the average of what is left is the result. So the silence between two notes does not lower a sound's loudness. The result is in *LUFS*, loudness units relative to full scale, where one loudness unit is one decibel. `A-LUFS` is this measurement. Here it is for a sine at gain 0.5, at frequencies across the range of hearing:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.lint import lint_audio
from euterpe.sound import Sine, render

freqs = np.geomspace(20, 20_000, 31)
lufs = [next(f.value for f in lint_audio(render(Sine(float(hz)) * 0.5, 1.0)).findings if f.rule == "A-LUFS") for hz in freqs]

fig, ax = plt.subplots(figsize=(7, 2.8))
ax.semilogx(freqs, lufs, "o-", markersize=3)
ax.axhline(-6.02, color="grey", linewidth=0.5)
ax.text(25, -5.6, "sample peak, −6 dBFS", fontsize=8, color="grey")
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("loudness (LUFS)")
show(fig, "The loudness of a sine at gain 0.5, by frequency, as A-LUFS measures it")
```

The measurement follows the ear at the bottom: a 100 Hz sine measures about 2 dB quieter than a 1 000 Hz one, and a 30 Hz sine 9 dB quieter. It does not follow the ear at the top: a 12 000 Hz sine measures as loud as a 3 000 Hz one, but it sounds quieter, and to many adults not at all. LUFS was designed for music and speech, which carry most of their energy below 5 000 Hz, and for those it agrees well with listeners. Broadcasters use it to keep programmes at the same loudness: the European broadcast standard, EBU R 128, sets every programme to −23 LUFS.

### The same peak, different shapes

The shape of a wave changes its loudness too. Here are four basic waveforms, `Sine`, `Triangle`, `Square` and `Saw`, at 220 Hz, all at gain 0.5, all peaking at −6 dBFS. A triangle rises and falls in straight lines. A saw rises in a straight line and drops back at once, as in chapter 1. A square jumps between its high and its low value and stays at each for half a cycle. Chapter 3 looks at their shapes and what they contain.

```python {run}
from euterpe.book import listen
from euterpe.sound import Saw, Sine, Square, Triangle

for wave in (Sine, Triangle, Square, Saw):
    listen(wave(220.0) * 0.5, 1.5, f"{wave.__name__} at 220 Hz, gain 0.5")
```

The square sounds the loudest. It spends almost all of its time at +0.5 or −0.5, so it carries more power than the others, which pass through the values in between. The table measures each one. *RMS*, the root of the mean of the squared samples, is the average power expressed as an amplitude, in dBFS. A square's samples are all at its peak, so its RMS equals its peak. A sine's RMS is its peak divided by √2, 3 dB lower. A triangle's and a saw's are the peak divided by √3, 4.8 dB lower, because they pass evenly through every value from −peak to +peak:

```python {run echo=false}
import numpy as np

from euterpe.lint import lint_audio
from euterpe.sound import Saw, Sine, Square, Triangle, render

print("| wave | peak (dBFS) | RMS (dBFS) | loudness (LUFS) |")
print("|:---|---:|---:|---:|")
for wave in (Sine, Triangle, Square, Saw):
    x = render(wave(220.0) * 0.5, 2.0)
    v = {f.rule: f.value for f in lint_audio(x).findings}
    rms = 20 * np.log10(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
    print(f"| {wave.__name__} | {v['A-PEAK']:.1f} | {rms:.1f} | {v['A-LUFS']:.1f} |")
```

The peaks are equal to within 0.1 dB, and the loudness spans 5 dB: the square measures −6.6 LUFS, the triangle −11.7. The saw has about the same RMS as the triangle but measures 0.5 dB louder, because more of its energy sits at high harmonics, which K-weighting raises. To make the square as loud as the sine, lower it by the difference, 3.4 dB. That is a gain of 10^(−3.4/20) = 0.68 on top of the 0.5, so about 0.34:

```python {run}
from euterpe.book import listen
from euterpe.sound import Sine, Square

listen(Sine(220.0) * 0.5, 1.5, "Sine at 220 Hz, gain 0.5")
listen(Square(220.0) * 0.34, 1.5, "Square at 220 Hz, gain 0.34: as loud as the sine")
```

```python {run echo=false}
from euterpe.lint import lint_audio
from euterpe.sound import Sine, Square, render

def lufs(unit):
    return next(f.value for f in lint_audio(render(unit, 2.0)).findings if f.rule == "A-LUFS")

print(f"The sine measures {lufs(Sine(220.0) * 0.5):.1f} LUFS and the square {lufs(Square(220.0) * 0.34):.1f} LUFS.")
```

The square still sounds brighter and buzzier than the sine, because it has harmonics the sine lacks (chapter 3). But neither one now stands out as louder. Matching loudness rather than peaks is what a mix does to keep every part audible (milestone 4 of Euterpe builds a mixer on it).

## Summary

- Pitch follows the ratio of frequencies. A ratio of 2 is an octave, and notes an octave apart share a name.
- Equal temperament splits the octave into twelve semitones, each a ratio of 2^(1/12) ≈ 1.0595. A4 = 440 Hz, and a note n semitones above it has 440 × 2^(n/12) Hz.
- Levels are measured in decibels, 20 × log₁₀ of an amplitude ratio. Half the amplitude is −6 dB, a tenth is −20 dB. dBFS uses full scale as the reference.
- Loudness depends on frequency and shape, not only on the peak. LUFS estimates it with a frequency weighting and a power average.
- `lint_audio` measures peak, loudness and common mistakes, and `euterpe lint` does the same from the shell.

## Exercises

1. In the first example, change `Square(1.0) * 110 + 330` so that the two tones are 440 Hz and 660 Hz. Their ratio is 3/2, an interval called a *fifth*. Then raise A4 by 7 steps in the semitone example: how far is equal temperament's fifth from 660 Hz?
2. In the `lint_audio` example, change the gain from `0.25` to `0.1`. Predict `A-PEAK` and `A-LUFS` before you run it. Then try `2.0`: which rule fires, and with what severity?
3. In the last example, replace `Square` with `Saw` and find the gain that makes it as loud as the sine, using the table of the four waves. Check your answer with `lint_audio`.

```python {run echo=false}
# Level check: lint every sound in build/audio, this chapter's and any written before it.
# It prints nothing unless one has an error.
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
