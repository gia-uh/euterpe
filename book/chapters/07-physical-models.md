# Physical models

Chapters 3 and 6 described a sound by its spectrum, the partials it should have, and built it out of sines, filters and noise. A *physical model* starts from the object instead: a string, a bar, a bell. It computes how the object moves once something sets it going, and the sound is that motion. The model needs only two parts. One is something that holds the vibration and loses a little of it on each cycle: the delay line and comb of chapter 5, or a filter that rings. The other is the energy that sets it going, a pluck or a strike, which is a short burst of the noise of chapters 5 and 6. This chapter builds a plucked string from the first part and a struck bar and a bell from resonators.

## A string you can pluck

A guitar string, plucked, starts with the shape the finger gave it. That shape runs along the string in both directions, reflects at both ends, and comes back. A wave that goes round a loop and comes back again and again is exactly the comb filter of chapter 5. In 1983 Kevin Karplus and Alex Strong found that a comb with a small filter inside its loop makes a convincing string. Their method, *Karplus–Strong synthesis*, is built here in three steps.

### Step 1: noise in a delay line

The pluck is a short burst of noise, one period long: at 220 Hz, 1/220 s, 4.5 ms. It goes into a comb whose delay is the same period and whose feedback is 0.996, so it circulates and comes back 220 times a second, losing 0.4 % at each trip. `Segments` (chapter 5) holds the noise at 1 for samples 0 to 218, the first 1/220 s, then at 0. A `OnePole` high-pass at 20 Hz removes the small offset of those 219 random samples, which the comb would otherwise build up. The `ADSR`, with no attack and full sustain, only fades the note out from 2.4 s, as a hand laid on the string would.

```python {run}
from euterpe.sound import ADSR, Comb, OnePole, Segments, WhiteNoise

burst = WhiteNoise(seed=1) * Segments([(0.0, 1.0), (1 / 220, 1.0), (1 / 220, 0.0)])
string = OnePole(Comb(burst, delay=1 / 220, feedback=0.996), 20.0, kind="highpass")
display((string * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 0.25).take(3.0, "A burst of noise circulating in a comb at 220 Hz"))
```

It has a pitch, 220 Hz, because the burst repeats every 1/220 s, and a sound that repeats f times a second has the harmonics of f (chapter 3). But it does not sound like a string. It buzzes, with a hard, electric edge, and its tone never changes as it fades, because the comb loses the same 0.4 % at every frequency.

### Step 2: the averaging filter

A real string loses its high harmonics sooner than its low ones. Karplus and Strong put the simplest low-pass there is inside the loop: each sample that comes back is the average of two neighbouring samples, (y[n − N] + y[n − N − 1]) / 2, where N is the delay in samples. Averaging two samples cancels what changes fast between them. For a sine at f Hz, write a = 2π × f × n / 48 000 for sample n and b = 2π × f × (n − 1) / 48 000 for the one before; the identity sin a + sin b = 2 sin((a + b) / 2) cos((a − b) / 2) gives (sin a + sin b) / 2 = cos(π × f / 48 000) × sin(2π × f × (n − ½) / 48 000). So the average is the same sine, delayed by half a sample, at cos(π × f / 48 000) of its level: 1 at 0 Hz, falling to 0 at 24 000 Hz. The loss multiplies on every trip, and a note at 220 Hz makes 220 trips a second. The block computes what one second does to each harmonic, with damping 0.996 on top:

```python {run output=code}
import numpy as np

for k in (1, 5, 20, 50):
    f = 220 * k
    per_trip = 0.996 * np.cos(np.pi * f / 48_000)
    print(f"harmonic {k:2} ({f:5} Hz): {20 * np.log10(per_trip ** 220):7.1f} dB in one second")
```

The first harmonic loses 7.9 dB in a second and the fifth 12.6. The twentieth loses 88, so it falls 60 dB in under a second, and the fiftieth, at 11 000 Hz, loses 553: it is gone in about a tenth of a second. So the note starts bright and becomes rounder as it rings, which is the sound of a plucked string. The first sound in this chapter with the averaging filter in its loop is `Pluck`, after step 3; the spectrogram there sets it beside the comb of step 1.

### Step 3: the exact pitch

The delay line holds a whole number of samples, N, and the averaging filter adds the half sample of delay that step 2's identity found. So the loop is N + 0.5 samples long, and the best N is the one that brings N + 0.5 closest to the period: round(period − 0.5). For 220 Hz the period is 48 000 / 220 = 218.2 samples, the best loop is 218.5, and it plays at 48 000 / 218.5 = 219.7 Hz. The loop can miss the period by up to half a sample, and half a sample is a larger part of a shorter period, so the possible error grows with the pitch. The block computes it for five A's, from A2 to A6, in cents (chapter 2: 100 cents is a semitone):

```python {run output=code}
import numpy as np

for f in (110, 220, 440, 880, 1760):
    played = 48_000 / (round(48_000 / f - 0.5) + 0.5)
    print(f"{f:4} Hz: plays {played:7.2f} Hz, {1200 * np.log2(played / f):6.1f} cents")
```

How far each note is off depends on where its period falls between two loop lengths: 880 Hz has a period of 54.55 samples, and 54.5 is almost exact, 1.4 cents. 1 760 Hz has 27.27 samples, and the nearest loop, 27.5, is 14 cents flat, a seventh of a semitone, which a trained ear hears in a chord. At the worst, half a sample out of 27.27 would be 1200 × log₂(27.77 / 27.27) = 31 cents. The higher the note, the worse the worst case, and a string instrument must be in tune everywhere. The fix, from David Jaffe and Julius Smith's paper of the same year, is a third filter in the loop, a first-order *allpass*: y[n] = c × x[n] + x[n − 1] − c × y[n − 1]. It is chapter 5's allpass with a delay of one sample and gain −c, so it passes every frequency at its level. At low frequencies, where a string's pitch lies, it delays the signal by (1 − c) / (1 + c) samples, so the coefficient c = (1 − d) / (1 + d) gives any fraction d of a sample. With it the loop can be any length, not only a whole number of samples plus a half.

### Pluck

`Pluck(freq, damping=0.996, brightness=0.5, position=0.0, seed=0)` is the burst, the delay line, the averaging filter and the allpass in one unit. Here it is with the default damping, the same 0.4 % lost per trip as the comb of step 1:

```python {run}
from euterpe.sound import ADSR, Pluck

note = Pluck(220.0, damping=0.996, seed=1)
display((note * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 0.6).take(3.0, "A plucked A3"))
```

The line that makes `note` is the whole instrument. The `ADSR` is the same hand on the string as in step 1: left alone, at damping 0.996 the first harmonic loses 7.9 dB a second, so it takes 60 / 7.9 = 7.6 s to fall 60 dB. The spectrogram shows the difference from step 1: in the comb, every harmonic fades at the same rate; in the pluck, the high ones vanish first.

```python {run echo=false}
from euterpe.sound import Comb, Pluck, Segments, WhiteNoise
from euterpe.view import spectrogram

burst = WhiteNoise(seed=1) * Segments([(0.0, 1.0), (1 / 220, 1.0), (1 / 220, 0.0)])
spectrogram(
    Comb(burst, delay=1 / 220, feedback=0.996).take(2.0), Pluck(220.0, damping=0.996, seed=1).take(2.0),
    labels=["comb (step 1)", "Pluck"], lo=110, hi=6000,
    caption="A burst circulating in a comb, and the same idea as Pluck: in the pluck the high harmonics die first",
)
```

`Pluck`'s burst is not raw noise. One period of raw noise gives each harmonic a random level, so with some seeds the octave above the note is louder than the note itself, and the same note played with two seeds differs in loudness and tone. `Pluck` sets the level of each harmonic and draws only their phases from the seed. The k-th harmonic starts at 1 / (1 + (k × freq / cutoff)²), with cutoff = freq × 2^(8 × brightness): This curve is the gain of two of chapter 5's one-pole low-passes in a row, each with gain 1 / √(1 + (f / cutoff)²). `brightness=0` puts the cutoff at the note itself, so the harmonics start at about 1/k². That is the spectrum of a string a finger has pulled aside at one point, so that it starts in the shape of a triangle; the triangle is the string's shape, not chapter 3's triangle wave, which falls as 1/k² too. `brightness=1` puts the cutoff at the 256th harmonic, as bright as raw noise.

`damping` is the gain of one trip round the loop, between 0.9 and 0.9999. Above 1, each trip would make the sound louder and it would grow without end, so `Pluck` refuses it. The three plucks below differ only in damping:

```python {run}
from euterpe.sound import ADSR, Pluck

for damping in (0.99, 0.996, 0.999):
    display((Pluck(220.0, damping=damping, seed=1) * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 0.6).take(3.0, f"A plucked A3, damping {damping}"))
```

At 0.99 the note is short and muffled, like a string damped by the palm of the hand. At 0.999 it rings like a harp. `brightness` is the softness of what plucks it, from a fingertip (dark) to a hard plectrum (bright). `Pluck` gives every burst the same energy (unless that would put its peak above 0.9), but a bright burst holds much of it in high harmonics, and step 2 showed that those are gone within a fraction of a second. So over the whole note a bright pluck is quieter. The gains 0.49, 0.58 and 1.15 compensate, so the three differ in tone and not in loudness, and match the plucked A3 above; the second block measures them:

```python {run}
from euterpe.sound import ADSR, Pluck

plucks = {}
for brightness, gain in ((0.1, 0.49), (0.5, 0.58), (0.9, 1.15)):
    plucks[brightness] = Pluck(220.0, brightness=brightness, seed=1) * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * gain
    display(plucks[brightness].take(3.0, f"A plucked A3, brightness {brightness}"))
```

```python {run continue output=code}
from euterpe.lint import lint_audio
from euterpe.sound import render

for brightness, unit in plucks.items():
    print("brightness", brightness, ":", [f.message for f in lint_audio(render(unit, 3.0)).findings if f.rule == "A-LUFS"])
```

`position` is where the string is plucked, as a fraction of its length from one end, from 0 to 0.5. The k-th harmonic of a string vibrates in k segments, with still points between them, at 1/k, 2/k … of its length. A pluck at a point where a harmonic stands still cannot set that harmonic moving, so plucking at 1/n of the length removes every harmonic that has a still point there: the n-th, the 2n-th, the 3n-th and so on. `position=0.5` removes every even harmonic, and the tone turns hollow, as the square of chapter 3 does; `position=0.25` removes the 4th, 8th, 12th …; `position=0.1` the 10th, 20th …; and `position=0`, the default, removes nothing. Guitarists play near the bridge, at about 0.1, for a thin, bright tone, and over the sound hole, nearer 0.25, for a round one. The three plucks below use `brightness=0.8`, so the harmonics a position removes are loud enough to be missed, and `damping=0.998`, so they ring long enough to compare; the gain of 1.05 brings them to the level of the others:

```python {run}
from euterpe.sound import ADSR, Pluck

for position in (0.1, 0.25, 0.5):
    display((Pluck(220.0, damping=0.998, brightness=0.8, position=position, seed=1) * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 1.05).take(3.0, f"A plucked A3, position {position}"))
```

## Modes: bars and bells

A struck object does not vibrate at one frequency or at harmonics, but in *modes*: patterns of motion, each with its own frequency and its own decay time. Chapter 3 played the four lowest modes of a free metal bar, at 1, 2.76, 5.40 and 8.93 times its lowest frequency, as steady sines. Struck, each mode starts at once and then rings down, the high ones faster, because a faster vibration loses more energy per second to the air and to friction inside the metal.

`Modal(freqs, decays, amps)` makes each mode with a *resonator*: a filter of order 2 (chapter 5: it feeds back its last two outputs), tuned so that when it is struck it rings as a sine at one frequency and dies away. Each mode has a frequency in Hz, an amplitude and a decay time: the seconds it takes to fall by 60 dB, a thousandth of its starting level. With no other argument, all of them are struck at once, by a single sample of 1 at the start.

```python {run}
from euterpe.sound import Modal
from euterpe.view import listen

ratios = [1, 2.76, 5.40, 8.93]
bar = Modal([440 * r for r in ratios], decays=[1.2, 0.5, 0.25, 0.12], amps=[1.0, 0.5, 0.3, 0.2])
listen(bar * 0.3, 2.0, "A struck bar at 440 Hz: four modes")
```

It is a xylophone or a glockenspiel, depending on what you imagine striking it. The 60 dB is a rule of acousticians: it is about how far a sound falls before it is lost in the quiet of an ordinary room. The block measures how far the first mode has fallen at its decay time, 1.2 s, by rendering the first mode alone. Sample indexes are seconds times 48 000: `first[:4800]` is the first 0.1 s, and `first[57_120:57_600]` the 10 ms from 1.19 s to 1.2 s. In each it takes the peak:

```python {run continue output=code}
import numpy as np

from euterpe.sound import Modal, render

first = render(Modal([440.0], [1.2], [1.0]), 1.3)
start, at_decay = np.abs(first[:4800]).max(), np.abs(first[57_120:57_600]).max()
print(round(float(20 * np.log10(at_decay / start)), 1), "dB after 1.2 s")
```

It has fallen 59.5 dB, close to the 60 its decay time promises: the second peak comes from up to 10 ms before 1.2 s, when the mode had not quite finished its fall. The spectrogram shows the four modes as four lines, the higher ones shorter:

```python {run continue echo=false}
from euterpe.sound import Modal

bar = Modal([440 * r for r in ratios], decays=[1.2, 0.5, 0.25, 0.12], amps=[1.0, 0.5, 0.3, 0.2])
bar.take(2.0).spectrogram(lo=220, hi=6000, caption="The struck bar over time: each line is a mode, and the higher ones die sooner")
```

### What strikes it

A single sample is the hardest strike possible: it has every frequency at the same level, so every mode starts at its full amplitude. A soft mallet touches the bar for a few milliseconds and pushes less at high frequencies. `Modal` takes the strike as a fourth argument, `excite`, any unit. Here the excitation is 5 ms of noise through a low-pass at 1 500 Hz:

```python {run}
from euterpe.sound import ADSR, Biquad, Modal, WhiteNoise

mallet = Biquad(WhiteNoise(seed=1), "lowpass", cutoff=1500.0) * ADSR(attack=0.0, decay=0.005, sustain=0.0, release=0.0, gate=1.0)
soft = Modal([440 * r for r in [1, 2.76, 5.40, 8.93]], decays=[1.2, 0.5, 0.25, 0.12], amps=[1.0, 0.5, 0.3, 0.2], excite=mallet)
display((soft * 0.1).take(2.0, "The same bar struck with a soft mallet"))
```

The pitch and the decay are the same; the attack has lost its click, and the upper modes are quieter beside the lowest. The gain is 0.1 where the struck bar had 0.3, so the mallet must have made the bar ring louder, though at every instant it is far quieter than a sample of 1. A resonator rings for a long time, so it keeps adding up each part of its input that arrives in step with its ringing. A sample of 1 is one push. The mallet is 240 small pushes over 5 ms, and at the frequencies of the lower modes they add up to more than that one push. At the highest mode, 8.93 × 440 = 3 930 Hz, which the low-pass at 1 500 Hz weakens, they add up to less.

### A bell

A church bell is shaped so that its lowest modes fall close to the equal steps of chapter 2. Take the mode at the note the ear hears as 1. Below it is a mode an octave lower, at 0.5. Above it are a mode 3 steps up, at 2^(3/12) = 1.19 times (musicians call that distance a *minor third*), one 7 steps up, at 2^(7/12) = 1.50 times (a *fifth*), one an octave up, at 2, and higher modes above those. The ratios below are close to those of a tuned bell, and the low modes ring for many seconds:

```python {run}
from euterpe.sound import Modal

ratios = [0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.2]
decays = [6.0, 4.0, 3.5, 3.0, 2.5, 1.5, 1.0, 0.6]
amps = [0.6, 1.0, 0.7, 0.5, 0.8, 0.4, 0.3, 0.2]
display((Modal([220 * r for r in ratios], decays, amps) * 0.18).take(5.0, "A bell with its prime at 220 Hz: eight modes"))
```

The mode a minor third up gives a tuned bell its particular colour. Compare it with the FM bell of chapter 6: FM made inharmonic partials from two sines and one ratio, and put every one of them where the ratio placed it; the modal bell takes each frequency, level and decay from a list, so it can copy a real object that has been measured. FM is cheap and has few knobs. A modal model costs one filter per mode and can be as exact as the measurements behind it.

## Summary

- A physical model computes the motion of an object: something that holds a vibration and loses part of it on every cycle, set going by a pluck or a strike.
- `Pluck(freq, damping, brightness, position, seed)` is Karplus–Strong: a burst one period long in a delay line, an averaging filter that removes the high harmonics sooner, and an allpass for the exact pitch. `damping` sets how long it rings, `brightness` how bright it starts, `position` which harmonics the pluck point removes.
- `Modal(freqs, decays, amps, excite)` is a bank of resonators, one per mode, each a decaying sine that falls 60 dB in its decay time. Bars and bells are lists of modes; `excite` is what strikes them.

## Exercises

1. In the plucked A3, change `damping=0.996` to `damping=0.98`. Use the averaging-filter block to work out how many dB the first harmonic now loses in one second.
2. In the plucked A3, add `position=0.2` to the `Pluck`. Which harmonics disappear, and at what frequencies are the first two of them?
3. In the struck bar, change `decays=[1.2, 0.5, 0.25, 0.12]` to `decays=[1.2, 1.2, 1.2, 1.2]`. How does the sound change as it fades?

### Answers

1. Each trip now keeps 0.98 × cos(π × 220 / 48 000) of the first harmonic, and 220 trips a second give 20 × log₁₀ of that to the 220th power: about −38.8 dB in one second, about five times as much as at 0.996. By the 60 dB rule the note lasts 60 / 38.8 = 1.5 s instead of 7.6 s, and it sounds muted, like a pizzicato on a violin.
2. Plucking at 0.2 = 1/5 of the length removes every harmonic with a still point there: the 5th, 10th, 15th and so on. The first two are at 5 × 220 = 1 100 Hz and 10 × 220 = 2 200 Hz.
3. Every mode now rings for 1.2 s, so the high ones no longer die first. The bar no longer mellows towards its lowest mode as it fades: it stays as bright and as metallic at the end as at the strike. A real bar does not do this, because a faster vibration loses more energy per second; in the spectrogram the four lines would all be the same length.

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
