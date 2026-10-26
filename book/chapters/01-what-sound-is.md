# What sound is

A sound is a change in air pressure that reaches your ear. This chapter follows that change from the air into a computer: how it is measured, how many numbers a second of sound takes, what goes wrong when there are too few, and how coarse each number can be before you hear it.

## Pressure over time

Air at sea level presses on everything with about 101 325 pascals. A sound is a small, fast change on top of that value. Ordinary speech moves the pressure at your ear by about 0.02 pascals, two parts in ten million. The change travels away from its source at about 343 metres per second, at room temperature.

Your eardrum moves with the pressure, and the inner ear turns that motion into nerve signals. So a sound, for our purposes, is one number that changes over time: the pressure at one point. A microphone measures that number, a loudspeaker produces it, and a program can compute it.

The simplest sound repeats one shape forever. The shape is a sine wave, and the number of times it repeats each second is its frequency, measured in hertz (Hz). Here is a sine wave at 440 Hz, two seconds long, at half of full scale (full scale is the largest value a sound file can hold).

Euterpe calls anything that produces samples of sound a *unit*. `Sine(440.0)` is a unit. `Sine(440.0) * 0.5` builds a new unit that takes each value of the sine and multiplies it by 0.5; in the same way `a + b` builds a unit that adds two units value by value, and a plain number on either side counts as a constant. Building units computes nothing yet. `listen` asks the top unit for two seconds of sound, the top unit asks the sine, and a player appears on this page.

```python {run}
from euterpe.book import listen
from euterpe.sound import Sine

tone = Sine(440.0) * 0.5
listen(tone, 2.0, "A sine wave at 440 Hz")
```

`listen` is a helper for this book, which is why it lives in `euterpe.book` and not in the library proper, `euterpe.sound`. It writes an MP3 file under `build/audio/` in the current directory and prints a line that the book turns into a player. Run in your own terminal, it leaves that file for you to open in any audio player. To choose the file name yourself, use the library's `render(tone, 2.0, to="tone.wav")`.

A tone held at one steady frequency in a piece of music is a *note*. This one is the note musicians call A, the one orchestras tune to (chapter 2 explains note names). A sine is the plainest tone there is: it sounds like a tuning fork or a soft whistle. Every other sound in this book is built from sines, or analysed as a sum of them, so it is worth knowing well.

One cycle at 440 Hz lasts 1/440 of a second, about 2.27 milliseconds. In that time the sound travels 343 / 440 = 0.78 metres, which is the length of one wave in the air. Here are the first 5 milliseconds as a plot:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import RATE, Sine, render

x = render(Sine(440.0) * 0.5, 0.005)
ms = np.arange(len(x)) / RATE * 1000

fig, ax = plt.subplots(figsize=(7, 2.5))
ax.plot(ms, x)
ax.set_xlabel("time (ms)")
ax.set_ylabel("pressure (full scale = 1)")
ax.axhline(0, color="grey", linewidth=0.5)
show(fig, "The first 5 ms of the 440 Hz sine: a little over two cycles")
```

The vertical axis is not in pascals. Inside a computer a sound is a number between −1 and 1, and the loudspeaker and its volume knob decide how many pascals that becomes. That is why a value of 1 is called *full scale*: it means the most the file can hold, not a pressure. The sine above reaches 0.5, half of full scale.

## Samples

A computer cannot store a smooth curve. It stores the value of the curve at regular moments, and each stored value is a *sample*. Euterpe takes 48 000 samples every second; this number is the *sample rate*. Audio CDs use 44 100 and video uses 48 000. `render` returns the samples as a numpy array:

```python {run output=code}
from euterpe.sound import Sine, render

x = render(Sine(440.0) * 0.5, 2.0)
print(len(x), "samples,", x.nbytes, "bytes, type", x.dtype)
print(x[:8])
```

Each sample is a 32-bit float (`float32`), 4 bytes, so two seconds take 384 kilobytes. Sample number n is taken at time n / 48 000 seconds, so a sine of amplitude A and frequency f gives the samples

x[n] = A · sin(2π · f · n / 48 000)

where the angle is in radians and 2π is one full cycle. At n = 0 the sine is 0 and rising. numpy computes the same eight values from the formula:

```python {run continue output=code}
import numpy as np

n = np.arange(8)
print(0.5 * np.sin(2 * np.pi * 440.0 * n / 48_000))
```

The last digit can differ, because a 32-bit float keeps only about 7 significant digits and numpy computes here with 64-bit floats.

Between two samples there is nothing: the file does not say what the pressure was in between. Zoomed in to the first millisecond, the dots are all that is stored.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import RATE, Sine, render

x = render(Sine(440.0) * 0.5, 0.001)
ms = np.arange(len(x)) / RATE * 1000
fine = np.linspace(0, 1, 1000)

fig, ax = plt.subplots(figsize=(7, 2.5))
ax.plot(fine, 0.5 * np.sin(2 * np.pi * 440 * fine / 1000), color="lightgrey", label="the pressure")
ax.plot(ms, x, "o", markersize=3, label="the samples")
ax.set_xlabel("time (ms)")
ax.legend(loc="lower right")
show(fig, "The first millisecond: 48 samples of the 440 Hz sine")
```

At 440 Hz there are 48 000 / 440, about 109 samples per cycle. The minimum is a little more than 2 samples per cycle, and the next section shows why. Below that, the samples no longer pin down the wave.

## The Nyquist limit

Take a sine at some frequency f and a second sine at 48 000 − f. Put the second one into the formula:

sin(2π · (48 000 − f) · n / 48 000) = sin(2π · n − 2π · f · n / 48 000)

Two facts finish the argument. First, a sine repeats every full cycle, sin(x + 2π) = sin(x), and n is a whole number, so taking away 2π · n changes nothing. Second, a sine run backwards is the same shape upside down: sin(−x) = −sin(x). Together:

sin(2π · (48 000 − f) · n / 48 000) = −sin(2π · f · n / 48 000)

The samples of the sine at 48 000 − f are the samples of the sine at f, upside down. An upside-down sine is the same sine shifted by half a cycle, so it sounds the same, and after sampling the two frequencies cannot be told apart.

With numbers: a sine at 44 000 Hz advances 44/48 of a cycle from one sample to the next. Since a full cycle brings it back to where it was, 44/48 of a cycle forward lands on the same point as 4/48 of a cycle backward, and 4/48 of a cycle per sample is what a 4 000 Hz sine advances. Going backward through a sine traces it upside down, so the 44 000 Hz samples are the 4 000 Hz samples with the sign flipped. Comparing the two, one millisecond of samples:

```python {run output=code}
import numpy as np

n = np.arange(48)  # one millisecond of sample numbers
high = np.sin(2 * np.pi * 44_000 * n / 48_000)
low = np.sin(2 * np.pi * 4_000 * n / 48_000)
print(np.abs(high + low).max())  # largest difference from the upside-down 4 000 Hz samples
```

The difference is rounding error in the last digits of the floats: the samples are the same, with the sign flipped. In the plot, the thin line is the 44 000 Hz wave and the thick one is the 4 000 Hz wave turned upside down; the samples, the dots, lie on both.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show

ms = np.linspace(0, 0.5, 4000)
n = np.arange(25)

fig, ax = plt.subplots(figsize=(7, 2.5))
ax.plot(ms, np.sin(2 * np.pi * 44_000 * ms / 1000), color="lightgrey", linewidth=0.7, label="44 000 Hz")
ax.plot(ms, -np.sin(2 * np.pi * 4_000 * ms / 1000), linewidth=2, label="4 000 Hz, upside down")
ax.plot(n / 48, np.sin(2 * np.pi * 44_000 * n / 48_000), "o", markersize=4, label="the samples")
ax.set_xlabel("time (ms)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=3, fontsize=8)
show(fig, "Half a millisecond: a 44 000 Hz sine and a 4 000 Hz sine share their samples")
```

So every set of samples has two readings, f and 48 000 − f. As f rises from 0 to 48 000, its partner 48 000 − f falls from 48 000 to 0, and the two meet at 24 000 Hz. Below 24 000 Hz each reading is the lower one of its pair. That midpoint, half the sample rate, is the *Nyquist frequency*, and the frequencies below it are the ones sampling at 48 000 Hz can represent. A wave above it does not disappear: its samples are exactly those of its partner below, so it *folds back* to a lower frequency. This is called *aliasing*.

In samples per cycle, the rule is the same. A frequency f gets 48 000 / f samples per cycle, and f below 24 000 means more than 2 samples per cycle. Exactly 2 is not enough: a sine at 24 000 Hz is sampled at sin(π · n), which is 0 for every whole n, so its samples are all zeros.

Adding 48 000 Hz to a frequency adds exactly one cycle per sample, which also changes nothing. Putting both facts together, a frequency f above the Nyquist frequency lands at the distance from f to the nearest multiple of 48 000: 44 000 Hz lands at 4 000 Hz, 50 000 Hz at 2 000 Hz.

### What playback puts between the samples

If 44 000 Hz and 4 000 Hz have the same samples, why does a loudspeaker play 4 000 Hz? Because of what the sound card does between the samples. Its converter turns the list of samples into a voltage that varies smoothly, and it draws the one smooth wave through the samples that contains nothing above 24 000 Hz. It does that with a *filter*, a process that weakens some frequencies and keeps others: this one keeps everything below 24 000 Hz and removes everything above. Through the samples of the 44 000 Hz sine, the only wave below 24 000 Hz is the 4 000 Hz one, upside down, so that is what you hear.

This does not contradict "between two samples there is nothing". The file stores nothing there. Playback fills the gaps under one assumption: the sound had nothing above half the sample rate. When that holds, the fill is exact and the original wave comes back; this is the Nyquist–Shannon sampling theorem. When it does not hold, playback assumes it anyway, and a wave above the limit comes out as its partner below. Real converters come close to this ideal filter, not all the way.

Euterpe's oscillators guard against this at the source: asked for a frequency at or above 24 000 Hz, they output silence. The check is on the frequency you pass in and nothing else. `Saw(10_000.0)` is allowed, although most of what it contains lies above 24 000 Hz, as the next section shows.

### Why a saw wave folds back

A sine has one frequency, so it is easy to keep below the limit. Most sounds are not sines. A *saw wave* rises steadily from −1 to 1 and then drops back at once, once per cycle. Chapter 3 shows that such a wave is a sum of sines at every whole multiple of its frequency, called its *harmonics*: harmonic k is at k times the frequency and has 1/k of the first one's amplitude. A 10 000 Hz saw contains 10 000 Hz at amplitude 1, 20 000 Hz at 1/2, 30 000 Hz at 1/3, and so on without end. The first harmonic is the frequency you hear as the note.

Every harmonic above 24 000 Hz folds back. Here is the rule from the last section as a function, applied to the first seven harmonics of the 10 000 Hz saw:

```python {run output=code}
def fold(f, rate=48_000):
    """Where a frequency f lands after sampling at rate: its distance to the nearest multiple of rate."""
    return abs((f + rate / 2) % rate - rate / 2)

for k in range(1, 8):
    print(f"harmonic {k}: {10_000 * k:>6} Hz, heard at {fold(10_000 * k):>6.0f} Hz")
```

Adding `rate / 2` before the remainder `%` and taking it away after gives the signed distance from f to the nearest multiple of `rate`, between −24 000 and 24 000. `abs` drops the sign, which only turns the sine upside down.

The 5th harmonic, 50 000 Hz, is heard at 2 000 Hz, far below the note itself. A folded harmonic does not sit at a multiple of the note's frequency, so it does not blend into the note's tone. It sounds like a separate whistle that does not belong to the note.

Why does a saw have harmonics so far up? Because of the drop. A sine of amplitude A and frequency f changes at most by 2π · f · A per second, as it crosses zero. A sum of sines can change fast only if some of its sines change fast, and only high frequencies do. So the sharper a jump, the higher the frequencies it needs, and a drop that takes no time at all needs harmonics without end. A drop spread over a short time needs much less above about one divided by that time. Spread over two samples, 1/24 000 of a second, it needs much less above roughly 24 000 Hz, which is exactly what must not be there.

To hear the difference, Euterpe's `Saw` can be told to skip its correction. With `antialias=False` it computes the wave the direct way: take the position in the cycle, from 0 to 1, and scale it to run from −1 to 1, with the drop in a single sample. The normal `Saw` smooths each drop over two samples with a correction called *polyBLEP*. A BLEP, a band-limited step, is the shape a jump takes when it is *band-limited*: when it contains nothing above a limit, here 24 000 Hz. polyBLEP approximates that shape with a short polynomial, two samples wide, added at each drop, so much less is left above 24 000 Hz to fold.

Both saws below sweep from 1 000 Hz up to 23 000 Hz in four seconds. Their frequency is not a number but a unit: a parameter may be either, and a saw given a unit reads its frequency from it again at every sample. The unit is half a cycle of a slow sine. `Sine(0.125)` completes one cycle every 8 seconds, so in 4 seconds it covers half a cycle. `phase` is measured in cycles, from 0 to 1, and sets where the sine starts: at phase 0 it starts at 0 and rises, and at phase 0.75 it starts three quarters through its cycle, at its lowest value, −1. Over the next half cycle it rises to 1. Times 11 000, that runs from −11 000 to 11 000; plus 12 000, from 1 000 to 23 000.

```python {run}
from euterpe.book import listen
from euterpe.sound import Saw, Sine

sweep = Sine(0.125, phase=0.75) * 11_000 + 12_000      # 1 000 Hz to 23 000 Hz in 4 s

listen(Saw(sweep) * 0.5, 4.0, "A saw sweeping from 1 to 23 kHz, band-limited")
listen(Saw(sweep, antialias=False) * 0.5, 4.0, "The same sweep without the correction: aliasing")
```

Listen to the first sweep: one tone rises until it is too high to hear. Most adults stop hearing somewhere between 15 000 and 20 000 Hz, so the end of it may sound like silence. The players on this page also play MP3 files, a compressed format that discards what listeners hear least; the encoder used here removes everything above about 20 500 Hz. In the second sweep, other tones move down while the note moves up, and they stay audible after the note itself is gone. Those are folded harmonics. Both sweeps also start with a click: the wave jumps from silence to −0.5 in one sample, and a jump that sharp is a burst of high frequencies, like the saw's drop. Chapter 4 is about starting a sound smoothly.

A *spectrogram* shows the same thing as a picture. It cuts the sound into slices of 1 024 samples, about 21 ms each, measures how strong each frequency is in each slice, and draws one column per slice. Time runs left to right, frequency bottom to top, and brightness is the strength:

```python {run echo=false}
import matplotlib.pyplot as plt

from euterpe.book import show
from euterpe.sound import RATE, Saw, Sine, render

def sweep():
    return Sine(0.125, phase=0.75) * 11_000 + 12_000

fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True, dpi=60)
for ax, (title, unit) in zip(axes, [("Saw", Saw(sweep())), ("Saw, antialias=False", Saw(sweep(), antialias=False))]):
    ax.specgram(render(unit * 0.5, 4.0), NFFT=1024, Fs=RATE, noverlap=0, vmin=-90, cmap="magma")
    ax.set_title(title)
    ax.set_xlabel("time (s)")
axes[0].set_ylabel("frequency (Hz)")
show(fig, "The two sweeps: harmonics fold back from 24 kHz without the correction")
```

In the right panel each harmonic reaches the top edge, 24 000 Hz, and comes back down as a falling line. Those falling lines are the extra tones you heard. The left panel has them too, much fainter: polyBLEP reduces aliasing, it does not remove it.

To put numbers on it, measure energy. The *energy* of a stretch of sound is the sum of the squares of its samples, so it grows with the square of the amplitude. A *Fourier transform* splits a stretch of sound into sines. numpy's `np.fft.rfft` computes it: for one second of samples it returns one number for each whole frequency, 0, 1, 2 … 24 000 Hz, and the square of its size is proportional to the energy at that frequency (chapter 3 explains how it works). Multiplying by `np.hanning` first fades the second in and out, because the cut at each end is a sharp jump of its own and would add frequencies. The fade smears each sine over a few neighbouring frequencies, so anything within 20 Hz of a harmonic counts as that harmonic.

The block takes one second of each saw at a steady 3 300 Hz and measures which share of the energy is not at a harmonic of 3 300 Hz, that is, in folded tones. At 3 300 Hz the harmonics from the 8th, 26 400 Hz, are above 24 000 Hz and fold. And 48 000 is not a multiple of 3 300, so folded harmonics land between the real ones, where the measurement can tell them apart; a 3 000 Hz saw would fold every harmonic exactly onto another harmonic. The share is split at 12 000 Hz because hearing is most sensitive between about 1 000 and 5 000 Hz and weakens towards 20 000 Hz.

```python {run output=code}
import numpy as np

from euterpe.sound import Saw, render

def folded_share(unit, f, lo, hi):
    """The share of one second's energy that lies between lo and hi Hz, away from every harmonic of f."""
    x = render(unit, 1.0)
    energy = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2  # at 0, 1, 2 ... 24 000 Hz
    hz = np.arange(len(energy))
    folded = np.abs(hz - f * np.round(hz / f)) > 20  # more than 20 Hz from every multiple of f
    band = (hz >= lo) & (hz < hi)
    return energy[folded & band].sum() / energy.sum()

for name, saw in [("Saw", Saw(3_300.0)), ("Saw, antialias=False", Saw(3_300.0, antialias=False))]:
    below, above = folded_share(saw, 3_300.0, 0, 12_000), folded_share(saw, 3_300.0, 12_000, 24_000)
    print(f"{name}: {100 * below:.4f} % folded below 12 000 Hz, {100 * above:.3f} % above")
```

Below 12 000 Hz the direct saw puts 3.8 % of its energy into folded tones. Energy goes with the square of the amplitude, so that is as much as a tone at about a fifth of the saw's amplitude would carry (the square root of 0.038 is 0.19): anyone hears it. polyBLEP leaves about 660 times less there, 0.0057 %, the energy of tones below a hundredth of the amplitude. Above 12 000 Hz the reduction is far smaller, about 22 times, because a correction two samples wide cannot act sharply near the Nyquist frequency.

Better methods exist and cost more computation. One is *oversampling*: compute the wave at several times the sample rate, filter out everything above 24 000 Hz, and only then keep one sample in every few. For the notes of real music polyBLEP is enough. Most notes sit far below 3 300 Hz (the highest key of a piano is about 4 186 Hz), and the lower the note, the later the harmonic at which folding starts; harmonic k has 1/k of the amplitude, so what folds is quieter.

## How fine each sample is

Each sample is a number, and a file stores it with a fixed number of bits. With b bits a sample can take 2 to the power b different values (`2 ** b` in Python). CD audio uses 16 bits, 65 536 values. Rounding every sample to the nearest allowed value is called *quantisation*. The rounding error, the difference between the exact value and the rounded one, is a small signal added to the sound. It is never more than half the step between two neighbouring values. Each bit removed halves the number of values, so it doubles the step and the largest error. At 16 bits the largest error is about 1/65 000 of full scale, too quiet to hear in normal listening, which is why 16 bits was enough for the CD.

A 32-bit float is finite too, so the samples Euterpe computes are already quantised. A `float32` keeps 24 significant bits; between 0.5 and 1 its step is 2 to the power −24, about 0.00000006, and it gets finer closer to 0. When `render(..., to="tone.wav")` writes a WAV file, an uncompressed file of samples, it stores 24-bit integers: each sample is multiplied by about 8 388 608 (`2 ** 23`), rounded to a whole number and stored in 3 bytes. The step is then 1/8 388 608 of full scale, far below hearing.

`BitCrush` rounds each sample to `2 ** bits - 1` levels spread evenly between −1 and 1. That is one level fewer than the bits allow, so that the levels are symmetric and 0 is one of them: silence stays silent. Here is the 440 Hz sine with 16, 6, 4 and 2 bits:

```python {run}
from euterpe.book import listen
from euterpe.sound import BitCrush, Sine

for bits in (16, 6, 4, 2):
    listen(BitCrush(Sine(440.0), bits=bits) * 0.5, 2.0, f"The 440 Hz sine with {bits} bits")
```

`BitCrush` acts on the full-scale sine, and `* 0.5` scales after. The order matters, because the levels stay between −1 and 1 whatever the input. At 2 bits they are −1, 0 and 1, and every sample of a half-scale sine is nearer to 0 than to either end: `BitCrush(Sine(440.0) * 0.5, bits=2)` rounds every sample to 0 and plays silence. Crushing first uses all the levels; scaling after turns them into −0.5, 0 and 0.5.

At 16 bits it sounds like the sine at the top of the chapter. At 6 bits a faint hiss sits under the tone. At 4 bits the tone is harsh, and at 2 bits the wave jumps between −0.5, 0 and 0.5 and sounds close to a *square wave*, a wave that jumps between two values and spends half of each cycle at each. The plot shows one cycle of each, before the scaling:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import RATE, BitCrush, Sine, render

fig, ax = plt.subplots(figsize=(7, 3))
for bits in (16, 4, 2):
    x = render(BitCrush(Sine(440.0), bits=bits), 1 / 440)
    ax.plot(np.arange(len(x)) / RATE * 1000, x, label=f"{bits} bits")
ax.set_xlabel("time (ms)")
ax.legend(loc="lower left")
show(fig, "One cycle of the 440 Hz sine with 16, 4 and 2 bits")
```

Rounding changes the shape of the wave, so it adds frequencies that were not there. What they sound like depends on how large the error is next to the wave. At 6 bits there are 63 levels and the error is a small wiggle: each sample's error depends on where it falls between two levels, and that changes erratically from one sample to the next. Its energy spreads thinly over many frequencies. A sound with energy spread over many frequencies and no clear pitch is heard as *hiss*, like a radio tuned between stations. At 2 bits the error is as large as the wave itself, and it repeats, almost exactly, with every cycle of the tone: the samples switch level at the same points of each cycle. A shape that repeats 440 times a second is made of harmonics of 440 Hz, and its sharp jumps make them strong far up. That is heard as a *buzz*, a harsh tone at the note's own pitch, not as hiss.

## Summary

- A sound is air pressure that changes over time. In a computer it is a list of numbers between −1 and 1, the samples.
- Euterpe takes 48 000 samples per second. Between two samples nothing is stored; playback fills the gaps with the smooth wave that has nothing above half the sample rate.
- A sine at f and one at 48 000 − f have the same samples, upside down. So the highest frequency a sample rate can hold is half of it, the Nyquist frequency, 24 000 Hz here: more than two samples per cycle. A higher frequency folds back to a lower one.
- A sharp jump needs high frequencies. A saw's drop gives it harmonics far above its own frequency, and without band-limiting they fold back as tones that do not belong to the note.
- Each sample is rounded to a finite number of levels. Fewer bits mean a larger rounding error: a hiss when the error is small, a buzz when it is as large as the wave.

## Exercises

1. In the first example, change `440.0` to `220.0`, then to `880.0`. Each doubling of the frequency sounds like the same note, only higher. Chapter 2 calls a doubling an octave.
2. In the folding example, change `10_000` to `9_000` in both places and `range(1, 8)` to `range(1, 11)`, for the first ten harmonics of a 9 000 Hz saw. Ten is enough: the 10th has a tenth of the first one's amplitude, and those after it are quieter still. Which of the ten land below 9 000 Hz, the note itself? Then, in the sweep example, change `11_000 + 12_000` to `4_000 + 5_000`, a sweep from 1 000 to 9 000 Hz, and listen to the saw with `antialias=False`: do falling tones remain?
3. In the `BitCrush` example, change `bits=bits` to `bits=bits, downsample=8` and listen. `BitCrush` now keeps every 8th sample and repeats it for the next 7, so only 6 000 different values remain each second: in effect a sample rate of 6 000 Hz, with a Nyquist frequency of 3 000 Hz. The 440 Hz tone survives, but the staircase of repeated samples has a sharp step 6 000 times a second, and those steps add the frequencies that share the tone's samples at a 6 000 Hz rate: 6 000 − 440 and 6 000 + 440 Hz, and the same around 12 000 Hz, 18 000 Hz and so on. It is folding seen from the other side. Then replace `Sine` with `Saw`, in the import line too. The saw's 7th harmonic, 3 080 Hz, is now above the Nyquist frequency: where does it land? Compute `fold(3_080, rate=6_000)` with the function from the folding example, then do the same for the 13th harmonic, 5 720 Hz. Are the results multiples of 440 Hz?

```python {run echo=false}
# Level check: every sound this chapter plays stays below full scale.
from pathlib import Path

import numpy as np

from euterpe.io import read

# Replaced by lint_audio from chapter 2 on. A failure prints on the page as a block error;
# it stops the build only once scriptorium can refuse block errors.
failures = []
for path in sorted(Path("build/audio").glob("*.mp3")):
    x, rate = read(path)
    peak = float(np.abs(x).max())
    if rate != 48_000 or peak >= 0.999:
        failures.append(f"{path.name} has peak {peak:.3f} at {rate} Hz")
if failures:
    raise SystemExit("level check failed: " + "; ".join(failures))
```
