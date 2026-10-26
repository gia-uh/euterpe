# Timbre

Chapter 2 ended with four waves at the same pitch, 220 Hz, and the same peak. They did not sound alike. A sine sounds pure, a triangle soft, a square hollow and buzzy, a saw bright and brassy. What differs between them is called *timbre*: everything that tells two sounds apart when their pitch and loudness are the same. This chapter shows that for a steady tone, timbre is mostly a list of sines: which frequencies a wave contains and how strong each one is.

## Four waves, one pitch

Here are the four waves again, at 220 Hz and gain 0.5. 220 Hz is the note A3, one octave below A4.

```python {run}
from euterpe.book import listen
from euterpe.sound import Saw, Sine, Square, Triangle

for wave in (Sine, Triangle, Square, Saw):
    listen(wave(220.0) * 0.5, 1.5, f"{wave.__name__} at 220 Hz")
```

All four have the same pitch: you could sing along with any of them on the same note. The plot shows two cycles of each, about 9.1 ms; each period is 1/220 of a second, 4.5 ms.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import RATE, Saw, Sine, Square, Triangle, render

fig, axes = plt.subplots(1, 4, figsize=(8, 2.2), sharey=True)
for ax, wave in zip(axes, (Sine, Triangle, Square, Saw)):
    x = render(wave(220.0), 2 / 220)
    ms = np.arange(len(x)) / RATE * 1000
    ax.plot(ms, x, linewidth=1)
    ax.axhline(0, color="grey", linewidth=0.5)
    ax.set_title(wave.__name__)
    ax.set_xlabel("time (ms)")
axes[0].set_ylim(-1.2, 1.2)
show(fig, "Two cycles of each wave at 220 Hz: the same period, 4.5 ms, and four shapes")
```

The period is the same, so the pitch is the same. The shape inside the period is different, and the shape is what you hear as timbre. To say what about a shape the ear hears, we need a way to take a wave apart.

## A spectrum

In the 1800s Joseph Fourier showed that any wave that repeats every 1/f seconds is a sum of sines, and only of sines that also repeat every 1/f seconds. Those are the sines at f, 2f, 3f and so on: a sine at k × f fits exactly k cycles into each period. They are called the *harmonics* of the wave, and harmonic 1, at f itself, is the *fundamental*. A sine at any other frequency would not fit a whole number of cycles into the period, so it would make the wave different from one period to the next.

The list of harmonics with their amplitudes is the wave's *spectrum*. numpy computes it with the *Fourier transform*, `np.fft.rfft`, which takes samples and returns one number per frequency. For exactly one second of samples it returns one number per whole hertz, from 0 Hz to 24 000 Hz, so index 220 is the 220 Hz component. The size of each number, times 2 and divided by the number of samples, is the amplitude of the sine at that frequency. Here are the first eight harmonics of each wave:

```python {run output=code}
import numpy as np

from euterpe.sound import Saw, Sine, Square, Triangle, render

for wave in (Sine, Triangle, Square, Saw):
    x = render(wave(220.0), 1.0)
    amp = np.abs(np.fft.rfft(x)) * 2 / len(x)   # amp[f]: the amplitude at f Hz
    print(f"{wave.__name__:8}", "  ".join(f"{amp[220 * k]:.3f}" for k in range(1, 9)))
```

Each column is a harmonic, from 220 Hz to 1 760 Hz. The sine has only its fundamental: it is the one wave made of a single sine. The others share three patterns:

- The saw has every harmonic, and harmonic k has 1/k of the fundamental's amplitude: 0.637, then 0.318 (half), 0.212 (a third), 0.159 (a quarter).
- The square has only the odd harmonics, 1, 3, 5, 7, also at 1/k: 1.273, 0.424 (a third), 0.254 (a fifth).
- The triangle has only the odd harmonics too, but at 1/k²: 0.811, 0.090 (a ninth), 0.032 (a twenty-fifth).

The fundamentals are larger than 1 for the square and smaller for the saw and the triangle, although all three waves peak at 1. A sine of amplitude 1.273 is taller than the square, but the other harmonics pull the sum back down to 1 everywhere. The exact values are 4/π for the square, 2/π for the saw and 8/π² for the triangle; they come from Fourier's formula for each shape, and they matter less than the pattern.

The plot shows the same spectra up to 6 000 Hz, in decibels. Each harmonic is a line at its frequency, as tall as its level in dB, so equal steps down mean equal ratios, as in chapter 2.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import Saw, Sine, Square, Triangle, render

fig, axes = plt.subplots(4, 1, figsize=(7, 5.5), sharex=True, sharey=True)
k = np.arange(1, 28)
for ax, wave in zip(axes, (Sine, Triangle, Square, Saw)):
    x = render(wave(220.0), 1.0)
    amp = np.abs(np.fft.rfft(x)) * 2 / len(x)
    db = 20 * np.log10(np.maximum(amp[220 * k], 1e-6))
    ax.vlines(220 * k, -80, db, linewidth=2)
    ax.set_ylim(-80, 5)
    ax.text(0.99, 0.8, wave.__name__, transform=ax.transAxes, ha="right")
    ax.set_ylabel("dB")
axes[-1].set_xlabel("frequency (Hz)")
show(fig, "The spectra of the four waves at 220 Hz, up to 6 kHz: one line per harmonic")
```

This is what the ear hears. The inner ear splits a sound into frequencies, much as the Fourier transform does, and timbre is largely the pattern of levels it finds. A sound with strong high harmonics sounds *bright*: the saw, whose levels fall by 6 dB per doubling of k. A sound whose harmonics fade fast sounds *dark* or soft: the triangle, whose levels fall by 12 dB per doubling, so that its fifth harmonic is already 28 dB below the fundamental. The square sounds hollow because of the gaps, the missing even harmonics.

### How A-BALANCE splits the spectrum

Chapter 2 left one line of the `lint_audio` report unexplained. `A-BALANCE` splits the energy of a sound into three bands: low, below 250 Hz; mid, from 250 to 4 000 Hz; and high, above 4 000 Hz. Each line gives its band's share of the total energy. The energy of a harmonic grows with the square of its amplitude, so a harmonic at 1/k carries 1/k² of the fundamental's energy.

```python {run output=code}
from euterpe.lint import lint_audio
from euterpe.sound import Saw, Sine, Square, Triangle, render

for wave in (Sine, Triangle, Square, Saw):
    report = lint_audio(render(wave(220.0) * 0.5, 2.0))
    shares = [100 * report.value(f"A-BALANCE-{band}") for band in ("LOW", "MID", "HIGH")]
    print(f"{wave.__name__:8}  low {shares[0]:5.1f} %   mid {shares[1]:5.1f} %   high {shares[2]:4.1f} %")
```

At 220 Hz only the fundamental is below 250 Hz, so the low band is the fundamental's share. The sine has all of its energy there. The triangle keeps 98.6 % there, the square 81.7 % and the saw 61.6 %. The saw puts the most energy above 4 000 Hz, 2.2 %, against 1.5 % for the square and 0.0 % for the triangle; that is what makes it the brightest. Later chapters use these numbers to balance a mix.

## Building sounds from sines

If a wave is a sum of sines, it can be built by adding sines. Euterpe's `Additive` does that. `Additive(freq, partials)` takes a frequency and a list of *partials*, pairs `(ratio, amplitude)`. Each partial is a sine at `ratio * freq` with that amplitude, and the unit outputs their sum. Partial is the general word: a harmonic is a partial whose ratio is a whole number.

Here is a 220 Hz tone built from its first three harmonics, at amplitudes 1, 1/2 and 1/3, then the same three harmonics with the second one turned up to 1:

```python {run}
from euterpe.book import listen
from euterpe.sound import Additive

listen(Additive(220.0, [(1, 1.0), (2, 0.5), (3, 0.33)]) * 0.3, 2.0, "Harmonics 1, 2 and 3 at 1, 1/2 and 1/3")
listen(Additive(220.0, [(1, 1.0), (2, 1.0), (3, 0.33)]) * 0.3, 2.0, "The same, with harmonic 2 as strong as the fundamental")
```

Both tones have the pitch of 220 Hz, and both are a little richer than a sine. The second sounds brighter and thinner, and a listener may hear its 440 Hz harmonic stand out. Still, there is one note, not three: when partials sit at whole multiples of one frequency, the ear fuses them into a single tone with the pitch of that frequency.

That fusion depends on the ratios being whole numbers. A free metal bar, struck, vibrates at frequencies with ratios near 1, 2.76, 5.40 and 8.93 to its lowest one. Here are those four partials at 220 Hz, next to harmonics 1, 3, 5 and 9 with the same amplitudes:

```python {run}
from euterpe.book import listen
from euterpe.sound import Additive

amps = [1.0, 0.6, 0.4, 0.25]
listen(Additive(220.0, list(zip([1, 3, 5, 9], amps))) * 0.3, 2.0, "Harmonics 1, 3, 5 and 9")
listen(Additive(220.0, list(zip([1, 2.76, 5.40, 8.93], amps))) * 0.3, 2.0, "Partials at 1, 2.76, 5.40 and 8.93: a metal bar")
```

The first tone is one note. It has only odd harmonics, and strong ones, as the square does, so it sounds hollow like the square. The second sounds metallic, and it is hard to say what note it is. Its ratios are 100, 276, 540 and 893 hundredths, which share no common factor, so their common period is 100 cycles of 220 Hz: 0.45 s, a repetition rate of 2.2 Hz. That is far below any pitch the ear hears, so the ear finds no single note, and hears several pitches at once. This is why bells and gongs sound the way they do. Chapter 6 makes such sounds ring and decay.

## A saw, one sine at a time

The spectrum table measured the saw's harmonics at 2/π × 1/k. That gives the recipe for a saw: harmonic k at amplitude 2/(πk). There is one more detail. Euterpe's `Saw` rises and then drops; the plain sum of these sines falls and then jumps up, the same wave played backwards. To rise instead, every sine is turned upside down, which is what a negative amplitude does. The ear cannot hear the difference, but the plots can.

The block below builds the saw with 1, 2, 4, 8, 16 and 109 harmonics. 109 is the last one below the Nyquist limit of chapter 1: 109 × 220 = 23 980 Hz, and the 110th would be 24 200 Hz.

```python {run}
import numpy as np

from euterpe.book import listen
from euterpe.sound import Additive, Saw

for n in (1, 2, 4, 8, 16, 109):
    partials = [(k, -2 / (np.pi * k)) for k in range(1, n + 1)]
    listen(Additive(220.0, partials) * 0.5, 1.5, f"A saw built up to harmonic {n}")
listen(Saw(220.0) * 0.5, 1.5, "Saw at 220 Hz, for comparison")
```

One harmonic is a sine. Each doubling adds an octave of brighter harmonics, and the tone grows from a soft hum towards the buzz of the saw. The step from 16 to 109 harmonics adds everything above 3 520 Hz; it is a smaller change to the ear than the step from 1 to 2, because the added harmonics are weak, 1/17 of the fundamental and less. The last two players are hard to tell apart.

The plot shows one cycle of the sums with 1, 4, 16 and 109 harmonics, drawn over the saw:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import RATE, Additive, Saw, render

saw = render(Saw(220.0), 1 / 220)
ms = np.arange(len(saw)) / RATE * 1000
fig, axes = plt.subplots(1, 4, figsize=(8, 2.2), sharey=True)
for ax, n in zip(axes, (1, 4, 16, 109)):
    built = render(Additive(220.0, [(k, -2 / (np.pi * k)) for k in range(1, n + 1)]), 1 / 220)
    ax.plot(ms, saw, color="grey", linewidth=0.8)
    ax.plot(ms, built, linewidth=1)
    ax.set_title(f"{n} harmonic" + ("s" if n > 1 else ""))
    ax.set_xlabel("time (ms)")
axes[0].set_ylim(-1.3, 1.3)
show(fig, "One cycle of a saw built from 1, 4, 16 and 109 harmonics, over Saw in grey")
```

Each harmonic added makes the ramp straighter and the drop steeper. Next to the drop the sum overshoots: it goes above 1, where the saw stops. This block prints the highest sample in one second of each sum:

```python {run output=code}
import numpy as np

from euterpe.sound import Additive, render

for n in (4, 8, 16, 109):
    partials = [(k, -2 / (np.pi * k)) for k in range(1, n + 1)]
    print(f"{n:3} harmonics: highest sample {render(Additive(220.0, partials), 1.0).max():.3f}")
```

With 4 harmonics the sum stays below 1 (0.972); with 8 it already passes 1, and with 16 and 109 it reaches 1.12 and 1.17. The overshoot moves closer to the drop as harmonics are added, but it does not get smaller: it approaches about 9 % of the jump, which is 2, so the peak approaches 1.18. It is called the *Gibbs phenomenon*, and it is the price of stopping at a finite number of harmonics, as a sampled wave must.

So which is the better saw? The 109-harmonic sum is exactly the saw with every harmonic below 24 000 Hz and nothing above, so nothing can fold back. `Saw` is cheaper to compute, one formula per sample instead of 109 sines, and its polyBLEP correction is only an approximation. This block compares their harmonics 1, 10, 50 and 100, each multiplied by k so that the ideal value is 2/π = 0.637 for every one:

```python {run output=code}
import numpy as np

from euterpe.sound import Additive, Saw, render

built = render(Additive(220.0, [(k, -2 / (np.pi * k)) for k in range(1, 110)]), 1.0)
saw = render(Saw(220.0), 1.0)
for name, x in (("Additive", built), ("Saw", saw)):
    amp = np.abs(np.fft.rfft(x)) * 2 / len(x)
    print(f"{name:8}", "  ".join(f"k={k}: {k * amp[220 * k]:.3f}" for k in (1, 10, 50, 100)))
print(f"energy of Saw against Additive: {100 * np.mean(saw ** 2) / np.mean(built ** 2):.1f} %")
```

The two agree up to the tenth harmonic, 2 200 Hz. Above it, `Saw` falls behind: harmonic 50, at 11 000 Hz, is at 84 % of the ideal, and harmonic 100, at 22 000 Hz, at 47 %. polyBLEP smooths the drop over two samples, which is a little smoother than the ideal saw, and smoothing takes away high harmonics. Yet the last line shows that `Saw` keeps 99.3 % of the ideal's energy: it loses 0.7 %, about 0.03 dB, far below the 1 dB step of chapter 2, and the loss falls on harmonics that are already weak. That is why the two players sound alike.

`Additive` drops a partial on its own when its frequency reaches 24 000 Hz. Asking for 200 harmonics of 220 Hz gives the same samples as asking for 109:

```python {run output=code}
import numpy as np

from euterpe.sound import Additive, render

def saw_partials(n):
    return [(k, -2 / (np.pi * k)) for k in range(1, n + 1)]

print(np.array_equal(render(Additive(220.0, saw_partials(200)), 1.0), render(Additive(220.0, saw_partials(109)), 1.0)))
```

## Why the square has only odd harmonics

A square spends the first half of each cycle at +1 and the second half at −1. So its second half is its first half turned upside down: if T is the period, the value at time t + T/2 is minus the value at t. The triangle has the same property: its second half, a fall from 1 to −1, is its first half, a rise from −1 to 1, turned upside down.

Now look at one harmonic. Harmonic k does k cycles per period, so in half a period it does k/2 cycles. When k is even, k/2 is a whole number, and half a period later the harmonic is back at the same value. When k is odd, it is half a cycle further on, which is the same sine upside down. Shift the whole wave by half a period, then: the even harmonics stay the same and the odd ones flip. For a square that shift must flip the whole wave. A wave has only one spectrum, so each harmonic of the shifted wave must equal minus the same harmonic of the wave. Call an even harmonic h(t): the shift leaves it h(t), and the flip requires −h(t), so h(t) = −h(t) for every t, which only zero satisfies. So a square, and any wave whose second half mirrors its first, has no even harmonics.

The saw does not have this property: its second half continues the same rising ramp. This block checks it on the samples. At 200 Hz a cycle is exactly 240 samples, so half a cycle is 120 samples, and `x[120:240] + x[:120]` is zero wherever the second half mirrors the first:

```python {run output=code}
import numpy as np

from euterpe.sound import Saw, Square, Triangle, render

for wave in (Square, Triangle, Saw):
    x = render(wave(200.0), 240 / 48_000)
    print(f"{wave.__name__:8} largest x[120:240] + x[:120]: {np.abs(x[120:240] + x[:120]).max():.4f}")
```

The square and the triangle mirror exactly, and their spectra have no even harmonic. The saw does not, and has every harmonic.

The argument also runs the other way: a sum of odd harmonics alone always mirrors itself. When those odd harmonics are strong, at 1/k as in the square, it sounds hollow; at 1/k², as in the triangle, they fade too fast to be heard much, and it sounds soft. Here is the square built from its odd harmonics, at 4/π × 1/k as the table measured, next to `Square`:

```python {run}
import numpy as np

from euterpe.book import listen
from euterpe.sound import Additive, Square

partials = [(k, 4 / (np.pi * k)) for k in range(1, 110, 2)]   # k = 1, 3, 5, ..., 109
listen(Additive(220.0, partials) * 0.35, 1.5, "A square from its odd harmonics")
listen(Square(220.0) * 0.35, 1.5, "Square at 220 Hz, for comparison")
```

The gain is 0.35 rather than 0.5 because a square is louder than the other waves at the same peak (chapter 2), and because the built square overshoots, as the saw did.

## Summary

- Timbre is what tells two sounds apart at the same pitch and loudness. For a steady tone, it is mostly the levels of the sines the tone contains.
- A wave that repeats every 1/f seconds is a sum of harmonics at f, 2f, 3f, and so on (Fourier). Their amplitudes are its spectrum, and `np.fft.rfft` computes it.
- The saw has every harmonic at 1/k, the square the odd ones at 1/k, the triangle the odd ones at 1/k². The faster the levels fall, the darker the sound.
- A wave whose second half is its first half upside down has only odd harmonics.
- `Additive(freq, partials)` sums sines at `ratio * freq`. Whole-number ratios fuse into one note; other ratios sound metallic, without a clear pitch. Partials at or above 24 000 Hz are dropped.
- `A-BALANCE` reports the share of energy below 250 Hz, from 250 to 4 000 Hz, and above 4 000 Hz.

## Exercises

1. In the saw built from harmonics, change `range(1, n + 1)` to `range(1, n + 1, 2)`. Which wave does it approach, and why does it come out at a lower level than `Square`?
2. In the spectrum table, replace `Square` with `lambda f: Square(f, duty=0.25)`, a square that stays high for only a quarter of each cycle. Which harmonics are missing now? (The table prints `<lambda>` for its name.)
3. In the block that builds the saw, raise the frequency from `220.0` to `2_000.0`. How many harmonics are left below 24 000 Hz, and how does the 16-harmonic version compare with the 109-harmonic one?

### Answers

1. It approaches a square: the odd harmonics at 1/k are the square's spectrum. The amplitudes are 2/(πk) instead of 4/(πk), half of the square's, so it swings between about −0.5 and 0.5 instead of −1 and 1 (0.59 at the overshoot). It also points the other way, because the amplitudes are negative.
2. Every fourth harmonic is missing: 4, 8, 12, and so on. The other even harmonics are back, because a pulse with duty 0.25 no longer mirrors itself. In general a pulse with duty 1/m has no harmonics at multiples of m.
3. Only 11: 11 × 2 000 = 22 000 Hz, and the 12th would be 24 000 Hz, which is the limit itself, so `Additive` drops it. The 16- and 109-harmonic versions sound the same, because both have the same 11 harmonics.

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
