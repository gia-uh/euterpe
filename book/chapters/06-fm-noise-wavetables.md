# FM, noise and wavetables

Chapter 3 built tones by adding sines, one per partial. Chapter 5 started from a source with many harmonics and filtered some away. This chapter adds three more ways to make a sound. *Frequency modulation* (FM) gets many partials out of two sines. *Noise* is sound with no pitch, and drums are mostly noise. A *wavetable* stores one cycle of any shape and plays it over and over. Chapter 7 adds a fourth way, physical models, which compute what a vibrating object does.

## Frequency modulation

Chapter 4 moved the frequency of a sine with an envelope, to make a bass drum. A slow sine can move it too. Here a sine at 440 Hz has its frequency pushed 10 Hz up and down, 5 times a second:

```python {run}
from euterpe.sound import ADSR, Sine

vibrato = Sine(Sine(5.0) * 10 + 440)
display((vibrato * ADSR(gate=1.7, release=0.3) * 0.4).take(2.2, "A sine at 440 Hz with 5 Hz vibrato"))
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
from euterpe.sound import FM
from euterpe.view import spectrum

indexes = (0.0, 1.0, 3.0, 8.0)
spectrum(
    *[FM(220.0, ratio=1.0, index=i).take(1.0) for i in indexes],
    f0=220.0, harmonics=20, upto=4400, labels=[f"index {i:g}" for i in indexes],
    caption="The spectrum of FM at 220 Hz, ratio 1, at index 0, 1, 3 and 8",
)
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
from euterpe.sound import ADSR, FM
from euterpe.view import listen

for index in (0.0, 1.0, 3.0, 8.0):
    display(listen(FM(220.0, ratio=1.0, index=index) * ADSR(gate=1.0, release=0.2) * 0.4, 1.3, f"FM at 220 Hz, ratio 1, index {index:g}"))
```

The pitch stays at 220 Hz while the tone goes from a flute-like sine to a buzz like a saw's. Two sines and one number did what chapter 3 needed dozens of partials for, which is why FM was cheap enough for the digital synthesizers of the 1980s.

### Ratios that are not whole numbers

When the ratio is a fraction p / q in lowest terms, the modulator is at freq × p / q, and every partial freq ± k × freq × p / q = (freq / q) × (q ± k × p) is a whole multiple of freq / q. So every FM tone with such a ratio is harmonic, but of freq / q, not always of freq. Ratios 1 and 2 give harmonics of freq itself. Ratio 1.5 = 3/2 gives harmonics of freq / 2, an octave below the carrier. Ratio 0.15 = 3/20, in the sideband table above, gives harmonics of 1 000 / 20 = 50 Hz. A ratio such as 1.4142 (√2, to four places) is not a simple fraction, and its partials never share a fundamental the ear could find.

How many of those harmonics are present decides what the ear hears. With freq 200 Hz and ratio 1.4 = 7/5, the modulator is at 280 Hz and the sidebands sit at 200 ± 280 k: 480, 760, 1 040 … and, mirrored, 80, 360, 640 … Hz. They are all multiples of 200 / 5 = 40 Hz, but only a few of them: the 2nd, 5th, 9th, 12th, 16th, 19th … harmonics of 40 Hz, with most of the series missing. Chapter 5's bass had no first harmonic either, and the ear still heard 55 Hz, because harmonics 2, 3, 4 and up to 18 were all there in a dense, unbroken run. Here the run is broken more often than not, so the ear does not fuse the partials into one tone at 40 Hz and hears several pitches at once, as with chapter 3's metal bar. The larger q is, the sparser the run and the less the partials fuse.

### An index that moves

A struck bell is bright at first and mellows as it rings, because its high partials die sooner. In FM the index sets the brightness, so an envelope on the index gives the same effect. John Chowning, who discovered FM synthesis at Stanford in the late 1960s, made bells this way: a ratio of 1.4 and an index that falls from 10 to 0 together with the level.

```python {run}
from euterpe.sound import ADSR, FM

def fading(seconds):
    return ADSR(attack=0.001, decay=seconds, sustain=0.0, gate=seconds, curve=0.8)

bell = FM(200.0, ratio=1.4, index=fading(4.0) * 10) * fading(4.0) * 0.35
display(bell.take(4.0, "An FM bell: ratio 1.4, the index falling from 10 to 0"))
```

The same idea with ratio 1 and a quick fall of the index gives the electric-piano sound of many 1980s ballads. The index starts at 2.8, falls to 0.3 within half a second and stays there, so each note starts with a bright bark and settles into a nearly pure tone:

```python {run}
from euterpe.sound import ADSR, FM

def epiano(freq):
    index = ADSR(attack=0.0, decay=0.4, sustain=0.0, gate=2.0, curve=0.7) * 2.5 + 0.3
    level = ADSR(attack=0.002, decay=1.6, sustain=0.0, gate=2.0, curve=0.7)
    return FM(freq, ratio=1.0, index=index) * level

display(((epiano(220.0) + epiano(277.18) + epiano(329.63)) * 0.25).take(2.0, "An FM electric piano: an A major chord"))
```

Several notes sounding together are a *chord*. These three are A3, C♯4 and E4: C♯4 is 4 equal steps (chapter 2) above A3 and E4 is 7 steps above it, and a chord built of a note with the notes 4 and 7 steps above it is called a *major* chord, here A major. Each `epiano` builds its own envelopes, because a unit can appear only once in a graph (chapter 4).

### Feedback

`FM` has a fourth parameter, `feedback`, in radians from 0 to 1.5. It feeds the modulator's own last output back into its phase. A sine that pushes its own phase spends longer on one side of its cycle than the other, and as feedback rises it turns into something close to a saw, with harmonics of its own. Those harmonics then modulate the carrier, so feedback makes the tone brighter and rougher than the index alone can:

```python {run}
from euterpe.sound import ADSR, FM, OnePoleHighPass

for feedback in (0.0, 1.5):
    tone = OnePoleHighPass(FM(110.0, ratio=1.0, index=1.5, feedback=feedback), 20.0)
    display((tone * ADSR(gate=1.0, release=0.2) * 0.4).take(1.3, f"FM at 110 Hz, index 1.5, feedback {feedback:g}"))
```

A modulator that leans to one side also pushes the carrier off-centre, so feedback adds a DC offset (chapter 4). The `OnePoleHighPass` at 20 Hz removes it, as chapter 5 showed.

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
from euterpe.sound import ADSR, BrownNoise, OnePoleHighPass, PinkNoise, WhiteNoise

display((WhiteNoise(seed=1) * ADSR(gate=1.7, release=0.3) * 0.25).take(2.2, "White noise"))
display((PinkNoise(seed=1) * ADSR(gate=1.7, release=0.3) * 1.0).take(2.2, "Pink noise"))
brown = OnePoleHighPass(BrownNoise(seed=1), 20.0)
display((brown * ADSR(gate=1.7, release=0.3) * 1.0).take(2.2, "Brown noise"))
```

White noise hisses like a detuned radio. Pink sounds even from bottom to top, like steady rain; it is the noise engineers play through speakers to check them, because a meter that reads in octaves shows it flat. Brown is a deep roar, like surf heard from a distance. Brown noise has so much of its energy at the lowest frequencies that two seconds of it do not average 0, so a `OnePoleHighPass` at 20 Hz (chapter 5) takes away what lies below hearing. White noise drawn evenly between −1 and 1 has an RMS level of 1 / √3 = 0.58. `PinkNoise` and `BrownNoise` are scaled to an RMS of 0.18, a level chosen so that their peaks stay below 1, which is why they need a gain of 1.0 where white noise needs 0.25.

```python {run echo=false}
from euterpe.sound import BrownNoise, PinkNoise, WhiteNoise
from euterpe.view import spectrum

noises = (WhiteNoise(seed=1), PinkNoise(seed=1), BrownNoise(seed=1))
spectrum(
    *[n.take(4.0) for n in noises], upto=20_000, labels=[type(n).__name__ for n in noises],
    caption="The spectra of white, pink and brown noise: flat, 3 dB and 6 dB per octave down",
)
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
from euterpe.sound import ADSR, LFSRNoise, OnePoleHighPass

for rate in (2_000.0, 12_000.0):
    noise = OnePoleHighPass(LFSRNoise(rate=rate), 20.0)
    display((noise * ADSR(gate=0.8, release=0.2) * 0.12).take(1.2, f"LFSR noise stepped at {rate:.0f} Hz"))
short = OnePoleHighPass(LFSRNoise(rate=12_000.0, short=True), 20.0)
display((short * ADSR(gate=0.8, release=0.2) * 0.12).take(1.2, "Short LFSR noise at 12000 Hz: a 127-step loop"))
```

One second of noise stepped 2 000 times a second is only 2 000 values of +1 or −1, and like any short stretch of random values they do not average exactly 0. That small offset is a DC component, so each example ends in a 20 Hz high-pass, as in chapter 5.

## Noise as drums

Most of a drum's sound has no pitch. A cymbal is a thin plate that vibrates at thousands of unrelated frequencies at once, which the ear hears as noise; a snare drum has a set of wires stretched under its lower skin that rattle against it. So drums are built from noise, filtered to the band where the real drum has its energy and shaped by a short envelope.

A hi-hat, the pair of small cymbals a drummer plays on most beats, has its energy above about 7 000 Hz. A high-pass at 7 000 Hz keeps that band. A closed hi-hat lasts about 50 ms, an open one about 0.4 s:

```python {run}
from euterpe.sound import ADSR, HighPass, WhiteNoise

def hat(decay):
    env = ADSR(attack=0.001, decay=decay, sustain=0.0, release=0.0, gate=1.0, curve=0.8)
    return HighPass(WhiteNoise(seed=1), cutoff=7000.0) * env * 0.6

display(hat(0.05).take(0.5, "A closed hi-hat: high-passed noise, 50 ms"))
display(hat(0.4).take(1.0, "An open hi-hat: the same noise, 0.4 s"))
```

A snare drum has two parts: the skin, struck, gives a short tone near 180 Hz whose pitch drops a little, as the bass drum of chapter 4 did; the wires give a burst of noise above 1 000 Hz that lasts longer than the tone. The snare is the sum of the two:

```python {run}
from euterpe.sound import ADSR, HighPass, Sine, WhiteNoise

def snare():
    pitch = ADSR(attack=0.0, decay=0.04, sustain=0.0, gate=1.0) * 60 + 180
    skin = Sine(pitch) * ADSR(attack=0.001, decay=0.12, sustain=0.0, release=0.0, gate=1.0, curve=0.7)
    wires = HighPass(WhiteNoise(seed=2), cutoff=1000.0) * ADSR(attack=0.001, decay=0.22, sustain=0.0, release=0.0, gate=1.0, curve=0.8)
    return skin * 0.35 + wires * 0.3

display(snare().take(0.6, "A snare: a falling tone at 240 to 180 Hz and high-passed noise"))
```

Remove `skin` and the snare loses its body: it becomes a hiss with no weight. Remove `wires` and it is a dull knock on a box.

## Wavetables

A *wavetable* is one cycle of a wave stored as a list of numbers and read out over and over. `Wavetable(table, freq)` plays any list as one cycle, `freq` times a second, holding each value as a step. The list can hold any shape: a cycle drawn by hand, computed from a formula, or cut from a recording of an instrument. Reading a stored cycle costs almost nothing, so wavetables are how many synthesizers make tones whose shape is not a sine, saw or square; some store many tables and move from one to the next as a note plays, so the timbre changes over time.

The early sound chips that made LFSR noise stored very short tables: 32 values of 4 bits each, so 16 possible levels. The block below makes one from a sine. `np.sin(...) + 1` runs from 0 to 2; times 7.5 it runs from 0 to 15; `np.round` makes each value one of the 16 whole numbers 0 to 15; dividing by 7.5 and subtracting 1 brings it back to between −1 and 1. Rounding moves some steps up more than others, so the table's average is not quite 0, and subtracting its mean centres it, so it has no DC offset (chapter 4).

```python {run}
import numpy as np

from euterpe.sound import ADSR, Sine, Wavetable

table = np.round((np.sin(2 * np.pi * np.arange(32) / 32) + 1) * 7.5) / 7.5 - 1
table = table - table.mean()
display((Sine(220.0) * ADSR(gate=1.0, release=0.2) * 0.4).take(1.3, "A sine at 220 Hz"))
display((Wavetable(table, 220.0) * ADSR(gate=1.0, release=0.2) * 0.4).take(1.3, "A 32-step, 16-level sine at 220 Hz"))
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

## Summary

- `FM(freq, ratio, index, feedback)` is a sine at `freq` whose phase is moved by a second sine at `ratio × freq`, by up to `index` radians, which swings its frequency by up to index × ratio × freq Hz. Its spectrum is the carrier and sidebands at freq ± k × ratio × freq, at the levels of the Bessel functions J_k(index); about index + 1 pairs are loud.
- A ratio p / q in lowest terms puts every partial on a harmonic of freq / q: ratios 1 and 2 give harmonics of freq, 1.5 of freq / 2. The larger q, the sparser that series and the less the ear fuses it into one pitch; a ratio that is no simple fraction, such as √2, has no common fundamental at all. A mirrored sideband that lands on another partial adds to it with its sign. An envelope on the index makes the brightness move: bells, electric pianos. `feedback` turns the modulator into a near-saw and adds roughness.
- White noise is flat per Hz, so each octave holds 3 dB more than the one below. `PinkNoise` holds the same energy in every octave; `BrownNoise` falls 6 dB per octave.
- `LFSRNoise(rate, short, seed)` is the noise of early sound chips, a shift register stepped `rate` times a second; `short=True` repeats every 127 steps and buzzes. `Wavetable(table, freq)` plays a list of numbers as one cycle of a wave, in steps; the steps add partials either side of the table length times freq.
- Drums are mostly filtered noise under short envelopes: a hi-hat is noise above 7 000 Hz; a snare is noise plus a short falling tone.

## Exercises

1. In the FM bell, change `ratio=1.4` to `ratio=2.0`. Is it still a bell? Which harmonics of 200 Hz does it have?
2. In the hi-hat, change `cutoff=7000.0` to `cutoff=1500.0`. What does the closed hat sound like now?
3. In the wavetable block, change both `7.5` to `1.5`. How many levels does the table have now, and what happens to the buzz?

### Answers

1. It is no longer a bell. The sidebands are at 200 ± 400 k Hz: 600, 1 000, 1 400 Hz above and, mirrored, 200, 600, 1 000 Hz from below, all odd multiples of 200 Hz. Only odd harmonics, as in the square of chapter 3, so the tone is hollow, close to a clarinet, and it has a clear pitch at 200 Hz.
2. It sounds less like metal and more like a shaker, or brushes on a snare. The level hardly changes: white noise has the same energy in every Hz, so keeping 24 000 − 1 500 = 22 500 Hz of it instead of 24 000 − 7 000 = 17 000 Hz is 22 500 / 17 000 = 1.32 times the power, 1.2 dB. What changes is the timbre: the hat now also holds the band from 1 500 to 7 000 Hz, so it sounds fuller and less like a cymbal.
3. (sin + 1) × 1.5 runs from 0 to 3, so rounding leaves the 4 whole numbers 0 to 3: 4 levels, 2 bits. The pitch stays at 220 Hz, but the rounding error is much larger, so the harmonics it adds (chapter 1's quantisation error, repeating every cycle) are much louder and the buzz is far stronger. Run the block that lists the loudest partials again to see them.

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
