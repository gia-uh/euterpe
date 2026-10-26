# Timbre

Near its end, chapter 2 played four waves at the same pitch, 220 Hz, and the same peak. They did not sound alike. A sine sounds pure, a triangle soft, a square hollow and buzzy, a saw bright and brassy. What differs between them is called *timbre*: everything that tells two sounds apart when their pitch and loudness are the same. This chapter shows that for a steady tone, timbre is a list of sines: which frequencies a wave contains and how strong each one is.

## Four waves, one pitch

Here are the four waves again, at 220 Hz and gain 0.5. 220 Hz is the note A3, one octave below A4.

```python {run}
from euterpe.view import listen
from euterpe.sound import Saw, Sine, Square, Triangle

for wave in (Sine, Triangle, Square, Saw):
    display(listen(wave(220.0) * 0.5, 1.5, f"{wave.__name__} at 220 Hz"))
```

All four have the same pitch: you could sing along with any of them on the same note. The plot shows two cycles of each, about 9.1 ms; each period is 1/220 of a second, 4.5 ms.

```python {run echo=false}
from euterpe.sound import Saw, Sine, Square, Triangle
from euterpe.view import waveform

waves = (Sine, Triangle, Square, Saw)
waveform(
    *[wave(220.0).take(2 / 220) for wave in waves],
    separate=True, labels=[wave.__name__ for wave in waves],
    caption="Two cycles of each wave at 220 Hz: the same period, 4.5 ms, and four shapes",
)
```

The period is the same, so the pitch is the same. The shape inside the period is different, and the shape is what you hear as timbre. To say what about a shape the ear hears, we need a way to take a wave apart.

## A spectrum

In the 1800s Joseph Fourier showed that any wave that repeats every 1/f seconds is a sum of sines, and only of sines that also repeat every 1/f seconds. Those are the sines at f, 2f, 3f and so on: a sine at k × f fits exactly k cycles into each period. They are called the *harmonics* of the wave, and harmonic 1, at f itself, is the *fundamental*. A sine at any other frequency would not fit a whole number of cycles into the period, so it would make the wave different from one period to the next.

Each harmonic has an amplitude and a *phase*. Chapter 1 introduced phase as a parameter of `Sine`: where in its cycle the sine starts, measured in cycles from 0 to 1. The list of harmonics with their amplitudes is the wave's *spectrum*.

numpy computes it with the *Fourier transform*, `np.fft.rfft`. It returns complex numbers, one per frequency: the size of each, `np.abs`, is how strong that frequency is, and its angle is the phase. With T seconds of sound there is one number every 1/T Hz, so for exactly one second there is one per whole hertz, and index 220 is the 220 Hz component. The transform adds up the samples multiplied by a test sine at each frequency. A sine of amplitude a, over N samples, adds up to a × N / 2, because the average of a sine squared is 1/2. So `np.abs(...) * 2 / len(x)` turns each number back into the amplitude of the sine at that frequency. Here are the first eight harmonics of each wave:

```python {run output=code}
import numpy as np

from euterpe.sound import Saw, Sine, Square, Triangle, render

for wave in (Sine, Triangle, Square, Saw):
    x = render(wave(220.0), 1.0)
    amp = np.abs(np.fft.rfft(x)) * 2 / len(x)   # amp[f]: the amplitude at f Hz
    print(wave.__name__, np.round(amp[220 * np.arange(1, 9)], 3))
```

Each column is a harmonic, from 220 Hz to 1 760 Hz. The sine has only its fundamental: it is the one wave made of a single sine. The others share three patterns:

- The saw has every harmonic, and harmonic k has 1/k of the fundamental's amplitude: 0.637, then 0.318 (half), 0.212 (a third), 0.159 (a quarter).
- The square has only the odd harmonics, 1, 3, 5, 7, also at 1/k: 1.273, 0.424 (a third), 0.254 (a fifth).
- The triangle has only the odd harmonics too, but at 1/k²: 0.811, 0.090 (a ninth), 0.032 (a twenty-fifth).

The fundamentals are larger than 1 for the square and smaller for the saw and the triangle, although all three waves peak at 1. A sine of amplitude 1.273 is taller than the square, but the other harmonics pull the sum back down to 1, everywhere except next to the jumps, as the overshoot below shows. The exact values are 4/π for the square, 2/π for the saw and 8/π² for the triangle; they come from Fourier's formula for each shape, and they matter less than the pattern.

`np.abs` keeps the size of each number and drops its phase. That loses nothing the ear needs: for a steady tone, the ear hears the amplitudes of the harmonics, not their phases or signs. So for a steady tone the spectrum table is the whole of timbre. Phase does matter for the shape of the wave, and so for its peak and for whether it clips; the end of this chapter hears and measures both.

The plot shows the same spectra up to 6 000 Hz, in decibels. Each harmonic is a line at its frequency, as tall as its level in dB, so equal steps down mean equal ratios, as in chapter 2.

```python {run echo=false}
from euterpe.sound import Saw, Sine, Square, Triangle
from euterpe.view import spectrum

waves = (Sine, Triangle, Square, Saw)
spectrum(
    *[wave(220.0).take(1.0) for wave in waves],
    f0=220.0, upto=6000, labels=[wave.__name__ for wave in waves],
    caption="The spectra of the four waves at 220 Hz, up to 6 kHz: one line per harmonic",
)
```

This is what the ear hears. The inner ear splits a sound into frequencies, much as the Fourier transform does, and timbre is the pattern of levels it finds. A sound with strong high harmonics sounds *bright*: the saw, whose levels fall by 6 dB per doubling of k. A sound whose harmonics fade fast sounds *dark* or soft: the triangle, whose levels fall by 12 dB per doubling, so that its fifth harmonic is already 28 dB below the fundamental. The square sounds hollow because of the gaps, the missing even harmonics.

### How A-BALANCE splits the spectrum

Chapter 2 left the three `A-BALANCE` lines of the `lint_audio` report unexplained. They split the energy of a sound into three bands: low, below 250 Hz; mid, from 250 to 4 000 Hz; and high, above 4 000 Hz. Each line gives its band's share of the total energy, as a fraction from 0 to 1.

```python {run output=code}
from euterpe.lint import lint_audio
from euterpe.sound import Saw, Sine, Square, Triangle, render

for wave in (Sine, Triangle, Square, Saw):
    report = lint_audio(render(wave(220.0) * 0.5, 2.0))
    print(wave.__name__, [round(report.value(f"A-BALANCE-{band}"), 3) for band in ("LOW", "MID", "HIGH")])
```

At 220 Hz only the fundamental is below 250 Hz, so the low share is the fundamental's share of the energy. The energy of a harmonic grows with the square of its amplitude, so for the saw, whose harmonic k has amplitude 1/k, harmonic k carries 1/k² of the fundamental's energy. With the 109 harmonics below 24 000 Hz, the fundamental's share is:

```python {run output=code}
print(1 / sum(1 / k ** 2 for k in range(1, 110)))
```

That is 0.611, and the report reads 0.616. The difference is `Saw`'s polyBLEP correction: it weakens the highest harmonics a little, as the end of this chapter measures, which leaves a slightly larger share to the fundamental.

For brightness, the band to compare is the high one. The saw puts the most energy above 4 000 Hz, 0.022 of it, against 0.015 for the square and nothing measurable for the triangle; that is what makes it the brightest. Later chapters use these numbers to balance a mix.

## Building sounds from sines

If a wave is a sum of sines, it can be built by adding sines. Euterpe's `Additive` does that. `Additive(freq, partials)` takes a frequency and a list of *partials*, pairs `(ratio, amplitude)`. Each partial is a sine at `ratio * freq` with that amplitude, and the unit outputs their sum. Partial is the general word: a harmonic is a partial whose ratio is a whole number. `Additive` does not scale the sum, so the gain after it decides the level.

Here is a 220 Hz tone built from its first three harmonics, at amplitudes 1, 1/2 and 1/3, then the same three harmonics with the second one turned up to 1:

```python {run}
from euterpe.view import listen
from euterpe.sound import Additive

display(listen(Additive(220.0, [(1, 1.0), (2, 0.5), (3, 0.33)]) * 0.3, 2.0, "Harmonics 1, 2 and 3 at 1, 1/2 and 1/3"))
listen(Additive(220.0, [(1, 1.0), (2, 1.0), (3, 0.33)]) * 0.3, 2.0, "The same, with harmonic 2 as strong as the fundamental")
```

Both tones have the pitch of 220 Hz, and both are a little richer than a sine. The second sounds brighter and thinner, and a listener may hear its 440 Hz harmonic stand out. Still, there is one note, not three: when partials sit at whole multiples of one frequency, the ear fuses them into a single tone with the pitch of that frequency.

That fusion depends on the ratios being whole numbers. A free metal bar, struck, vibrates at frequencies with ratios near 1, 2.76, 5.40 and 8.93 to its lowest one. Here are those four partials at 220 Hz, next to harmonics 1, 3, 5 and 9 with the same amplitudes:

```python {run}
from euterpe.view import listen
from euterpe.sound import Additive

amps = [1.0, 0.6, 0.4, 0.25]
display(listen(Additive(220.0, list(zip([1, 3, 5, 9], amps))) * 0.3, 2.0, "Harmonics 1, 3, 5 and 9"))
listen(Additive(220.0, list(zip([1, 2.76, 5.40, 8.93], amps))) * 0.3, 2.0, "Partials at 1, 2.76, 5.40 and 8.93: a metal bar")
```

The first tone is one note. It has only odd harmonics, and strong ones, as the square does, so it sounds hollow like the square. The second sounds metallic, and it is hard to say what note it is. A sum of sines repeats when every one of them has finished a whole number of cycles. This block finds when that happens for the bar:

```python {run output=code}
import numpy as np

hz = 220 * np.array([1, 2.76, 5.40, 8.93])
print(hz, hz / 2.2, np.gcd.reduce([100, 276, 540, 893]))
```

The four frequencies are 2.2 Hz times 100, 276, 540 and 893. Some of those whole numbers share a factor (100, 276 and 540 are all multiples of 4), but all four together share none, as `np.gcd.reduce` shows. So 2.2 Hz is the largest step that fits all four, and the wave repeats every 1/2.2 s, 0.45 s. A repetition rate of 2.2 Hz is far below any pitch the ear hears, so the ear finds no single note, and hears several pitches at once. This is why bells and gongs sound the way they do. Chapter 7 makes such sounds ring and decay.

## A saw, one sine at a time

The spectrum table measured the saw's harmonics at 2/π × 1/k. That gives the recipe for a saw: harmonic k at amplitude 2/(πk). There is one more detail. Euterpe's `Saw` rises and then drops; the plain sum of these sines falls and then jumps up, the same wave played backwards. To rise instead, every sine is turned upside down, which is what a negative amplitude does: it shifts that sine's phase by half a cycle. The ear cannot hear the difference, but the plots can.

`saw_partials(n)` lists harmonics 1 to n with those amplitudes. The block builds the saw with 1, 2, 4, 8, 16 and 109 harmonics. 109 is the last one below the Nyquist limit of chapter 1: 109 × 220 = 23 980 Hz, and the 110th would be 24 200 Hz.

```python {run}
import numpy as np

from euterpe.view import listen
from euterpe.sound import Additive, Saw

def saw_partials(n):
    return [(k, -2 / (np.pi * k)) for k in range(1, n + 1)]

for n in (1, 2, 4, 8, 16, 109):
    display(listen(Additive(220.0, saw_partials(n)) * 0.5, 1.5, f"A saw built up to harmonic {n}"))
listen(Saw(220.0) * 0.5, 1.5, "Saw at 220 Hz, for comparison")
```

One harmonic is a sine. Each doubling adds an octave of brighter harmonics, and the tone grows from a soft hum towards the buzz of the saw. The step from 16 to 109 harmonics adds everything above 3 520 Hz; it is a smaller change to the ear than the step from 1 to 2, because the added harmonics are weak, 1/17 of the fundamental and less. The last two players are hard to tell apart.

The plot shows one cycle of the sums with 1, 4, 16 and 109 harmonics, drawn over the saw:

```python {run continue echo=false}
from euterpe.view import waveform

counts = (1, 4, 16, 109)
waveform(
    *[Additive(220.0, saw_partials(n)).take(1 / 220) for n in counts],
    separate=True, reference=Saw(220.0).take(1 / 220),
    labels=[f"{n} harmonic" + ("s" if n > 1 else "") for n in counts],
    caption="One cycle of a saw built from 1, 4, 16 and 109 harmonics, over Saw in grey",
)
```

Each harmonic added makes the ramp straighter and the drop steeper. Next to the drop the sum overshoots: it goes above 1, where the saw stops. This block prints the highest sample in one second of each sum, and of `Saw` and `Square`:

```python {run continue output=code}
from euterpe.sound import Square, render

for n in (4, 8, 16, 109):
    print(n, "harmonics:", render(Additive(220.0, saw_partials(n)), 1.0).max())
print("Saw:", render(Saw(220.0), 1.0).max(), " Square:", render(Square(220.0), 1.0).max())
```

With 4 harmonics the sum stays below 1 (0.972); with 8 it already passes 1, and with 16 and 109 it reaches 1.12 and 1.17. This is called the *Gibbs phenomenon*. Adding harmonics narrows the overshoot, squeezing it closer to the drop, but does not lower it, so its height settles near 9 % of the jump, which is 2: the peak approaches 1.18. `Saw` and `Square` do not overshoot (0.991 and 1.0), because they are computed from the shape itself, with polyBLEP's two-sample correction at each jump, not as a sum of sines. The overshoot matters for levels: a saw built from its harmonics at full scale would reach 1.17 and clip, so the examples here use gain 0.5.

Which is the better saw? They sound the same; `Saw` is cheaper, one formula per sample instead of 109 sines, and its polyBLEP correction lets a little aliasing through, while `Additive` drops every partial at or above 24 000 Hz and aliases not at all. This block compares their harmonics 1, 10, 50 and 100, each multiplied by k so that the ideal value is 2/π = 0.637 for every one:

```python {run continue output=code}
k = np.array([1, 10, 50, 100])
for unit in (Additive(220.0, saw_partials(109)), Saw(220.0)):
    x = render(unit, 1.0)
    amp = np.abs(np.fft.rfft(x)) * 2 / len(x)
    print(type(unit).__name__, np.round(k * amp[220 * k], 3))
```

The two agree up to the tenth harmonic, 2 200 Hz. Above it, `Saw` falls behind: harmonic 50, at 11 000 Hz, is at 84 % of the ideal (0.534 / 0.637), and harmonic 100, at 22 000 Hz, at 47 %. polyBLEP smooths the drop over two samples, which is a little smoother than the ideal saw, and smoothing takes away high harmonics. Those harmonics are already weak, so the loss changes the sound very little.

## Why the square has only odd harmonics

A square spends the first half of each cycle at +1 and the second half at −1. So its second half is its first half turned upside down. The proof that this rules out every even harmonic takes one step per line. Let T be the period.

1. Shift the wave by half a period: look at x(t + T/2) instead of x(t).
2. Harmonic k makes k cycles per period, so in half a period it makes k/2 cycles.
3. When k is even, k/2 is a whole number, so the harmonic is back where it was: an even harmonic h satisfies h(t + T/2) = h(t).
4. When k is odd, the harmonic is half a cycle further on, which is the same sine upside down: an odd harmonic h satisfies h(t + T/2) = −h(t).
5. For the square, the second half is the first upside down: x(t + T/2) = −x(t).
6. Shifting the square shifts each of its harmonics, so by step 3 the shifted square has the same even harmonics h(t) as the square.
7. Minus the square has every harmonic negated, so its even harmonics are −h(t).
8. A wave has only one spectrum, and by step 5 these two waves are the same wave. So h(t) = −h(t) for every t.
9. Only h = 0 satisfies that. The square has no even harmonics.

The triangle has the same property: its second half, a fall from 1 to −1, is its first half, a rise from −1 to 1, turned upside down. The saw does not: its second half continues the same rising ramp. This block checks it on the samples. At 200 Hz a cycle is exactly 240 samples, so half a cycle is 120 samples, and `x[120:240] + x[:120]` is zero wherever the second half mirrors the first:

```python {run output=code}
import numpy as np

from euterpe.sound import Saw, Square, Triangle, render

for wave in (Square, Triangle, Saw):
    x = render(wave(200.0), 240 / 48_000)
    print(wave.__name__, np.abs(x[120:240] + x[:120]).max().round(4))
```

The square and the triangle print 0 to four decimals: they mirror, and their spectra have no even harmonic. The saw does not, and has every harmonic.

The argument also runs the other way: a sum of odd harmonics alone always mirrors itself. When those odd harmonics are strong, at 1/k as in the square, it sounds hollow; at 1/k², as in the triangle, they fade too fast to be heard much, and it sounds soft. Here is the square built from its odd harmonics, at 4/π × 1/k as the table measured, next to `Square`:

```python {run}
import numpy as np

from euterpe.view import listen
from euterpe.sound import Additive, Square

partials = [(k, 4 / (np.pi * k)) for k in range(1, 110, 2)]   # k = 1, 3, 5, ..., 109
display(listen(Additive(220.0, partials) * 0.35, 1.5, "A square from its odd harmonics"))
listen(Square(220.0) * 0.35, 1.5, "Square at 220 Hz, for comparison")
```

The gain is 0.35 rather than 0.5 because a square is louder than the other waves at the same peak (chapter 2), and because the built square overshoots, as the saw did.

### The triangle, and what phase changes

The triangle's odd harmonics have amplitude 8/(π²k²), and their signs alternate: +, −, +, − for k = 1, 3, 5, 7. `(-1) ** (k // 2)` gives that sign, since k // 2 is 0, 1, 2, 3 for those k. The block builds the triangle, then the same harmonics with every sign positive: the same amplitudes, with the phase of every other harmonic shifted by half a cycle.

```python {run}
import numpy as np

from euterpe.view import listen
from euterpe.sound import Additive, Triangle

odd = range(1, 110, 2)
triangle = [(k, (-1) ** (k // 2) * 8 / (np.pi ** 2 * k ** 2)) for k in odd]
same_sizes = [(k, 8 / (np.pi ** 2 * k ** 2)) for k in odd]

display(listen(Additive(220.0, triangle) * 0.5, 1.5, "A triangle from its odd harmonics, signs alternating"))
display(listen(Additive(220.0, same_sizes) * 0.5, 1.5, "The same harmonics, every sign positive"))
listen(Triangle(220.0) * 0.5, 1.5, "Triangle at 220 Hz, for comparison")
```

The three players sound the same. The plot shows why that is remarkable: the second wave has a different shape.

```python {run continue echo=false}
from euterpe.view import waveform

waveform(
    Additive(220.0, triangle).take(2 / 220), Additive(220.0, same_sizes).take(2 / 220),
    separate=True, labels=["signs alternating", "every sign positive"],
    caption="Two cycles of the same odd harmonics at 220 Hz with two sets of signs: two shapes, one sound",
)
```

The block below measures what changed and what did not: the amplitudes of the first four odd harmonics, the loudness of the sum at gain 0.5, and its peak.

```python {run continue output=code}
from euterpe.lint import lint_audio
from euterpe.sound import render

for partials in (triangle, same_sizes):
    x = render(Additive(220.0, partials), 1.0)
    amp = np.abs(np.fft.rfft(x)) * 2 / len(x)
    print(np.round(amp[220 * np.array([1, 3, 5, 7])], 3), lint_audio(x * 0.5).value("A-LUFS"), "LUFS, peak", x.max())
```

Both have the same harmonic amplitudes and the same loudness, −11.7 LUFS, so they have the same timbre. Only the phases differ, and the phases change the shape and the peak: 0.996 for the triangle, 0.742 for the other. Phase decides how high a wave reaches, and so how much gain it takes before it clips, but not how it sounds.

## Summary

- Timbre is what tells two sounds apart at the same pitch and loudness. For a steady tone, it is the amplitudes of the sines the tone contains.
- A wave that repeats every 1/f seconds is a sum of harmonics at f, 2f, 3f, and so on (Fourier). Their amplitudes are its spectrum, and `np.abs(np.fft.rfft(x)) * 2 / len(x)` computes it, one value every 1/T Hz for T seconds of sound.
- The saw has every harmonic at 1/k, the square the odd ones at 1/k, the triangle the odd ones at 1/k². The faster the levels fall, the darker the sound.
- A wave whose second half is its first half upside down has only odd harmonics.
- The ear does not hear the phases of a steady tone's harmonics, but phase sets the shape and the peak. A sum of sines stopped at a finite number of harmonics overshoots a jump by about 9 % of it.
- `Additive(freq, partials)` sums sines at `ratio * freq`, without scaling. Whole-number ratios fuse into one note; other ratios sound metallic, without a clear pitch. Partials at or above 24 000 Hz are dropped.
- `A-BALANCE` reports the share of energy below 250 Hz, from 250 to 4 000 Hz, and above 4 000 Hz. The high share tracks brightness.

## Exercises

1. In the block that builds the saw, change `range(1, n + 1)` in `saw_partials` to `range(1, n + 1, 2)`, and add `listen(Square(220.0) * 0.25, 1.5, "Square at gain 0.25")` (import `Square`). Which wave does the sum approach, and why does gain 0.25 on `Square` match its level?
2. `Square` takes a second parameter, `duty`: the fraction of each cycle it spends at +1. At `duty=0.5`, the default, it is the square of this chapter; at any other duty it is called a *pulse*. In the spectrum table, define `def quarter_pulse(freq): return Square(freq, duty=0.25)` and put `quarter_pulse` in place of `Square` in the tuple. Which harmonics are missing now?
3. In the block that builds the saw, raise the frequency from `220.0` to `2_000.0` in the `listen` line. How many harmonics are left below 24 000 Hz, and how does the 16-harmonic version compare with the 109-harmonic one?

### Answers

1. It approaches a square: the odd harmonics at 1/k are the square's spectrum. The amplitudes are 2/(πk) instead of the square's 4/(πk), half as large, and the sum then goes through gain 0.5, so it matches `Square` at 0.5 × 0.5 = 0.25. It points the other way, because the amplitudes are negative, and that does not change the sound.
2. Harmonics 4 and 8 are missing, and all the others are present, odd and even: a pulse with duty 0.25 no longer mirrors itself. Fourier's formula gives harmonic k of a pulse with duty d an amplitude proportional to sin(πkd) / k, which is zero whenever k × d is a whole number: here at k = 4, 8, 12 and so on.
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
