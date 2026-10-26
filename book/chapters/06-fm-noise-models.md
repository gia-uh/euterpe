# FM, noise and physical models

Chapter 3 built tones by adding sines, one per partial. Chapter 5 started from a source with many harmonics and filtered some away. This chapter adds three more ways to make a sound. *Frequency modulation* (FM) gets many partials out of two sines. *Noise* is sound with no pitch, and drums are mostly noise. *Physical models* compute what a vibrating object does: a plucked string and a struck bar or bell.

## Frequency modulation

Chapter 4 moved the frequency of a sine with an envelope, to make a bass drum. A slow sine can move it too. Here a sine at 440 Hz has its frequency pushed 10 Hz up and down, 5 times a second:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Sine

vibrato = Sine(Sine(5.0) * 10 + 440)
listen(vibrato * ADSR(gate=1.7, release=0.3) * 0.4, 2.2, "A sine at 440 Hz with 5 Hz vibrato")
```

This is *vibrato*: the pitch wobbles, as a singer's does on a held note. The inner `Sine(5.0)` is the *modulator*, the sine that does the moving. The outer one is the *carrier*, the sine that is heard. When the modulator is slow, the ear follows the pitch as it moves. When the modulator is itself at an audible frequency, a few hundred Hz, the pitch moves too fast to follow. The ear hears a single steady tone with a new timbre.

`FM(freq, ratio, index)` is that pair of sines in one unit. The carrier is at `freq`; the modulator is at `ratio × freq`. The modulator is added to the carrier's phase, the position in its cycle, scaled by `index`, so the carrier runs up to `index` radians ahead of or behind where it would be. Written out, the n-th sample is sin(2π × freq × t + index × sin(2π × ratio × freq × t)), with t = n / 48 000 in seconds. The block checks that this is all `FM` does:

```python {run output=code}
import numpy as np

from euterpe.sound import FM, render

t = np.arange(48_000) / 48_000
fm = render(FM(220.0, ratio=1.0, index=2.0), 1.0)
for f in (220.0, round(220 / 48_000 * 2**32) / 2**32 * 48_000):
    by_hand = np.sin(2 * np.pi * f * t + 2.0 * np.sin(2 * np.pi * f * t))
    print(f"{f:.7f} Hz: largest difference {np.abs(fm - by_hand).max():.1e}")
```

Against 220 Hz the two agree to about 0.00005. The gap is not in the formula but in the frequency. `FM`, like every oscillator in Euterpe, keeps its phase in a fixed-point counter that counts one cycle as 2³² steps, so it advances by a whole number of steps per sample: round(220 / 48 000 × 2³²). That is 220.0000025 Hz, and after one second the two waves have drifted 0.00005 apart. Against that frequency, the second line, they agree to 3 × 10⁻⁸, the rounding of 32-bit samples. Pushing the phase is the same as moving the frequency: a phase that runs ahead faster is a higher frequency. So this is also called *phase modulation*, and the two names are used for the same thing. The famous synthesizers that use it, such as Yamaha's DX7 of 1983, compute it this way.

### Sidebands

A modulated sine is no longer one frequency. Its spectrum is the carrier plus *sidebands*, partials at freq + m, freq − m, freq + 2m, freq − 2m and so on, where m = ratio × freq is the modulator's frequency. The level of the k-th pair is a known function of the index, the *Bessel function* J_k(index), which scipy computes. Here the carrier is at 1 000 Hz and the modulator at 0.15 × 1 000 = 150 Hz, so the sidebands sit 150 Hz apart. The block measures each one in the spectrum and prints it next to J_k(2):

```python {run output=code}
import numpy as np
from scipy.special import jv

from euterpe.sound import FM, render

x = render(FM(1000.0, ratio=0.15, index=2.0), 1.0)
amp = np.abs(np.fft.rfft(x)) * 2 / len(x)   # one bin per Hz: amp[f] is the level at f Hz
print(f"carrier: 1000 Hz {amp[1000]:.3f}, J_0(2) = {abs(jv(0, 2.0)):.3f}")
for k in range(1, 5):
    print(f"k={k}: {1000 + 150 * k} Hz {amp[1000 + 150 * k]:.3f}, {1000 - 150 * k} Hz {amp[1000 - 150 * k]:.3f}, J_k(2) = {abs(jv(k, 2.0)):.3f}")
```

The measured levels match the Bessel function: 0.224 for the carrier, 0.577 for the first pair, 0.353 for the second, and they keep falling. At index 2 the first sidebands are louder than the carrier. A rule of thumb (Carson's rule) says that about index + 1 pairs are loud, so a higher index spreads the energy wider and the tone gets brighter. The plot shows the spectrum at four indexes, with the modulator at the carrier's frequency, ratio 1.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import FM, render

fig, axes = plt.subplots(4, 1, figsize=(7, 5), sharex=True)
for ax, index in zip(axes, (0.0, 1.0, 3.0, 8.0)):
    x = render(FM(220.0, ratio=1.0, index=index), 1.0)
    amp = np.abs(np.fft.rfft(x)) * 2 / len(x)
    k = np.arange(1, 21) * 220
    ax.vlines(k, -80, np.maximum(20 * np.log10(amp[k] + 1e-9), -80), linewidth=2)
    ax.set_ylim(-80, 0)
    ax.set_ylabel("dB")
    ax.set_title(f"index {index:g}", fontsize=9, loc="left")
axes[-1].set_xlabel("frequency (Hz)")
fig.tight_layout()
show(fig, "The spectrum of FM at 220 Hz, ratio 1, at index 0, 1, 3 and 8")
```

With ratio 1, every sideband falls on a multiple of 220 Hz, because freq ± k × freq is always a whole number times freq. A sideband below 0 Hz, such as 220 − 2 × 220 = −220 Hz, is heard at +220 Hz, mirrored. So the result is harmonic, with the pitch of the carrier. Index 0 is a plain sine; index 8 has strong harmonics up to about the 9th.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, FM

for index in (0.0, 1.0, 3.0, 8.0):
    listen(FM(220.0, ratio=1.0, index=index) * ADSR(gate=1.0, release=0.2) * 0.4, 1.3, f"FM at 220 Hz, ratio 1, index {index:g}")
```

The pitch stays at 220 Hz while the tone goes from a flute-like sine to a buzz like a saw's. Two sines and one number did what chapter 3 needed dozens of partials for, which is why FM was cheap enough for the digital synthesizers of the 1980s.

### Ratios that are not whole numbers

When the ratio is not a whole number, the sidebands are not harmonics of the carrier. With freq 200 Hz and ratio 1.4, the modulator is at 280 Hz, and the sidebands sit at 200 ± 280 k: 480, 760, 1 040 … and, mirrored, 80, 360, 640 … Hz. These are all multiples of 40 Hz, but only a few of them: the 2nd, 5th, 9th, 12th, 16th, 19th … harmonics of 40 Hz, with most of the series missing. The ear does not fuse such a sparse set into one tone at 40 Hz, so it hears several pitches at once, as with chapter 3's metal bar.

### An index that moves

A struck bell is bright at first and mellows as it rings, because its high partials die sooner. In FM the index sets the brightness, so an envelope on the index gives the same effect. John Chowning, who discovered FM synthesis at Stanford in the late 1960s, made bells this way: a ratio of 1.4 and an index that falls from 10 to 0 together with the level.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, FM

def fading(seconds):
    return ADSR(attack=0.001, decay=seconds, sustain=0.0, gate=seconds, curve=0.8)

bell = FM(200.0, ratio=1.4, index=fading(4.0) * 10) * fading(4.0) * 0.35
listen(bell, 4.0, "An FM bell: ratio 1.4, the index falling from 10 to 0")
```

The same idea with ratio 1 and a quick fall of the index gives the electric-piano sound of many 1980s ballads. The index starts at 2.8, falls to 0.3 within half a second and stays there, so each note starts with a bright bark and settles into a nearly pure tone:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, FM

def epiano(freq):
    index = ADSR(attack=0.0, decay=0.4, sustain=0.0, gate=2.0, curve=0.7) * 2.5 + 0.3
    level = ADSR(attack=0.002, decay=1.6, sustain=0.0, gate=2.0, curve=0.7)
    return FM(freq, ratio=1.0, index=index) * level

listen((epiano(220.0) + epiano(277.18) + epiano(329.63)) * 0.25, 2.0, "An FM electric piano: an A major chord")
```

The three notes are A3, C♯4 and E4, the chord of A major. Each `epiano` builds its own envelopes, because a unit can appear only once in a graph (chapter 4).

### Feedback

`FM` has a fourth parameter, `feedback`, in radians from 0 to 1.5. It feeds the modulator's own last output back into its phase. A sine that pushes its own phase spends longer on one side of its cycle than the other, and as feedback rises it turns into something close to a saw, with harmonics of its own. Those harmonics then modulate the carrier, so feedback makes the tone brighter and rougher than the index alone can:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, FM, OnePole

for feedback in (0.0, 1.5):
    tone = OnePole(FM(110.0, ratio=1.0, index=1.5, feedback=feedback), 20.0, kind="highpass")
    listen(tone * ADSR(gate=1.0, release=0.2) * 0.4, 1.3, f"FM at 110 Hz, index 1.5, feedback {feedback:g}")
```

A modulator that leans to one side also pushes the carrier off-centre, so feedback adds a DC offset (chapter 4). The `OnePole` high-pass at 20 Hz removes it, as chapter 5 showed.

## The colours of noise

Chapter 5 used `WhiteNoise`, whose spectrum is flat: each band 100 Hz wide holds the same energy, on average, from 0 to 24 000 Hz. The ear does not hear in bands of equal width, though. It hears in octaves, and each octave is twice as wide as the one below it: 4 000 to 8 000 Hz is 4 000 Hz wide, 250 to 500 Hz only 250. So white noise puts more energy in each octave than in the one below, twice as much, 3 dB more, and it sounds bright, like hiss.

Two other noises are named after colours of light. The level per Hz of `PinkNoise(seed)` falls 3 dB per octave, which exactly cancels the doubling width: every octave holds the same energy. `BrownNoise(seed)` falls 6 dB per octave. It is not named after the colour but after Robert Brown, who described the random motion of pollen grains in water: each sample is the last one plus a small random step, the way a grain wanders. The block measures each noise's level, in dB, in bands 10 % wide starting at six frequencies an octave apart:

```python {run output=code}
import numpy as np

from euterpe.sound import BrownNoise, PinkNoise, WhiteNoise, render

for noise in (WhiteNoise(seed=1), PinkNoise(seed=1), BrownNoise(seed=1)):
    power = np.abs(np.fft.rfft(render(noise, 10.0))) ** 2
    f = np.fft.rfftfreq(480_000, 1 / 48_000)
    levels = [10 * np.log10(power[(f >= lo) & (f < 1.1 * lo)].mean()) for lo in (250, 500, 1000, 2000, 4000, 8000)]
    print(f"{type(noise).__name__:10}", [round(float(v - levels[0]), 1) for v in levels])
```

Each line is relative to its first band. White noise stays within a fraction of a dB: flat. Pink falls about 3 dB at each octave, to −15 at 8 000 Hz, five octaves above 250. Brown falls about 6 per octave, to −29.5.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, BrownNoise, OnePole, PinkNoise, WhiteNoise

listen(WhiteNoise(seed=1) * ADSR(gate=1.7, release=0.3) * 0.25, 2.2, "White noise")
listen(PinkNoise(seed=1) * ADSR(gate=1.7, release=0.3) * 1.0, 2.2, "Pink noise")
brown = OnePole(BrownNoise(seed=1), 20.0, kind="highpass")
listen(brown * ADSR(gate=1.7, release=0.3) * 1.0, 2.2, "Brown noise")
```

White noise hisses like a detuned radio. Pink sounds even from bottom to top, like steady rain; it is the noise engineers play through speakers to check them, because a meter that reads in octaves shows it flat. Brown is a deep roar, like surf heard from a distance. Brown noise has so much of its energy at the lowest frequencies that two seconds of it do not average 0, so a `OnePole` high-pass at 20 Hz (chapter 5) takes away what lies below hearing. `PinkNoise` and `BrownNoise` come out at an RMS level of 0.18, which is why they need a gain of 1.0 where white noise, at an RMS of 0.58, needs 0.25.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import BrownNoise, PinkNoise, WhiteNoise, render

fig, ax = plt.subplots(figsize=(7, 2.8))
for unit in (WhiteNoise(seed=1), PinkNoise(seed=1), BrownNoise(seed=1)):
    x = render(unit, 4.0)
    power = np.abs(np.fft.rfft(x)) ** 2 / len(x)
    edges = np.geomspace(30, 20_000, 40)
    f = np.fft.rfftfreq(len(x), 1 / 48_000)
    db = [10 * np.log10(power[(f >= a) & (f < b)].mean()) for a, b in zip(edges[:-1], edges[1:])]
    ax.semilogx(np.sqrt(edges[:-1] * edges[1:]), db, linewidth=1, label=type(unit).__name__)
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("dB per Hz")
ax.legend(fontsize=8)
show(fig, "The spectra of white, pink and brown noise: flat, 3 dB and 6 dB per octave down")
```

### Noise from a shift register

Early game consoles and home computers had no spare power to compute random numbers, so their sound chips made noise with a *linear-feedback shift register* (LFSR): a row of bits that shifts one place right at each step, while a new bit, the exclusive or (XOR) of the two lowest bits, comes in at the top. The lowest bit is the output, +1 or −1. The sequence looks random, but it repeats once the register returns to its starting state. The block counts the steps that takes, for a register of 7 bits and one of 15:

```python {run output=code}
for bits in (7, 15):
    state, steps = 1, 0
    while True:
        new_bit = (state ^ (state >> 1)) & 1
        state = (state >> 1) | (new_bit << (bits - 1))
        steps += 1
        if state == 1:
            break
    print(bits, "bits:", steps, "steps")
```

A register of b bits has 2^b − 1 states other than all zeros, and with this feedback it visits every one: 127 for 7 bits, 32 767 for 15. `LFSRNoise(rate, short=False, seed=1)` is that register, stepped `rate` times a second, each value held until the next step. Stepping faster moves the noise up, as a higher frequency moves a tone up. With `short=True` the register has 7 bits, and a sequence that repeats every 127 steps is a pitch: 12 000 / 127 = 94.5 Hz with many harmonics, a metallic buzz.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, LFSRNoise, OnePole

for rate in (2_000.0, 12_000.0):
    noise = OnePole(LFSRNoise(rate=rate), 20.0, kind="highpass")
    listen(noise * ADSR(gate=0.8, release=0.2) * 0.12, 1.2, f"LFSR noise stepped at {rate:.0f} Hz")
listen(LFSRNoise(rate=12_000.0, short=True) * ADSR(gate=0.8, release=0.2) * 0.12, 1.2, "Short LFSR noise at 12000 Hz: a 127-step loop")
```

Over a whole period the register gives one more +1 than −1, an average of 1 / 32 767, but one second at 2 000 steps covers only 2 000 of them, and those do not average 0: the high-pass at 20 Hz takes that offset away. The short register repeats every 127 steps, so it averages 1 / 127 over any whole number of loops, too little to matter.

### Tables of steps

The same chips played tones from a *wavetable*: one cycle of a wave stored as a short list of numbers, read out over and over. `Wavetable(table, freq)` plays any list as one cycle, `freq` times a second, holding each value as a step. A chip of that era stored 32 values of 4 bits each, 16 possible levels. The block below rounds one cycle of a sine to those 16 levels and plays it next to the true sine. Rounding moves some steps up more than others, so the table's average is not quite 0; subtracting its mean centres it, so it has no DC offset (chapter 4).

```python {run}
import numpy as np

from euterpe.book import listen
from euterpe.sound import ADSR, Sine, Wavetable

table = np.round((np.sin(2 * np.pi * np.arange(32) / 32) + 1) * 7.5) / 7.5 - 1
table = table - table.mean()
listen(Sine(220.0) * ADSR(gate=1.0, release=0.2) * 0.4, 1.3, "A sine at 220 Hz")
listen(Wavetable(table, 220.0) * ADSR(gate=1.0, release=0.2) * 0.4, 1.3, "A 32-step, 16-level sine at 220 Hz")
```

The stepped sine has the same pitch and a thin buzz on top. The steps repeat 32 times per cycle, so they add partials near 32 × 220 = 7 040 Hz and its multiples. That buzz is what game music of the 1980s sounds like.

## Noise as drums

Most of a drum's sound has no pitch. A cymbal is a thin plate that vibrates at thousands of unrelated frequencies at once, which the ear hears as noise; a snare drum has a set of wires stretched under its lower skin that rattle against it. So drums are built from noise, filtered to the band where the real drum has its energy and shaped by a short envelope.

A hi-hat, the pair of small cymbals a drummer plays on most beats, has its energy above about 7 000 Hz. A high-pass at 7 000 Hz keeps that band. A closed hi-hat lasts about 50 ms, an open one about 0.4 s:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Biquad, WhiteNoise

def hat(decay):
    env = ADSR(attack=0.001, decay=decay, sustain=0.0, release=0.0, gate=1.0, curve=0.8)
    return Biquad(WhiteNoise(seed=1), "highpass", cutoff=7000.0) * env * 0.6

listen(hat(0.05), 0.5, "A closed hi-hat: high-passed noise, 50 ms")
listen(hat(0.4), 1.0, "An open hi-hat: the same noise, 0.4 s")
```

A snare drum has two parts: the skin, struck, gives a short tone near 180 Hz whose pitch drops a little, as the bass drum of chapter 4 did; the wires give a burst of noise above 1 000 Hz that lasts longer than the tone. The snare is the sum of the two:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Biquad, Sine, WhiteNoise

def snare():
    pitch = ADSR(attack=0.0, decay=0.04, sustain=0.0, gate=1.0) * 60 + 180
    skin = Sine(pitch) * ADSR(attack=0.001, decay=0.12, sustain=0.0, release=0.0, gate=1.0, curve=0.7)
    wires = Biquad(WhiteNoise(seed=2), "highpass", cutoff=1000.0) * ADSR(attack=0.001, decay=0.22, sustain=0.0, release=0.0, gate=1.0, curve=0.8)
    return skin * 0.35 + wires * 0.3

listen(snare(), 0.6, "A snare: a falling tone at 240 to 180 Hz and high-passed noise")
```

Remove `skin` and the snare loses its body: it becomes a hiss with no weight. Remove `wires` and it is a dull knock on a box.

## A string you can pluck

A guitar string, plucked, starts with the shape the finger gave it. That shape runs along the string in both directions, reflects at both ends, and comes back. A wave that goes round a loop and comes back again and again is exactly the comb filter of chapter 5. In 1983 Kevin Karplus and Alex Strong found that a comb with a small filter inside its loop makes a convincing string. Their method, *Karplus–Strong synthesis*, is built here in three steps.

### Step 1: noise in a delay line

The pluck is a short burst of noise, one period long: at 220 Hz, 1/220 s, 4.5 ms. It goes into a comb whose delay is the same period and whose feedback is 0.996, so it circulates and comes back 220 times a second, losing 0.4 % at each trip. `Segments` makes the burst's envelope: 1 from the start to 1/220 s, then 0. The burst's 219 random samples (from sample 0 to sample 218, where 1/220 s falls) do not average exactly 0, and the comb boosts 0 Hz as much as it boosts each harmonic, so a `OnePole` high-pass at 20 Hz removes that offset, as in chapter 5. The `ADSR` at the end, with no attack and full sustain, only fades the note out over 0.4 s from 2.4 s on, as a hand laid on the string would, so that the sound ends before the file does.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Comb, OnePole, Segments, WhiteNoise

burst = WhiteNoise(seed=1) * Segments([(0.0, 1.0), (1 / 220, 1.0), (1 / 220, 0.0)])
string = OnePole(Comb(burst, delay=1 / 220, feedback=0.996), 20.0, kind="highpass")
listen(string * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 0.25, 3.0, "A burst of noise circulating in a comb at 220 Hz")
```

It has a pitch, 220 Hz, because the burst repeats every 1/220 s, and a sound that repeats f times a second has the harmonics of f (chapter 3). But it does not sound like a string. It buzzes, with a hard, electric edge, and its tone never changes as it fades, because the comb loses the same 0.4 % at every frequency.

### Step 2: the averaging filter

A real string loses its high harmonics sooner than its low ones. Karplus and Strong put the simplest low-pass there is inside the loop: each sample that comes back is the average of two neighbouring samples, (y[n − N] + y[n − N − 1]) / 2, where N is the delay in samples. Averaging two samples cancels what changes fast between them, so a sine at f Hz comes out of it at cos(π × f / 48 000) of its level: 1 at 0 Hz, falling to 0 at 24 000 Hz. The loss multiplies on every trip, and a note at 220 Hz makes 220 trips a second. The block computes what one second does to each harmonic, with damping 0.996 on top:

```python {run output=code}
import numpy as np

for k in (1, 5, 20, 50):
    f = 220 * k
    per_trip = 0.996 * np.cos(np.pi * f / 48_000)
    print(f"harmonic {k:2} ({f:5} Hz): {20 * np.log10(per_trip ** 220):7.1f} dB in one second")
```

The first harmonic loses 7.9 dB in a second and the fifth 12.6. The twentieth loses 88, so it falls 60 dB in under a second, and the fiftieth, at 11 000 Hz, loses 553: it is gone in about a tenth of a second. So the note starts bright and becomes rounder as it rings, which is the sound of a plucked string. The first sound in this chapter with the averaging filter in its loop is `Pluck`, after step 3; the spectrogram there sets it beside the comb of step 1.

### Step 3: the exact pitch

The delay line holds a whole number of samples, N, and the averaging filter adds half a sample of delay, because its output sits halfway between the two samples it averages. So the loop is N + 0.5 samples long, and the best N is the one that brings N + 0.5 closest to the period: round(period − 0.5). For 220 Hz the period is 48 000 / 220 = 218.2 samples, the best loop is 218.5, and it plays at 48 000 / 218.5 = 219.7 Hz. The loop can miss the period by up to half a sample, and half a sample is a larger part of a shorter period, so the possible error grows with the pitch. The block computes it for five A's, from A2 to A6, in cents (chapter 2: 100 cents is a semitone):

```python {run output=code}
import numpy as np

for f in (110, 220, 440, 880, 1760):
    played = 48_000 / (round(48_000 / f - 0.5) + 0.5)
    print(f"{f:4} Hz: plays {played:7.2f} Hz, {1200 * np.log2(played / f):6.1f} cents")
```

How far each note is off depends on where its period falls between two loop lengths: 880 Hz has a period of 54.55 samples, and 54.5 is almost exact, 1.4 cents. 1 760 Hz has 27.27 samples, and the nearest loop, 27.5, is 14 cents flat, a seventh of a semitone, which a trained ear hears in a chord. At the worst, half a sample out of 27.27 would be 1200 × log₂(27.77 / 27.27) = 31 cents. The higher the note, the worse the worst case, and a string instrument must be in tune everywhere. The fix, from David Jaffe and Julius Smith's paper of the same year, is a third filter in the loop: a first-order *allpass*, like chapter 5's but with a delay of one sample, which passes every frequency at its level and delays it by any fraction of a sample its coefficient asks for. With it the loop can be any length, not only a whole number of samples plus a half.

### Pluck

`Pluck(freq, damping, brightness, position, seed)` is the burst, the delay line, the averaging filter and the allpass in one unit. Here it is with the same damping as the comb of step 1, 0.4 % lost per trip:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Pluck

note = Pluck(220.0, damping=0.996, seed=1)
listen(note * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 0.8, 3.0, "A plucked A3", id="pluck-a3")
```

The line that makes `note` is the whole instrument. The `ADSR` is the same hand on the string as in step 1: left alone, at damping 0.996 the first harmonic loses 7.9 dB a second, so it takes 60 / 7.9 = 7.6 s to fall 60 dB. The spectrogram shows the difference from step 1: in the comb, every harmonic fades at the same rate; in the pluck, the high ones vanish first.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import spectrogram

from euterpe.book import show
from euterpe.sound import Comb, Pluck, Segments, WhiteNoise, render

burst = WhiteNoise(seed=1) * Segments([(0.0, 1.0), (1 / 220, 1.0), (1 / 220, 0.0)])
fig, axes = plt.subplots(1, 2, figsize=(8, 2.8), sharey=True)
for ax, unit, title in ((axes[0], Comb(burst, delay=1 / 220, feedback=0.996), "comb (step 1)"), (axes[1], Pluck(220.0, damping=0.996, seed=1), "Pluck")):
    x = render(unit, 2.0)
    f, t, s = spectrogram(x, fs=48_000, nperseg=2048, noverlap=1536)
    db = 10 * np.log10(s + 1e-14)
    ax.pcolormesh(t, f, db, shading="auto", vmin=db.max() - 70, vmax=db.max(), cmap="magma", rasterized=True)
    ax.set_ylim(0, 6000)
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("time (s)")
axes[0].set_ylabel("frequency (Hz)")
show(fig, "A burst circulating in a comb, and the same idea as Pluck: in the pluck the high harmonics die first")
```

`Pluck`'s burst is not raw noise. One period of raw noise gives each harmonic a random level, so with some seeds the octave above the note is louder than the note itself, and the same note played with two seeds differs in loudness and tone. `Pluck` sets the level of each harmonic and draws only their phases from the seed. The k-th harmonic starts at 1 / (1 + (k × freq / cutoff)²), with cutoff = freq × 2^(8 × brightness): `brightness=0` puts the cutoff at the note itself, so the harmonics start at about 1/k², the spectrum of a string pulled into a triangle by a finger; `brightness=1` puts it at the 256th harmonic, as bright as raw noise.

`damping` is the gain of one trip round the loop, between 0.9 and 0.9999. Above 1, each trip would make the sound louder and it would grow without end, so `Pluck` refuses it. The three plucks below differ only in damping:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Pluck

for damping in (0.99, 0.996, 0.999):
    listen(Pluck(220.0, damping=damping, seed=1) * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 0.8, 3.0, f"A plucked A3, damping {damping}")
```

At 0.99 the note is short and muffled, like a string damped by the palm of the hand. At 0.999 it rings like a harp. `brightness` is the softness of what plucks it, from a fingertip (dark) to a hard plectrum (bright). `Pluck` gives every burst the same energy (unless that would put its peak above 0.9), but a bright burst holds much of it in high harmonics, and step 2 showed that those are gone within a fraction of a second. So over the whole note a bright pluck is quieter. The gains 0.49, 0.58 and 1.15 compensate, so the three differ in tone and not in loudness, and the second block measures them:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Pluck

plucks = {}
for brightness, gain in ((0.1, 0.49), (0.5, 0.58), (0.9, 1.15)):
    plucks[brightness] = Pluck(220.0, brightness=brightness, seed=1) * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * gain
    listen(plucks[brightness], 3.0, f"A plucked A3, brightness {brightness}")
```

```python {run continue output=code}
from euterpe.lint import lint_audio
from euterpe.sound import render

for brightness, unit in plucks.items():
    print("brightness", brightness, ":", [f.message for f in lint_audio(render(unit, 3.0)).findings if f.rule == "A-LUFS"])
```

`position` is where the string is plucked, as a fraction of its length from one end, from 0 to 0.5. A string plucked at its middle cannot vibrate in any pattern that needs the middle to stand still, and those are the even harmonics: the 2nd has a still point at the middle, the 4th too, and so on. So `position=0.5` removes every even harmonic, and the tone turns hollow, as the square of chapter 3 does. Guitarists play near the bridge, at about 0.1, for a thin, bright tone, and over the sound hole, nearer 0.25, for a round one:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Pluck

for position in (0.1, 0.25, 0.5):
    listen(Pluck(220.0, damping=0.998, brightness=0.8, position=position, seed=1) * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 1.05, 3.0, f"A plucked A3, position {position}")
```

Strings are often played together. Five plucks at once are a strummed chord, held a little longer:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Pluck

chord = Pluck(110.0, seed=1) + Pluck(164.81, seed=2) + Pluck(220.0, seed=3) + Pluck(277.18, seed=4) + Pluck(329.63, seed=5)
listen(chord * ADSR(attack=0.0, sustain=1.0, gate=3.0, release=0.5) * 0.4, 3.7, "An A major chord on five plucked strings")
```

The notes are A2, E3, A3, C♯4 and E4, the shape of an A chord on a guitar. They all start at the same instant, which a strum does not quite do; scores, later in the book, place notes in time.

## Modes: bars and bells

A struck object does not vibrate at one frequency or at harmonics, but in *modes*: patterns of motion, each with its own frequency and its own decay time. Chapter 3 played the four lowest modes of a free metal bar, at 1, 2.76, 5.40 and 8.93 times its lowest frequency, as steady sines. Struck, each mode starts at once and then rings down, the high ones faster, because a faster vibration loses more energy per second to the air and to friction inside the metal.

`Modal(freqs, decays, amps)` makes each mode with a *resonator*, a two-pole filter that rings as a sine at its frequency when it is struck. Each mode has a frequency in Hz, an amplitude and a decay time: the seconds it takes to fall by 60 dB, a thousandth of its starting level. With no other argument, all of them are struck at once, by a single sample of 1 at the start.

```python {run}
from euterpe.book import listen
from euterpe.sound import Modal

ratios = [1, 2.76, 5.40, 8.93]
bar = Modal([440 * r for r in ratios], decays=[1.2, 0.5, 0.25, 0.12], amps=[1.0, 0.5, 0.3, 0.2])
listen(bar * 0.3, 2.0, "A struck bar at 440 Hz: four modes")
```

It is a xylophone or a glockenspiel, depending on what you imagine striking it. The 60 dB is a rule of acousticians: it is about how far a sound falls before it is lost in the quiet of an ordinary room. The block measures how far the first mode has fallen at its decay time, 1.2 s, by rendering the first mode alone:

```python {run continue output=code}
import numpy as np

from euterpe.sound import Modal, render

first = render(Modal([440.0], [1.2], [1.0]), 1.3)
start, at_decay = np.abs(first[:4800]).max(), np.abs(first[57_120:57_600]).max()
print(round(float(20 * np.log10(at_decay / start)), 1), "dB after 1.2 s")
```

It has fallen 59.5 dB, close to the 60 its decay time promises. The two levels are peaks read in short windows, the first 0.1 s and the 10 ms that end at 1.2 s, so the second peak comes from a moment up to 10 ms before 1.2 s, when the mode had not quite finished its fall. The spectrogram shows the four modes as four lines, the higher ones shorter:

```python {run continue echo=false}
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import spectrogram

from euterpe.book import show
from euterpe.sound import Modal, render

x = render(Modal([440 * r for r in ratios], decays=[1.2, 0.5, 0.25, 0.12], amps=[1.0, 0.5, 0.3, 0.2]), 2.0)
f, t, s = spectrogram(x, fs=48_000, nperseg=2048, noverlap=1536)
db = 10 * np.log10(s + 1e-14)
fig, ax = plt.subplots(figsize=(7, 2.8))
ax.pcolormesh(t, f, db, shading="auto", vmin=db.max() - 70, vmax=db.max(), cmap="magma", rasterized=True)
ax.set_ylim(0, 5000)
ax.set_xlabel("time (s)")
ax.set_ylabel("frequency (Hz)")
show(fig, "The struck bar over time: each line is a mode, and the higher ones die sooner")
```

### What strikes it

A single sample is the hardest strike possible: it has every frequency at the same level, so every mode starts at its full amplitude. A soft mallet touches the bar for a few milliseconds and pushes less at high frequencies. `Modal` takes the strike as a fourth argument, `excite`, any unit. Here the excitation is 5 ms of noise through a low-pass at 1 500 Hz:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Biquad, Modal, WhiteNoise

mallet = Biquad(WhiteNoise(seed=1), "lowpass", cutoff=1500.0) * ADSR(attack=0.0, decay=0.005, sustain=0.0, release=0.0, gate=1.0)
soft = Modal([440 * r for r in [1, 2.76, 5.40, 8.93]], decays=[1.2, 0.5, 0.25, 0.12], amps=[1.0, 0.5, 0.3, 0.2], excite=mallet)
listen(soft * 0.1, 2.0, "The same bar struck with a soft mallet")
```

The pitch and the decay are the same; the attack has lost its click, and the upper modes are quieter. The gain is 0.1 where the struck bar had 0.3, although the mallet is quieter than a sample of 1. A resonator keeps adding up whatever part of its input arrives in step with its own ringing, so 5 ms of noise, 240 samples, puts more energy into the low modes than one sample of 1 does.

### A bell

A church bell is shaped so that its lowest modes fall close to musical intervals. The *strike note* the ear hears sits on the mode called the prime; below it is the *hum*, an octave lower; above it a minor third (1.2 times), a fifth (1.5), the *nominal* an octave up (2), and higher modes above that. The ratios below are close to those of a tuned bell, and the low modes ring for many seconds:

```python {run}
from euterpe.book import listen
from euterpe.sound import Modal

ratios = [0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.2]
decays = [6.0, 4.0, 3.5, 3.0, 2.5, 1.5, 1.0, 0.6]
amps = [0.6, 1.0, 0.7, 0.5, 0.8, 0.4, 0.3, 0.2]
listen(Modal([220 * r for r in ratios], decays, amps) * 0.18, 5.0, "A bell with its prime at 220 Hz: eight modes")
```

The minor third at 1.2 gives a bell its slightly sad colour. Compare it with the FM bell earlier in the chapter: FM made inharmonic partials from two sines and one ratio, and put every one of them where the ratio placed it; the modal bell takes each frequency, level and decay from a list, so it can copy a real object that has been measured. FM is cheap and has few knobs. A modal model costs one filter per mode and can be as exact as the measurements behind it.

## Summary

- `FM(freq, ratio, index, feedback)` is a sine at `freq` whose phase is moved by a second sine at `ratio × freq`, by up to `index` radians. Its spectrum is the carrier and sidebands at freq ± k × ratio × freq, at the levels of the Bessel functions J_k(index); about index + 1 pairs are loud.
- A whole-number ratio gives harmonics; any other ratio gives inharmonic, bell-like partials. An envelope on the index makes the brightness move: bells, electric pianos. `feedback` turns the modulator into a near-saw and adds roughness.
- White noise is flat per Hz, so each octave holds 3 dB more than the one below. `PinkNoise` holds the same energy in every octave; `BrownNoise` falls 6 dB per octave.
- `LFSRNoise(rate, short, seed)` is the noise of early sound chips, a shift register stepped `rate` times a second; `short=True` repeats every 127 steps and buzzes. `Wavetable(table, freq)` plays a list of numbers as one cycle of a wave, in steps.
- Drums are mostly filtered noise under short envelopes: a hi-hat is noise above 7 000 Hz; a snare is noise plus a short falling tone.
- `Pluck(freq, damping, brightness, position, seed)` is Karplus–Strong: a burst one period long in a delay line, an averaging filter that removes the high harmonics sooner, and an allpass for the exact pitch. `damping` sets how long it rings, `brightness` how bright it starts, `position` which harmonics the pluck point removes.
- `Modal(freqs, decays, amps, excite)` is a bank of resonators, one per mode, each a decaying sine that falls 60 dB in its decay time. Bars and bells are lists of modes; `excite` is what strikes them.

## Exercises

1. In the FM bell, change `ratio=1.4` to `ratio=2.0`. Is it still a bell? Which harmonics of 200 Hz does it have?
2. In the plucked A3, change `damping=0.996` to `damping=0.98`. Use the averaging-filter block to work out how many dB the first harmonic now loses in one second.
3. In the hi-hat, change `cutoff=7000.0` to `cutoff=1500.0`. What does the closed hat sound like now?

### Answers

1. It is no longer a bell. The sidebands are at 200 ± 400 k Hz: 600, 1 000, 1 400 Hz above and, mirrored, 200, 600, 1 000 Hz from below, all odd multiples of 200 Hz. Only odd harmonics, as in the square of chapter 3, so the tone is hollow, close to a clarinet, and it has a clear pitch at 200 Hz.
2. Each trip now keeps 0.98 × cos(π × 220 / 48 000) of the first harmonic, and 220 trips a second give 20 × log₁₀ of that to the 220th power: about −38.8 dB in one second, about five times as much as at 0.996. The note dies within a second and sounds muted, like a pizzicato on a violin.
3. It sounds less like metal and more like a shaker, or brushes on a snare. The level hardly changes: white noise has the same energy in every Hz, so keeping 24 000 − 1 500 = 22 500 Hz of it instead of 24 000 − 7 000 = 17 000 Hz is 22 500 / 17 000 = 1.32 times the power, 1.2 dB. What changes is the timbre: the hat now holds the band from 1 500 to 7 000 Hz, where the ear is most sensitive, so it sounds fuller and less like a cymbal.

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
