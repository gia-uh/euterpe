# What sound is

A sound is a change in air pressure that reaches your ear. This chapter follows that change from the air into a computer: how it is measured, how many numbers a second of sound takes, what goes wrong when there are too few, and how coarse each number can be before you hear it.

## Pressure over time

Air at sea level presses on everything with about 101 325 pascals. A sound is a small, fast change on top of that value. Ordinary speech moves the pressure at your ear by about 0.02 pascals, two parts in ten million. The change travels away from its source at about 343 metres per second, at room temperature.

Your eardrum moves with the pressure, and the inner ear turns that motion into nerve signals. So a sound, for our purposes, is one number that changes over time: the pressure at one point. A microphone measures that number, a loudspeaker produces it, and a program can compute it.

The simplest sound repeats one shape forever. The shape is a sine wave, and the number of times it repeats each second is its frequency, measured in hertz (Hz). Here is a sine wave at 440 Hz, two seconds long, at half of full volume. Euterpe calls a sound source a *unit*: `Sine(440.0)` is one, `* 0.5` scales it, and `listen` renders it to a file and puts a player on this page.

```python {run}
from euterpe.book import listen
from euterpe.sound import Sine

tone = Sine(440.0) * 0.5
listen(tone, 2.0, "01-sine-440", "A sine wave at 440 Hz", id="sine-440")
```

This is the A that orchestras tune to. A sine is the plainest tone there is: it sounds like a tuning fork or a soft whistle. Every other sound in this book is built from sines, or analysed as a sum of them, so it is worth knowing well.

One cycle at 440 Hz lasts 1/440 of a second, about 2.27 milliseconds. In that time the sound travels 343 / 440 = 0.78 metres, which is the length of one wave in the air. Here are the first 5 milliseconds as a plot:

```python {run}
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
show(fig, "01-sine-plot", "The first 5 ms of the 440 Hz sine: a little over two cycles")
```

The vertical axis is not in pascals. Inside a computer a sound is a number between −1 and 1, and the loudspeaker and its volume knob decide how many pascals that becomes. A value of 1 is *full scale*, the largest the file can hold. The sine above reaches 0.5, half of full scale.

## Samples

A computer cannot store a smooth curve. It stores the value of the curve at regular moments, and each stored value is a *sample*. Euterpe takes 48 000 samples every second; this number is the *sample rate*. Audio CDs use 44 100 and video uses 48 000. `render` returns the samples as a numpy array:

```python {run}
from euterpe.sound import RATE, Sine, render

x = render(Sine(440.0) * 0.5, 2.0)
print(f"{RATE} samples per second, {len(x)} samples in 2 seconds, {x.nbytes} bytes")
print()
print("The first eight samples:")
print()
for i, v in enumerate(x[:8]):
    print(f"- sample {i}, at {i / RATE * 1000:.4f} ms: {v:+.5f}")
```

Each sample is a 32-bit float, so two seconds take 384 kilobytes. Between two samples there is nothing: the file does not say what the pressure was in between. Zoomed in to the first millisecond, the dots are all that is stored.

```python {run}
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
show(fig, "01-samples", "The first millisecond: 48 samples of the 440 Hz sine")
```

At 440 Hz there are 48 000 / 440, about 109 samples per cycle, which is plenty. The question is what happens when a wave moves faster, so that only a few samples land in each cycle.

## The Nyquist limit

Sampling at 48 000 Hz can represent frequencies up to half of that, 24 000 Hz. This half of the sample rate is the *Nyquist frequency*. A wave above it does not disappear. Its samples are exactly the samples of some wave below it, so after sampling the two cannot be told apart. The higher wave *folds back* to a lower one, and this is called *aliasing*.

Here is the arithmetic. A sine at 44 000 Hz is 4 000 Hz short of 48 000. At each sample it has advanced almost one full cycle, 44/48 of one; the shortfall, 4/48 of a cycle, is what a 4 000 Hz sine advances per sample, in the opposite direction. The code compares the samples of the two:

```python {run}
import numpy as np

n = np.arange(48)                        # one millisecond of sample numbers
high = np.sin(2 * np.pi * 44_000 * n / 48_000)
low = np.sin(2 * np.pi * 4_000 * n / 48_000)
print(f"largest difference between the 44 000 Hz samples and the upside-down 4 000 Hz samples: {np.abs(high + low).max():.1e}")
```

The difference is rounding error: the samples are the same, with the sign flipped. A sound system playing these samples produces 4 000 Hz. In the plot, the thin line is the 44 000 Hz wave and the thick one is the 4 000 Hz wave turned upside down; the samples, the dots, lie on both.

```python {run}
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
show(fig, "01-aliasing", "Half a millisecond: a 44 000 Hz sine and a 4 000 Hz sine share their samples")
```

In general, a frequency f above the Nyquist frequency lands at the distance from f to the nearest multiple of 48 000. Euterpe's oscillators avoid the problem at the source: asked for a frequency at or above 24 000 Hz, they output silence.

### Why a saw wave folds back

A sine has one frequency, so it is easy to keep below the limit. Most sounds are not sines. A *saw wave* rises steadily from −1 to 1 and then drops back at once, once per cycle. Chapter 3 shows that such a wave is a sum of sines at every whole multiple of its frequency, called its *harmonics*: a 10 000 Hz saw contains 10 000, 20 000, 30 000 Hz and so on, each one quieter. Every harmonic above 24 000 Hz folds back:

```python {run}
def fold(f, rate=48_000):
    """Where a frequency lands after sampling at rate."""
    return abs((f + rate / 2) % rate - rate / 2)

print("| harmonic | frequency (Hz) | heard at (Hz) |")
print("|---:|---:|---:|")
for k in range(1, 8):
    print(f"| {k} | {10_000 * k} | {fold(10_000 * k):.0f} |")
```

The 5th harmonic, 50 000 Hz, is heard at 2 000 Hz, far below the note itself. Folded harmonics do not sit at multiples of the note, so they sound like separate, out-of-tune whistles.

To hear it, here is a saw computed the direct way: take the position in the cycle, from 0 to 1, and scale it to run from −1 to 1. This is a new unit written in a few lines. A unit's `block(n)` returns its next `n` samples, and `_param("freq", n)` gives the frequency for each of them.

```python {run continue}
import numpy as np

from euterpe.sound import RATE, Param, Unit


class NaiveSaw(Unit):
    """A saw computed sample by sample, with nothing done about aliasing."""

    params = (Param("freq", "Hz", 0.01, 24_000.0, "log", 440.0),)

    def __init__(self, freq):
        self._set_params(freq=freq)
        self.reset()

    def reset(self):
        super().reset()
        self.position = 0.0

    def block(self, n):
        steps = self._param("freq", n).astype(np.float64) / RATE
        position = (self.position + np.cumsum(steps)) % 1.0
        self.position = position[-1]
        return (2 * position - 1).astype(np.float32)
```

Both saws now sweep from 1 000 Hz up to 23 000 Hz in four seconds. The frequency is itself a unit: half a cycle of a slow sine, scaled to the range. The first sweep is Euterpe's `Saw`, which smooths each drop over two samples with a correction called polyBLEP, so that much less is left above 24 000 Hz to fold. The second is the naive saw.

```python {run continue}
from euterpe.book import listen
from euterpe.sound import Saw, Sine

def sweep():
    """1 000 Hz at the start, 23 000 Hz after four seconds."""
    return Sine(0.125, phase=0.75) * 11_000 + 12_000

listen(Saw(sweep()) * 0.5, 4.0, "01-sweep-polyblep", "A saw sweeping from 1 to 23 kHz, band-limited", id="sweep-polyblep")
listen(NaiveSaw(sweep()) * 0.5, 4.0, "01-sweep-naive", "The same sweep with the naive saw: aliasing", id="sweep-naive")
```

Listen to the first sweep: one tone rises until it is too high to hear. Most adults stop hearing somewhere between 15 000 and 20 000 Hz, so the end of it may sound like silence. (The MP3 files on this page also drop everything above about 20 500 Hz.) In the second sweep, other tones move down while the note moves up, and they stay audible after the note itself is gone. Those are folded harmonics. Both sweeps also start with a click: the wave jumps from silence to −0.5 in one sample. Chapter 4 is about starting a sound smoothly.

A spectrogram shows the same thing. Time runs left to right, frequency bottom to top, and brightness is how much of each frequency is present at each moment:

```python {run continue}
import matplotlib.pyplot as plt

from euterpe.book import show
from euterpe.sound import RATE, render

fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True, dpi=60)
for ax, (title, unit) in zip(axes, [("Saw (polyBLEP)", Saw(sweep())), ("naive saw", NaiveSaw(sweep()))]):
    ax.specgram(render(unit * 0.5, 4.0), NFFT=1024, Fs=RATE, noverlap=0, vmin=-120, cmap="magma")
    ax.set_title(title)
    ax.set_xlabel("time (s)")
axes[0].set_ylabel("frequency (Hz)")
show(fig, "01-sweep-spectrogram", "The two sweeps: harmonics fold back from 24 kHz in the naive saw")
```

In the right panel each harmonic reaches the top edge, 24 000 Hz, and comes back down as a falling line. Those falling lines are the extra tones you heard. The left panel has them too, much fainter: polyBLEP reduces aliasing, it does not remove it. To put numbers on it, the next block takes one second of each saw at a steady 3 300 Hz and measures which share of the energy lies at frequencies that are not harmonics of 3 300 Hz, that is, in folded tones.

```python {run continue}
import numpy as np

from euterpe.sound import RATE, render

def folded_share(x, f, below, above):
    """The share of x's energy between below and above Hz that is not at a harmonic of f."""
    power = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / RATE)
    harmonic = np.min(np.abs(freqs[:, None] - f * np.arange(1, 8)), axis=1) < 20
    band = (freqs >= below) & (freqs < above)
    return power[band & ~harmonic].sum() / power.sum()

for name, unit in [("Saw (polyBLEP)", Saw(3_300.0)), ("naive saw", NaiveSaw(3_300.0))]:
    x = render(unit, 1.0)
    low, high = folded_share(x, 3_300.0, 0, 12_000), folded_share(x, 3_300.0, 12_000, 24_000)
    print(f"- {name}: {100 * low:.3f} % folded below 12 000 Hz, {100 * high:.2f} % above")
```

Below 12 000 Hz, where hearing is most sensitive, polyBLEP leaves about six hundred times less folded energy than the naive saw. Above 12 000 Hz the reduction is smaller, about twenty times, because a correction two samples wide cannot act sharply near the Nyquist frequency. Better methods exist and cost more computation; for the notes of real music, polyBLEP is enough.

## How fine each sample is

Each sample is a number, and a file stores it with a fixed number of bits. With b bits a sample can take 2 to the power b different values (`2 ** b` in Python). CD audio uses 16 bits, 65 536 values; Euterpe computes with 32-bit floats and writes 24-bit WAV files. Rounding every sample to the nearest allowed value is called *quantisation*. The rounding error is a small, noisy signal added to the sound, and each bit removed makes it about 6 dB louder (chapter 2 explains decibels).

`BitCrush` rounds each sample to `2 ** bits` levels spread evenly between −1 and 1. Here is the 440 Hz sine with 16, 6, 4 and 2 bits:

```python {run}
from euterpe.book import listen
from euterpe.sound import BitCrush, Sine

for bits in (16, 6, 4, 2):
    listen(BitCrush(Sine(440.0), bits=bits) * 0.5, 2.0, f"01-bits-{bits}", f"The 440 Hz sine with {bits} bits: {2 ** bits} levels", id=f"bits-{bits}")
```

At 16 bits it sounds like the sine at the top of the chapter. At 6 bits a faint hiss and buzz sit under the tone. At 4 bits the tone is harsh, and at 2 bits, four levels, the wave is a staircase of four steps and sounds close to a square wave. The plot shows one cycle of each:

```python {run}
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
show(fig, "01-bits-plot", "One cycle of the 440 Hz sine with 16, 4 and 2 bits")
```

Rounding is a change in the shape of the wave, so it adds frequencies that were not there: the rough edge you hear is those added frequencies. At 16 bits they are about 96 dB below full scale, too quiet to hear in normal listening, which is why 16 bits was enough for the CD.

## Summary

- A sound is air pressure that changes over time. In a computer it is a list of numbers between −1 and 1.
- Euterpe takes 48 000 samples per second. Between two samples nothing is stored.
- The highest frequency a sample rate can hold is half of it, the Nyquist frequency: 24 000 Hz here. A higher frequency folds back to a lower one.
- A wave with sudden jumps, like a saw, has harmonics far above its own frequency. Without band-limiting they fold back as audible, out-of-tune tones.
- Each sample is rounded to a finite number of levels. Fewer bits mean a larger rounding error, heard as hiss and harshness.

## Exercises

1. In the first example, change `440.0` to `220.0`, then to `880.0`. Each doubling of the frequency sounds like the same note, one step higher. Chapter 2 calls that step an octave.
2. In the sweep example, change `11_000 + 12_000` to `4_000 + 5_000`, a sweep from 1 000 to 9 000 Hz. Does the naive saw still produce falling tones? Use the `fold` table to predict which harmonics of a 9 000 Hz saw land below 9 000 Hz.
3. In the `BitCrush` example, add `downsample=8` and listen. Each sample is now held for 8 samples, so the sample rate is in effect 6 000 Hz and its Nyquist frequency 3 000 Hz. Holding adds copies of the tone around each multiple of 6 000 Hz: 5 560 and 6 440 Hz, 11 560 and 12 440 Hz, and so on. Then replace `Sine` with `Saw`, in the import line too: which harmonics of the 440 Hz saw now fold back below 3 000 Hz?

```python {run echo=false}
# Level check: every sound this chapter plays stays below full scale.
from pathlib import Path

import numpy as np

from euterpe.io import read

for path in sorted(Path("build/audio").glob("01-*.mp3")):
    x, rate = read(path)
    peak = float(np.abs(x).max())
    if rate != 48_000 or peak >= 0.999:
        print(f"**level check failed:** {path.name} has peak {peak:.3f} at {rate} Hz")
```
