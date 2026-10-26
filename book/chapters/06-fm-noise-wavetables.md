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

`FM(freq, ratio, index)` is that pair of sines in one unit. The carrier is at `freq`; the modulator is at `ratio × freq`. The modulator is added to the carrier's phase, the position in its cycle, scaled by `index`, so the carrier runs up to `index` radians ahead of or behind where it would be. Written out, the n-th sample is sin(2π × freq × t + index × sin(2π × ratio × freq × t)), with t = n / 48 000 in seconds.

Pushing the phase is the same as moving the frequency: a phase that runs ahead faster is a higher frequency. The rate of change of index × sin(2π × m × t), divided by 2π, is index × m × cos(2π × m × t), so the frequency swings up and down by at most index × m Hz, where m = ratio × freq is the modulator's frequency. The vibrato above moved 10 Hz at 5 Hz: as phase modulation that is index 10 / 5 = 2. So FM is also called *phase modulation*, and the two names are used for the same thing. The famous synthesizers that use it, such as Yamaha's DX7 of 1983, compute it this way.

### Sidebands

A modulated sine is no longer one frequency. Its spectrum is the carrier plus *sidebands*, partials at freq + m, freq − m, freq + 2m, freq − 2m and so on, where m = ratio × freq is the modulator's frequency. The level of the k-th pair is a known function of the index, the *Bessel function* J_k(index). Its formula is beyond this book; treat it as a table of levels that scipy looks up for you, as you use `np.sin` without deriving it. Here the carrier is at 1 000 Hz and the modulator at 0.15 × 1 000 = 150 Hz, so the sidebands sit 150 Hz apart. The block measures each one in the spectrum and prints it next to J_k(2):

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

The measured levels match the formula: 0.224 for the carrier, 0.577 for the first pair, 0.353 for the second, and they keep falling. The block prints `abs(jv(...))` because a spectrum's level has no sign, but J_k can be negative, and the lower sideband of an odd k has the opposite sign of the upper one. The sign matters when two partials land on the same frequency, as the next section shows. At index 2 the first sidebands are louder than the carrier. A rule of thumb (Carson's rule) says that about index + 1 pairs are loud, so a higher index spreads the energy wider and the tone gets brighter. The plot shows the spectrum at four indexes, with the modulator at the carrier's frequency, ratio 1.

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

With ratio 1, every sideband falls on a multiple of 220 Hz, because freq ± k × freq is always a whole number times freq. So the result is harmonic, with the pitch of the carrier. Index 0 is a plain sine; index 8 has strong harmonics up to about the 9th.

A sideband below 0 Hz, such as 220 − 2 × 220 = −220 Hz, is heard at +220 Hz, mirrored, and a sine at −f is the sine at f turned upside down. Here it lands on the carrier, and the two add with their signs: the carrier's level becomes J_0 − J_2. At index 3:

```python {run output=code}
import numpy as np
from scipy.special import jv

from euterpe.sound import FM, render

x = render(FM(220.0, ratio=1.0, index=3.0), 1.0)
amp = np.abs(np.fft.rfft(x)) * 2 / len(x)
print("measured at 220 Hz:", round(float(amp[220]), 3))
print("J_0(3) =", round(float(jv(0, 3.0)), 3), " J_2(3) =", round(float(jv(2, 3.0)), 3), " J_0 - J_2 =", round(float(jv(0, 3.0) - jv(2, 3.0)), 3))
```

J_0(3) is −0.260 and J_2(3) is 0.486, so J_0 − J_2 = −0.746, and its size, 0.746, is what the spectrum shows. Here the two pull the same way; at other indexes they have opposite signs and partly cancel, which is why a harmonic of an FM tone can grow and shrink as the index rises.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, FM

for index in (0.0, 1.0, 3.0, 8.0):
    listen(FM(220.0, ratio=1.0, index=index) * ADSR(gate=1.0, release=0.2) * 0.4, 1.3, f"FM at 220 Hz, ratio 1, index {index:g}")
```

The pitch stays at 220 Hz while the tone goes from a flute-like sine to a buzz like a saw's. Two sines and one number did what chapter 3 needed dozens of partials for, which is why FM was cheap enough for the digital synthesizers of the 1980s.

### Ratios that are not whole numbers

When the ratio is a fraction p / q in lowest terms, the modulator is at freq × p / q, and every partial freq ± k × freq × p / q = (freq / q) × (q ± k × p) is a whole multiple of freq / q. So every FM tone with such a ratio is harmonic, but of freq / q, not always of freq. Ratios 1 and 2 give harmonics of freq itself. Ratio 1.5 = 3/2 gives harmonics of freq / 2, an octave below the carrier. Ratio 0.15 = 3/20, in the sideband table above, gives harmonics of 1 000 / 20 = 50 Hz. A ratio such as 1.4142 (√2, to four places) is not a simple fraction, and its partials never share a fundamental the ear could find.

How many of those harmonics are present decides what the ear hears. With freq 200 Hz and ratio 1.4 = 7/5, the modulator is at 280 Hz and the sidebands sit at 200 ± 280 k: 480, 760, 1 040 … and, mirrored, 80, 360, 640 … Hz. They are all multiples of 200 / 5 = 40 Hz, but only a few of them: the 2nd, 5th, 9th, 12th, 16th, 19th … harmonics of 40 Hz, with most of the series missing. Chapter 5's bass had no first harmonic either, and the ear still heard 55 Hz, because harmonics 2, 3, 4 and up to 18 were all there in a dense, unbroken run. Here the run is broken more often than not, so the ear does not fuse the partials into one tone at 40 Hz and hears several pitches at once, as with chapter 3's metal bar. The larger q is, the sparser the run and the less the partials fuse.

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

Several notes sounding together are a *chord*. These three are A3, C♯4 and E4: C♯4 is 4 equal steps (chapter 2) above A3 and E4 is 7 steps above it, and a chord built of a note with the notes 4 and 7 steps above it is called a *major* chord, here A major. Each `epiano` builds its own envelopes, because a unit can appear only once in a graph (chapter 4).

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

Two other noises are named after colours of light. The level per Hz of `PinkNoise(seed)` falls 3 dB per octave, which exactly cancels the doubling width: every octave holds the same energy. `BrownNoise(seed)` falls 6 dB per octave. It is not named after the colour but after Robert Brown, who described the random motion of pollen grains in water: each sample is the last one plus a small random step, the way a grain wanders. The block measures each noise's level per Hz in six bands, each 10 % wide, starting at frequencies an octave apart. `power` is the squared size of each frequency component of 10 s of noise, and `freqs` the frequency of each, in Hz. `band_db` averages the power over one band and turns it into dB with 10 × log₁₀, not chapter 2's 20 × log₁₀, because power is already amplitude squared:

```python {run output=code}
import numpy as np

from euterpe.sound import BrownNoise, PinkNoise, WhiteNoise, render

def band_db(power, freqs, lo):
    band = (freqs >= lo) & (freqs < 1.1 * lo)
    return 10 * np.log10(power[band].mean())

for noise in (WhiteNoise(seed=1), PinkNoise(seed=1), BrownNoise(seed=1)):
    x = render(noise, 10.0)
    power = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / 48_000)
    levels = [band_db(power, freqs, lo) for lo in (250, 500, 1000, 2000, 4000, 8000)]
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

White noise hisses like a detuned radio. Pink sounds even from bottom to top, like steady rain; it is the noise engineers play through speakers to check them, because a meter that reads in octaves shows it flat. Brown is a deep roar, like surf heard from a distance. Brown noise has so much of its energy at the lowest frequencies that two seconds of it do not average 0, so a `OnePole` high-pass at 20 Hz (chapter 5) takes away what lies below hearing. White noise drawn evenly between −1 and 1 has an RMS level of 1 / √3 = 0.58. `PinkNoise` and `BrownNoise` are scaled to an RMS of 0.18, a level chosen so that their peaks stay below 1, which is why they need a gain of 1.0 where white noise needs 0.25.

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
short = OnePole(LFSRNoise(rate=12_000.0, short=True), 20.0, kind="highpass")
listen(short * ADSR(gate=0.8, release=0.2) * 0.12, 1.2, "Short LFSR noise at 12000 Hz: a 127-step loop")
```

One second of noise stepped 2 000 times a second is only 2 000 values of +1 or −1, and like any short stretch of random values they do not average exactly 0. That small offset is a DC component, so each example ends in a 20 Hz high-pass, as in chapter 5.

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

## Wavetables

A *wavetable* is one cycle of a wave stored as a list of numbers and read out over and over. `Wavetable(table, freq)` plays any list as one cycle, `freq` times a second, holding each value as a step. The list can hold any shape: a cycle drawn by hand, computed from a formula, or cut from a recording of an instrument. Reading a stored cycle costs almost nothing, so wavetables are how many synthesizers make tones whose shape is not a sine, saw or square; some store many tables and move from one to the next as a note plays, so the timbre changes over time.

The early sound chips that made LFSR noise stored very short tables: 32 values of 4 bits each, so 16 possible levels. The block below makes one from a sine. `np.sin(...) + 1` runs from 0 to 2; times 7.5 it runs from 0 to 15; `np.round` makes each value one of the 16 whole numbers 0 to 15; dividing by 7.5 and subtracting 1 brings it back to between −1 and 1. Rounding moves some steps up more than others, so the table's average is not quite 0, and subtracting its mean centres it, so it has no DC offset (chapter 4).

```python {run}
import numpy as np

from euterpe.book import listen
from euterpe.sound import ADSR, Sine, Wavetable

table = np.round((np.sin(2 * np.pi * np.arange(32) / 32) + 1) * 7.5) / 7.5 - 1
table = table - table.mean()
listen(Sine(220.0) * ADSR(gate=1.0, release=0.2) * 0.4, 1.3, "A sine at 220 Hz")
listen(Wavetable(table, 220.0) * ADSR(gate=1.0, release=0.2) * 0.4, 1.3, "A 32-step, 16-level sine at 220 Hz")
```

The stepped sine has the same pitch and a thin buzz on top. The block lists its six loudest partials:

```python {run continue output=code}
from euterpe.sound import render

y = render(Wavetable(table, 220.0), 1.0)
amp = np.abs(np.fft.rfft(y)) * 2 / len(y)   # one bin per Hz
for f in np.argsort(amp)[::-1][:6]:
    print(f, "Hz:", round(float(20 * np.log10(amp[f])), 1), "dB")
```

Two kinds of partial make the buzz. The loudest, at 6 820 and 7 260 Hz, are 220 Hz either side of 32 × 220 = 7 040 Hz, not at it. The 32 steps are 32 samples of a sine, taken 7 040 times a second, and chapter 1 showed that a sine at f shares its samples with partners at the sample rate ± f. A converter playing 7 040 samples a second would remove those partners with its filter; holding each value as a flat step for 1/7 040 s does not, so they stay, about 30 dB down. The weaker ones, at 1 540 and 3 300 Hz (the 7th and 15th harmonics), are the rounding to 16 levels: chapter 1's quantisation error, which here repeats every cycle, so it lands on harmonics of 220 Hz. That buzz is what game music of the 1980s sounds like.

## A string you can pluck

A guitar string, plucked, starts with the shape the finger gave it. That shape runs along the string in both directions, reflects at both ends, and comes back. A wave that goes round a loop and comes back again and again is exactly the comb filter of chapter 5. In 1983 Kevin Karplus and Alex Strong found that a comb with a small filter inside its loop makes a convincing string. Their method, *Karplus–Strong synthesis*, is built here in three steps.

### Step 1: noise in a delay line

The pluck is a short burst of noise, one period long: at 220 Hz, 1/220 s, 4.5 ms. It goes into a comb whose delay is the same period and whose feedback is 0.996, so it circulates and comes back 220 times a second, losing 0.4 % at each trip. `Segments` holds the noise at 1 for samples 0 to 218, the first 1/220 s, then at 0. A `OnePole` high-pass at 20 Hz removes the small offset of those 219 random samples, which the comb would otherwise build up. The `ADSR`, with no attack and full sustain, only fades the note out from 2.4 s, as a hand laid on the string would.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Comb, OnePole, Segments, WhiteNoise

burst = WhiteNoise(seed=1) * Segments([(0.0, 1.0), (1 / 220, 1.0), (1 / 220, 0.0)])
string = OnePole(Comb(burst, delay=1 / 220, feedback=0.996), 20.0, kind="highpass")
listen(string * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 0.25, 3.0, "A burst of noise circulating in a comb at 220 Hz")
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
from euterpe.book import listen
from euterpe.sound import ADSR, Pluck

note = Pluck(220.0, damping=0.996, seed=1)
listen(note * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 0.6, 3.0, "A plucked A3", id="pluck-a3")
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

`Pluck`'s burst is not raw noise. One period of raw noise gives each harmonic a random level, so with some seeds the octave above the note is louder than the note itself, and the same note played with two seeds differs in loudness and tone. `Pluck` sets the level of each harmonic and draws only their phases from the seed. The k-th harmonic starts at 1 / (1 + (k × freq / cutoff)²), with cutoff = freq × 2^(8 × brightness): This curve is the gain of two of chapter 5's one-pole low-passes in a row, each with gain 1 / √(1 + (f / cutoff)²). `brightness=0` puts the cutoff at the note itself, so the harmonics start at about 1/k². That is the spectrum of a string a finger has pulled aside at one point, so that it starts in the shape of a triangle; the triangle is the string's shape, not chapter 3's triangle wave, which falls as 1/k² too. `brightness=1` puts the cutoff at the 256th harmonic, as bright as raw noise.

`damping` is the gain of one trip round the loop, between 0.9 and 0.9999. Above 1, each trip would make the sound louder and it would grow without end, so `Pluck` refuses it. The three plucks below differ only in damping:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Pluck

for damping in (0.99, 0.996, 0.999):
    listen(Pluck(220.0, damping=damping, seed=1) * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 0.6, 3.0, f"A plucked A3, damping {damping}")
```

At 0.99 the note is short and muffled, like a string damped by the palm of the hand. At 0.999 it rings like a harp. `brightness` is the softness of what plucks it, from a fingertip (dark) to a hard plectrum (bright). `Pluck` gives every burst the same energy (unless that would put its peak above 0.9), but a bright burst holds much of it in high harmonics, and step 2 showed that those are gone within a fraction of a second. So over the whole note a bright pluck is quieter. The gains 0.49, 0.58 and 1.15 compensate, so the three differ in tone and not in loudness, and match the plucked A3 above; the second block measures them:

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

`position` is where the string is plucked, as a fraction of its length from one end, from 0 to 0.5. The k-th harmonic of a string vibrates in k segments, with still points between them, at 1/k, 2/k … of its length. A pluck at a point where a harmonic stands still cannot set that harmonic moving, so plucking at 1/n of the length removes every harmonic that has a still point there: the n-th, the 2n-th, the 3n-th and so on. `position=0.5` removes every even harmonic, and the tone turns hollow, as the square of chapter 3 does; `position=0.25` removes the 4th, 8th, 12th …; `position=0.1` the 10th, 20th …; and `position=0`, the default, removes nothing. Guitarists play near the bridge, at about 0.1, for a thin, bright tone, and over the sound hole, nearer 0.25, for a round one. The three plucks below use `brightness=0.8`, so the harmonics a position removes are loud enough to be missed, and `damping=0.998`, so they ring long enough to compare; the gain of 1.05 brings them to the level of the others:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Pluck

for position in (0.1, 0.25, 0.5):
    listen(Pluck(220.0, damping=0.998, brightness=0.8, position=position, seed=1) * ADSR(attack=0.0, sustain=1.0, gate=2.4, release=0.4) * 1.05, 3.0, f"A plucked A3, position {position}")
```

## Modes: bars and bells

A struck object does not vibrate at one frequency or at harmonics, but in *modes*: patterns of motion, each with its own frequency and its own decay time. Chapter 3 played the four lowest modes of a free metal bar, at 1, 2.76, 5.40 and 8.93 times its lowest frequency, as steady sines. Struck, each mode starts at once and then rings down, the high ones faster, because a faster vibration loses more energy per second to the air and to friction inside the metal.

`Modal(freqs, decays, amps)` makes each mode with a *resonator*: a filter of order 2 (chapter 5: it feeds back its last two outputs), tuned so that when it is struck it rings as a sine at one frequency and dies away. Each mode has a frequency in Hz, an amplitude and a decay time: the seconds it takes to fall by 60 dB, a thousandth of its starting level. With no other argument, all of them are struck at once, by a single sample of 1 at the start.

```python {run}
from euterpe.book import listen
from euterpe.sound import Modal

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

The pitch and the decay are the same; the attack has lost its click, and the upper modes are quieter beside the lowest. The gain is 0.1 where the struck bar had 0.3, so the mallet must have made the bar ring louder, though at every instant it is far quieter than a sample of 1. A resonator rings for a long time, so it keeps adding up each part of its input that arrives in step with its ringing. A sample of 1 is one push. The mallet is 240 small pushes over 5 ms, and at the frequencies of the lower modes they add up to more than that one push. At the highest mode, 8.93 × 440 = 3 930 Hz, which the low-pass at 1 500 Hz weakens, they add up to less.

### A bell

A church bell is shaped so that its lowest modes fall close to the equal steps of chapter 2. Take the mode at the note the ear hears as 1. Below it is a mode an octave lower, at 0.5. Above it are a mode 3 steps up, at 2^(3/12) = 1.19 times (musicians call that distance a *minor third*), one 7 steps up, at 2^(7/12) = 1.50 times (a *fifth*), one an octave up, at 2, and higher modes above those. The ratios below are close to those of a tuned bell, and the low modes ring for many seconds:

```python {run}
from euterpe.book import listen
from euterpe.sound import Modal

ratios = [0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.2]
decays = [6.0, 4.0, 3.5, 3.0, 2.5, 1.5, 1.0, 0.6]
amps = [0.6, 1.0, 0.7, 0.5, 0.8, 0.4, 0.3, 0.2]
listen(Modal([220 * r for r in ratios], decays, amps) * 0.18, 5.0, "A bell with its prime at 220 Hz: eight modes")
```

The mode a minor third up gives a tuned bell its particular colour. Compare it with the FM bell earlier in the chapter: FM made inharmonic partials from two sines and one ratio, and put every one of them where the ratio placed it; the modal bell takes each frequency, level and decay from a list, so it can copy a real object that has been measured. FM is cheap and has few knobs. A modal model costs one filter per mode and can be as exact as the measurements behind it.

## Summary

- `FM(freq, ratio, index, feedback)` is a sine at `freq` whose phase is moved by a second sine at `ratio × freq`, by up to `index` radians, which swings its frequency by up to index × ratio × freq Hz. Its spectrum is the carrier and sidebands at freq ± k × ratio × freq, at the levels of the Bessel functions J_k(index); about index + 1 pairs are loud.
- A ratio p / q in lowest terms puts every partial on a harmonic of freq / q: ratios 1 and 2 give harmonics of freq, 1.5 of freq / 2. The larger q, the sparser that series and the less the ear fuses it into one pitch; a ratio that is no simple fraction, such as √2, has no common fundamental at all. A mirrored sideband that lands on another partial adds to it with its sign. An envelope on the index makes the brightness move: bells, electric pianos. `feedback` turns the modulator into a near-saw and adds roughness.
- White noise is flat per Hz, so each octave holds 3 dB more than the one below. `PinkNoise` holds the same energy in every octave; `BrownNoise` falls 6 dB per octave.
- `LFSRNoise(rate, short, seed)` is the noise of early sound chips, a shift register stepped `rate` times a second; `short=True` repeats every 127 steps and buzzes. `Wavetable(table, freq)` plays a list of numbers as one cycle of a wave, in steps; the steps add partials either side of the table length times freq.
- Drums are mostly filtered noise under short envelopes: a hi-hat is noise above 7 000 Hz; a snare is noise plus a short falling tone.
- `Pluck(freq, damping, brightness, position, seed)` is Karplus–Strong: a burst one period long in a delay line, an averaging filter that removes the high harmonics sooner, and an allpass for the exact pitch. `damping` sets how long it rings, `brightness` how bright it starts, `position` which harmonics the pluck point removes.
- `Modal(freqs, decays, amps, excite)` is a bank of resonators, one per mode, each a decaying sine that falls 60 dB in its decay time. Bars and bells are lists of modes; `excite` is what strikes them.

## Exercises

1. In the FM bell, change `ratio=1.4` to `ratio=2.0`. Is it still a bell? Which harmonics of 200 Hz does it have?
2. In the plucked A3, change `damping=0.996` to `damping=0.98`. Use the averaging-filter block to work out how many dB the first harmonic now loses in one second.
3. In the hi-hat, change `cutoff=7000.0` to `cutoff=1500.0`. What does the closed hat sound like now?
4. In the plucked A3, add `position=0.2` to the `Pluck`. Which harmonics disappear, and at what frequencies are the first two of them?
5. In the wavetable block, change both `7.5` to `1.5`. How many levels does the table have now, and what happens to the buzz?

### Answers

1. It is no longer a bell. The sidebands are at 200 ± 400 k Hz: 600, 1 000, 1 400 Hz above and, mirrored, 200, 600, 1 000 Hz from below, all odd multiples of 200 Hz. Only odd harmonics, as in the square of chapter 3, so the tone is hollow, close to a clarinet, and it has a clear pitch at 200 Hz.
2. Each trip now keeps 0.98 × cos(π × 220 / 48 000) of the first harmonic, and 220 trips a second give 20 × log₁₀ of that to the 220th power: about −38.8 dB in one second, about five times as much as at 0.996. By the 60 dB rule the note lasts 60 / 38.8 = 1.5 s instead of 7.6 s, and it sounds muted, like a pizzicato on a violin.
3. It sounds less like metal and more like a shaker, or brushes on a snare. The level hardly changes: white noise has the same energy in every Hz, so keeping 24 000 − 1 500 = 22 500 Hz of it instead of 24 000 − 7 000 = 17 000 Hz is 22 500 / 17 000 = 1.32 times the power, 1.2 dB. What changes is the timbre: the hat now also holds the band from 1 500 to 7 000 Hz, so it sounds fuller and less like a cymbal.
4. Plucking at 0.2 = 1/5 of the length removes every harmonic with a still point there: the 5th, 10th, 15th and so on. The first two are at 5 × 220 = 1 100 Hz and 10 × 220 = 2 200 Hz.
5. (sin + 1) × 1.5 runs from 0 to 3, so rounding leaves the 4 whole numbers 0 to 3: 4 levels, 2 bits. The pitch stays at 220 Hz, but the rounding error is much larger, so the harmonics it adds (chapter 1's quantisation error, repeating every cycle) are much louder and the buzz is far stronger. Run the block that lists the loudest partials again to see them.

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
