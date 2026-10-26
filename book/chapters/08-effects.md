# Effects

The chapters so far made sounds: oscillators, envelopes, filters, FM, noise, wavetables and physical models. An *effect* takes a sound that already exists and changes it. A guitar amplifier, an echo pedal, the reverb of a concert hall and the compressor on a radio station's output are all effects. Each one is a unit that takes another unit as its source, as a filter does, so they chain: a source, then a distortion, then a delay, then a reverb.

This chapter covers five families. Delays add copies of the sound later in time. Moving delays (chorus, flanger) and the phaser make the copy's timing change as the sound plays. Distortion bends the wave and adds harmonics. Dynamics (compressor, limiter, gate) turn the volume up and down by themselves, following the level of the sound. Reverb adds the thousands of echoes a room makes. The chapter ends with stereo: placing a sound between two speakers.

## Delay and echo

`Delay(src, time, feedback, mix)` keeps the last few seconds of its source and plays them back `time` seconds later. Inside it is a *delay line*, a buffer that holds time × 48 000 samples: at 0.3 s, 14 400 of them. `mix` sets how much of the delayed copy is heard: the output is (1 − mix) × source + mix × delayed. `feedback` sends the delayed copy back into the line, so it comes out again, `time` seconds later, multiplied by `feedback` once more.

Here a plucked string at 330 Hz goes through a delay of 0.3 s with feedback 0.45:

```python {run}
from euterpe.view import listen
from euterpe.sound import Delay, Pluck

note = Pluck(330.0, damping=0.99)
listen(Delay(note, time=0.3, feedback=0.45, mix=0.5) * 0.7, 3.0, "A pluck with echoes every 0.3 s, feedback 0.45")
```

You hear the note, then the same note again every 0.3 s, quieter each time. Each echo is 0.45 times the one before, 20 × log₁₀ 0.45 = −6.9 dB. Counting the first echo as echo 1, echo k is k − 1 steps after it, so it is (k − 1) × 6.9 dB below the first: echo 5 is 4 × 6.9 = 28 dB below it. With feedback 1 the echoes would never die away; the unit allows at most 0.99.

The plot shows the same delay fed a single sample of 1, a click. The click itself comes out at 1 − mix = 0.5. Echo 1 also comes out at 0.5, since it is the copy at mix = 0.5, and echo k at 0.5 × 0.45ᵏ⁻¹:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import Const, Delay, Segments, render

click = Segments([(0.0, 1.0), (1 / 48000, 0.0)])
x = render(Delay(click, time=0.3, feedback=0.45, mix=0.5), 1.6)
t = np.arange(len(x)) / 48000
fig, ax = plt.subplots(figsize=(7, 2.4))
ax.vlines(t[x > 1e-4], 0, x[x > 1e-4], linewidth=2)
ax.set_xlabel("time (s)")
ax.set_ylabel("level")
ax.set_ylim(0, 0.6)
fig.tight_layout()
show(fig, "A click through Delay(time=0.3, feedback=0.45, mix=0.5): the click, then echoes every 0.3 s")
```

### Short delays colour the sound

A delay is only heard as an echo when the copy arrives late enough. Below about 30 to 50 ms the ear fuses the two into one sound with a new tone. Chapter 5 explained why: adding a copy delayed by T seconds is a comb filter. A sine whose period fits a whole number of times into T comes back in step and doubles; one with half a period left over comes back opposite and cancels. So the spectrum gets peaks at every multiple of 1 / T Hz and dips halfway between them.

The same noise burst, with a copy at 1 ms, 10 ms, 40 ms and 150 ms, one after the other:

```python {run}
from euterpe.view import listen
from euterpe.sound import ADSR, Delay, WhiteNoise

for ms in (1, 10, 40, 150):
    burst = WhiteNoise(seed=7) * ADSR(attack=0.001, decay=0.08, sustain=0.0, gate=0.1) * 0.5
    display(listen(Delay(burst, time=ms / 1000, feedback=0.0, mix=0.5), 0.6, f"A noise burst plus a copy {ms} ms later"))
```

At 1 ms the burst sounds like a hollow tube: peaks every 1 000 Hz. At 10 ms the peaks are 100 Hz apart and the burst has a faint pitch, 100 Hz. At 40 ms the copy is just far enough apart to hear as two hits, a rough double hit. At 150 ms it is a clear echo.

## Moving delays: chorus, flanger, phaser

A delay whose time changes while the sound plays does more than add a copy. When the time grows, each sample of the copy comes out a little later than the one before it: the copy is stretched, and stretched sound is lower in pitch. When the time shrinks, the copy is squeezed and higher. If the delay grows by r seconds every second, the copy plays at 1 − r times its speed: after 1 s the copy has fallen r s further behind, so in that second it played only 1 − r s of sound. Every frequency in it is multiplied by 1 − r.

### Chorus

`Chorus(src, rate, depth, mix)` mixes the source with a copy delayed by 20 ms plus or minus `depth` seconds, and swings the delay up and down `rate` times a second along a sine: at time t the delay is 0.020 + depth × sin(2π × rate × t) seconds. How fast does it change? Picture a point going round a circle of radius `depth`, `rate` times a second: it travels 2π × depth × rate per second, and the sine is its height, which moves fastest when the point crosses the middle, where it moves straight up or down. So the delay changes by at most 2π × depth × rate seconds per second. The block computes it both ways for the defaults, depth 3 ms and rate 0.8 Hz: by the formula, and from the delay curve itself, as the largest change between two samples times 48 000:

```python {run output=code}
import numpy as np

t = np.arange(48000) / 48000
delay = 0.020 + 0.003 * np.sin(2 * np.pi * 0.8 * t)
r = 2 * np.pi * 0.003 * 0.8
print(f"by the formula: {r:.4f} s per second; from the curve: {np.abs(np.diff(delay)).max() * 48000:.4f}")
print(f"the copy's pitch moves by up to {100 * r:.2f} %, {1200 * np.log2(1 + r):.0f} cents")
```

A *cent* is a hundredth of one of chapter 2's equal steps, so 26 cents is about a quarter of a step. Two singers on the same note are never exactly in tune: they drift apart by a few cents and back. The chorus copies that drift, which is where its name comes from. Here is a saw at 220 Hz, alone and then with a chorus:

```python {run}
from euterpe.view import listen
from euterpe.sound import ADSR, Biquad, Chorus, Saw

saw = lambda: Biquad(Saw(220.0), "lowpass", cutoff=2500.0) * ADSR(gate=2.6, release=0.3) * 0.5
display(listen(saw(), 3.0, "A filtered saw at 220 Hz, dry"))
listen(Chorus(saw(), rate=0.8, depth=0.003, mix=0.5), 3.0, "The same saw through a chorus")
```

`saw` is a function that builds a fresh saw each time it is called, because a unit keeps its own state and cannot be played in two places at once. The `ADSR` fades it out at the end. The chorused saw sounds thicker, as if two players were playing it, and it slowly shimmers. The shimmer is *beating*. Two tones close in frequency, added, drift in and out of step: when their peaks line up they add, and 1 / (2 × the difference) seconds later one is at its peak where the other is at its trough, and they cancel. So the sum gets louder and softer as many times a second as the difference of their frequencies. A copy 1.5 % higher than 220 Hz is at 223.3 Hz, and the pair beats 3.3 times a second:

```python {run}
from euterpe.view import listen
from euterpe.sound import ADSR, Sine

listen((Sine(220.0) + Sine(223.3)) * ADSR(gate=2.6, release=0.3) * 0.3, 3.0, "Sines at 220 and 223.3 Hz added: 3.3 beats a second")
```

In the chorus every harmonic of the saw beats with its moving copy, each at its own rate, since the k-th harmonic's copy is k times further off in Hz. The rates change as the delay swings, so no single beat stands out, and the result is a shimmer.

### Flanger

`Flanger(src, rate, depth, feedback, mix)` uses a much shorter delay: from 0.5 ms up to 0.5 ms + `depth`. At those lengths the copy is not heard as a copy at all, only as the comb filter of the previous section, with peaks at multiples of 1 / T. The example below uses depth 0.004, so T sweeps from 0.5 ms to 4.5 ms, and the first peak slides between 1 / 0.0005 = 2 000 Hz and 1 / 0.0045 = 222 Hz, every other peak sliding with it. `feedback`, from −0.95 to 0.95, sends the delayed copy back in, which makes the peaks taller and narrower, as feedback did for `Comb` in chapter 5. A negative feedback flips the copy each time it goes round, and the flanger then also mixes the copy in upside down: a frequency is reinforced where an odd number of half periods fits into T, so the peaks move to the odd multiples of 1 / (2T).

A comb is easiest to hear on a sound that has every frequency, so here is white noise through a flanger sweeping once every 4 seconds:

```python {run}
from euterpe.view import listen
from euterpe.sound import ADSR, Flanger, WhiteNoise

noise = WhiteNoise(seed=3) * ADSR(attack=0.5, gate=7.2, release=0.6) * 0.15
listen(Flanger(noise, rate=0.25, depth=0.004, feedback=0.7, mix=0.5), 8.0, "White noise through a flanger, rate 0.25 Hz, feedback 0.7")
```

The noise sounds like a jet passing overhead. The picture shows why: in this *spectrogram* time runs to the right, frequency goes up, and brighter means louder. The bright bands are the peaks of the comb, evenly spaced, rising and falling together.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import Flanger, WhiteNoise, render

x = render(Flanger(WhiteNoise(seed=3) * 0.15, rate=0.25, depth=0.004, feedback=0.7, mix=0.5), 8.0)
fig, ax = plt.subplots(figsize=(7, 3))
ax.specgram(x, NFFT=2048, Fs=48000, noverlap=1024, cmap="magma", vmin=-110)
ax.set_ylim(0, 8000)
ax.set_xlabel("time (s)")
ax.set_ylabel("frequency (Hz)")
fig.tight_layout()
show(fig, "Spectrogram of white noise through the flanger: the comb's peaks sweep together")
```

### Phaser

`Phaser(src, rate, stages, mix)` sounds close to a flanger but works differently. It passes the source through a chain of `stages` *allpass* filters, which chapter 5 met: an allpass keeps the level of every frequency and only delays it, by a different amount at each frequency. Each of the phaser's allpasses has a *turning frequency*, where it delays a sine by a quarter of its period, 90°. Below that frequency it delays less, above it more, up to half a period, 180°, at 24 000 Hz. All the stages share one turning frequency, which sweeps from 200 Hz to 2 000 Hz and back, `rate` times a second, so n stages delay n × 90° there.

Mixed with the source, the chained copy cancels wherever its total delay is an odd number of half periods: 180°, 540°, 900° and so on. Four stages delay 4 × 90° = 360° at the turning frequency, so they pass 180° at one frequency below it and 540° at one above it, two notches; they never reach 900°, since four stages give at most 720°. In general n stages reach at most n × 180°, so they have n / 2 notches, rounded down. A flanger's comb has peaks at 1, 2, 3, 4 ... times one frequency, evenly spaced all the way up. A phaser has only these few notches, and they are not at multiples of one frequency, so its sweep sounds softer:

```python {run}
from euterpe.view import listen
from euterpe.sound import ADSR, Biquad, Phaser, Saw

saw = Biquad(Saw(110.0), "lowpass", cutoff=4000.0) * ADSR(gate=5.4, release=0.5) * 0.5
listen(Phaser(saw, rate=0.3, stages=8, mix=0.5), 6.0, "A saw at 110 Hz through an 8-stage phaser, rate 0.3 Hz")
```

Eight stages give four notches that move together. Try `stages=2`: a single notch, and a much gentler sweep.

## Distortion

The effects so far add copies of the sound, and a delay that does not move adds no new frequencies: a sine in gives a sine out, at the same frequency. *Distortion* does add new ones. A *waveshaper* passes each sample through a fixed curve, and a curve that bends the wave adds new frequencies to it. Chapter 1's `BitCrush` was one: its curve was a staircase.

`Shaper(src, kind, drive)` has three curves. Each multiplies the sample by `drive` / 2 first and then bends it. The half is there so that drive 2 puts a full-scale input exactly at u = 1, where the soft and hard curves stop rising, and drive 1 bends only a little:

- `"tanh"`, the hyperbolic tangent: straight near 0 and bending smoothly towards ±1.
- `"soft"`, the cubic u − u³/3, which stops rising at u = 1 and stays flat beyond.
- `"hard"`, a clip: straight up to ±1, then flat. An amplifier pushed past its supply voltage does this.

The output is scaled so a full-scale input comes out at −1 dBFS, so turning up `drive` changes the shape and not the peak. The curves are drawn here at drive 4:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show

u = np.linspace(-1, 1, 400) * 2
curves = {
    "tanh": np.tanh(u) / np.tanh(2),
    "soft": (np.clip(u, -1, 1) - np.clip(u, -1, 1) ** 3 / 3) / (2 / 3),
    "hard": np.clip(u, -1, 1),
}
fig, ax = plt.subplots(figsize=(4.5, 3.2))
ax.plot(u / 2, u / 2, color="0.75", linestyle="--", label="no shaper")
for name, y in curves.items():
    ax.plot(u / 2, 0.891 * y, label=name)
ax.set_xlabel("input sample")
ax.set_ylabel("output sample")
ax.legend(fontsize=8)
fig.tight_layout()
show(fig, "The three curves of Shaper at drive 4: each input sample maps to one output sample")
```

A sine pushed through a curve stays periodic with the same period, so whatever the curve adds must be harmonics, multiples of the sine's frequency. The block measures the first seven harmonics of a sine at 220 Hz through each curve, in dB:

```python {run output=code}
import numpy as np

from euterpe.sound import Shaper, Sine, render

for kind in ("tanh", "soft", "hard"):
    x = render(Shaper(Sine(220.0), kind, drive=4.0), 1.0)
    amp = np.abs(np.fft.rfft(x)) * 2 / len(x)          # one bin per Hz, as in chapter 6
    levels = [20 * np.log10(amp[220 * k] + 1e-9) for k in range(1, 8)]
    print(f"{kind:>4}:", "  ".join(f"{v:6.1f}" for v in levels))
```

Two things show. First, the even harmonics (2nd, 4th, 6th) are at −150 dB or below: absent. All three curves are *odd*: the bottom half is the top half turned upside down, so the positive and negative halves of the sine are bent the same way, and a wave with that symmetry has only odd harmonics, as the square of chapter 3. The fundamental of all three is above 0 dB although the output peaks at −1 dBFS: a wave squashed towards a square has a fundamental larger than its peak, 1.273 times it for a full square, as chapter 3 measured. Second, the curves bend the wave by different amounts at the same drive. The 7th harmonic is −40.6 dB after `tanh`, −35.1 dB after `hard` and −30.0 dB after `soft`, whose curve rises most steeply in the plot above and then turns flat at the same point as `hard`, with a rounder corner.

More drive pushes more of the wave into the bend. Here is the same sine at drive 1, 4 and 16, through `tanh`:

```python {run}
from euterpe.view import listen
from euterpe.sound import ADSR, Shaper, Sine

for drive in (1.0, 4.0, 16.0):
    display(listen(Shaper(Sine(220.0), "tanh", drive=drive) * ADSR(gate=1.2, release=0.2) * 0.5, 1.5, f"A sine at 220 Hz through tanh at drive {drive:g}"))
```

At drive 1 you hear a sine with a slight buzz; at 16 the wave is nearly a square, and sounds like one.

### Saturation and even harmonics

`Saturator(src, drive, bias)` is a tanh with the wave shifted by `bias` before the curve: tanh(drive / 2 × (x + bias)), with `drive` halved as in `Shaper`, so the same drive means the same push into the curve in both. The shift makes the curve lopsided around the wave. The top half is bent more than the bottom half, the symmetry is gone, and the even harmonics appear. Tube amplifiers do the same, and the 2nd harmonic, an octave above the note, is why their distortion is called warm: it adds the note's own octave rather than a harsher odd harmonic. The shift also leaves an offset at 0 Hz, which the unit removes with a high-pass at 10 Hz.

```python {run output=code}
import numpy as np

from euterpe.sound import Saturator, Sine, render

x = render(Saturator(Sine(220.0), drive=4.0, bias=0.2), 1.0)
amp = np.abs(np.fft.rfft(x)) * 2 / len(x)
print("  ".join(f"{20 * np.log10(amp[220 * k] + 1e-12):6.1f}" for k in range(1, 8)))
```

The 2nd harmonic is now at −17.7 dB, as loud as the 3rd, and the 4th and 6th are there too. The plot puts the four spectra side by side, the first ten harmonics of 220 Hz marked, odd ones in blue and even ones in orange:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import Saturator, Shaper, Sine, render

units = {
    "Shaper tanh, drive 4": Shaper(Sine(220.0), "tanh", drive=4.0),
    "Shaper soft, drive 4": Shaper(Sine(220.0), "soft", drive=4.0),
    "Shaper hard, drive 4": Shaper(Sine(220.0), "hard", drive=4.0),
    "Saturator, drive 4, bias 0.2": Saturator(Sine(220.0), drive=4.0, bias=0.2),
}
fig, axes = plt.subplots(4, 1, figsize=(7, 5.6), sharex=True)
k = np.arange(1, 11)
for ax, (name, unit) in zip(axes, units.items()):
    amp = np.abs(np.fft.rfft(render(unit, 1.0))) * 2 / 48000
    level = np.maximum(20 * np.log10(amp[220 * k] + 1e-12), -80)
    ax.vlines(220 * k, -80, level, linewidth=3, colors=["C0" if i % 2 else "C1" for i in k])
    ax.set_ylim(-80, 5)
    ax.set_ylabel("dB")
    ax.set_title(name, fontsize=9, loc="left")
axes[-1].set_xticks(220 * k)
axes[-1].set_xlabel("frequency (Hz)")
fig.tight_layout()
show(fig, "Spectra of a 220 Hz sine through the three curves and the saturator: harmonics 1 to 10")
```

Listen to the two side by side, a shaper and a saturator at the same drive on a bass note at 110 Hz:

```python {run}
from euterpe.view import listen
from euterpe.sound import ADSR, Saturator, Shaper, Sine

note = lambda: Sine(110.0) * ADSR(attack=0.005, decay=0.4, sustain=0.6, gate=1.2, release=0.3)
display(listen(Shaper(note(), "tanh", drive=4.0) * 0.6, 1.6, "A 110 Hz note through tanh, drive 4: odd harmonics"))
listen(Saturator(note(), drive=4.0, bias=0.2) * 0.6, 1.6, "The same note through a saturator, drive 4, bias 0.2: odd and even")
```

### Two notes through one curve

A curve does not treat a sum of sines as separate sines. Any of these curves can be written, near 0, as a sum of powers of its input: x, x³, x⁵ and so on for an odd curve, which is why an odd curve on one sine gives odd harmonics. Feed it the sum of two notes, x + y, and the powers mix them: (x + y)³ = x³ + 3x²y + 3xy² + y³ already holds x²y and xy². Products of sines turn into sines at sums and differences of frequencies, by the high-school identity sin a × sin b = ½ [cos(a − b) − cos(a + b)]. So x²y, with x at f₁ and y at f₂, holds frequencies such as 2f₁ − f₂ and 2f₁ + f₂. Two notes through a distortion produce these new frequencies, called *intermodulation*.

When the two notes are a fifth apart (frequency ratio 3 : 2, here 220 Hz and 330 Hz), every combination is a multiple of 110 Hz, so the new frequencies are harmonics of a 110 Hz note and the result still sounds like one chord. When they are 6 equal steps apart (a ratio of 2^(6/12) = 1.414, an interval called a *tritone*, 220 Hz and 311.1 Hz), the combinations fall on no common series:

```python {run output=code}
import numpy as np

from euterpe.sound import Shaper, Sine, render

for top in (330.0, 311.1):
    x = render(Shaper(Sine(220.0) * 0.5 + Sine(top) * 0.5, "hard", drive=8.0), 10.0)
    amp = np.abs(np.fft.rfft(x))                # 10 s: one bin every 0.1 Hz
    loudest = sorted(np.argsort(amp)[-10:] / 10)
    print(f"220 + {top} Hz, the ten loudest (Hz):", ", ".join(f"{f:g}" for f in loudest))
```

The block renders 10 s so that the spectrum has a bin every 0.1 Hz and 311.1 Hz falls exactly on one; over 1 s the bins are 1 Hz apart and its energy would spill into the bins at 311 and 312 Hz. The fifth gives 110, 220, 330, 440 Hz and on, all multiples of 110: 110 Hz itself is 2 × 220 − 330. The tritone gives 128.9 Hz (2 × 220 − 311.1), 37.8 Hz (3 × 220 − 2 × 311.1), 402.2 Hz (2 × 311.1 − 220) and more, on no common series, a cluster that sounds rough:

```python {run}
from euterpe.view import listen
from euterpe.sound import ADSR, Shaper, Sine

for top, name in ((330.0, "a fifth"), (311.1, "a tritone")):
    chord = Shaper(Sine(220.0) * 0.5 + Sine(top) * 0.5, "hard", drive=8.0)
    display(listen(chord * ADSR(gate=1.7, release=0.2) * 0.5, 2.0, f"220 and {top:g} Hz, {name}, through a hard clip"))
```

This is why rock guitarists play only two notes a fifth apart through heavy distortion, the *power chord*.

## Dynamics

*Dynamics* units watch how loud their source is and change its gain as it plays. To do that they need a *level detector*: a running measure of loudness. Euterpe's detector squares the samples, averages them over about 10 ms and takes the square root, the RMS of chapter 2, so a full-scale sine reads −3 dB.

### Compressor

`Compressor(src, threshold, ratio, attack, release, makeup)` leaves the source alone while its level is below `threshold` dB. Above it, every `ratio` dB more of input gives only 1 dB more of output. A sound 20 dB above a threshold of −30 dB, through ratio 4, comes out 20 / 4 = 5 dB above it, at −25 dB: the compressor took 15 dB away. The *makeup* gain in dB is added at the end, to bring the quieter result back up.

The rule is a small function of the input level, here with threshold −30 dB and ratio 4:

```python {run output=code}
def compressed(level, threshold=-30.0, ratio=4.0):
    return level if level < threshold else threshold + (level - threshold) / ratio

for level in (-40, -30, -20, -10, 0):
    print(f"in {level:4d} dB -> out {compressed(level):6.1f} dB")
```

Here is a saw at 110 Hz whose level jumps every second, quiet, loud, then medium. `Segments` takes (time, value) pairs and draws straight lines between them, as in chapter 4; two pairs at the same time make a jump. A saw's RMS is its peak divided by √3 (chapter 2), so the quiet step at 0.05 should read 20 × log₁₀(0.05 / √3) = −30.8 dB. The block measures the RMS of each second, before and after a compressor with threshold −30 dB and ratio 4:

```python {run output=code}
import numpy as np

from euterpe.sound import Compressor, Saw, Segments, render

steps = [(0, 0.05), (1, 0.05), (1, 0.6), (2, 0.6), (2, 0.15), (3, 0.15)]
before = render(Saw(110.0) * Segments(steps), 3.0)
after = render(Compressor(Saw(110.0) * Segments(steps), threshold=-30.0, ratio=4.0), 3.0)
db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)))
for s in range(3):
    part = slice(s * 48000 + 4800, (s + 1) * 48000)   # skip the first 0.1 s of each second
    print(f"second {s + 1}: in {db(before[part]):6.1f} dB, out {db(after[part]):6.1f} dB")
```

The first second, at −30.8 dB, is under the threshold and comes through untouched. The second, at −9.2 dB, comes out at −25.1 dB, within a few tenths of the rule's −24.8 dB. The difference between the loudest and quietest second fell from 21.6 dB to 5.7 dB. That is what a compressor is for: it shrinks the range between loud and soft, so a voice stays audible over a band, or a whole song sounds dense and even.

`attack` and `release` set how fast the gain follows the level: how quickly it comes down when the level rises and how quickly it goes back up when the level falls. Each is a *time constant*, chapter 4's time scale: the time the gain takes to cover 63 % of the way to its new value. The plot shows the level every 10 ms, before and after, with the defaults, attack 10 ms and release 100 ms:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import Compressor, Saw, Segments, render

steps = [(0, 0.05), (1, 0.05), (1, 0.6), (2, 0.6), (2, 0.15), (3, 0.15)]
before = render(Saw(110.0) * Segments(steps), 3.0)
after = render(Compressor(Saw(110.0) * Segments(steps), threshold=-30.0, ratio=4.0), 3.0)


def level(x, size=480):
    frames = x[: len(x) // size * size].reshape(-1, size)
    return 10 * np.log10((frames ** 2).mean(axis=1) + 1e-12)


t = np.arange(len(before) // 480) * 0.01
fig, ax = plt.subplots(figsize=(7, 2.8))
ax.plot(t, level(before), label="before")
ax.plot(t, level(after), label="after the compressor")
ax.axhline(-30, color="0.6", linestyle="--", linewidth=1, label="threshold")
ax.set_xlabel("time (s)")
ax.set_ylabel("level (dB, 10 ms)")
ax.legend(fontsize=8, loc="lower right")
fig.tight_layout()
show(fig, "Level of the stepped saw before and after Compressor(threshold=-30, ratio=4), every 10 ms")
```

The block reads the numbers off the plot's orange line: its 10 ms levels from 1.00 s, the lowest level after 2 s, and when it gets back to within 1 dB of where it settles:

```python {run continue output=code}
out = level(after)                       # one level every 10 ms, from the plot
print("from 1.00 s:", "  ".join(f"{v:.1f}" for v in out[100:106]), "dB")
low = 200 + int(out[200:].argmin())
settled = out[290:].mean()
back = 200 + int(np.argmax(out[200:] > settled - 1))
print(f"lowest after 2 s: {out[low]:.1f} dB at {low / 100:.2f} s; within 1 dB of {settled:.1f} dB at {back / 100:.2f} s")
```

*Attack.* At the jump to the loud step, at 1 s, the output overshoots for about 40 ms before it settles near −25 dB. Two delays add up there: the detector's 10 ms average needs time to see the new level, and the gain then follows what it sees with its own 10 ms attack. A slower attack lets more of the start of each note through, which keeps the click of a drum or a plucked string.

*Release.* At 2 s the level drops, but the gain is still low, so the output dips well below where it settles and climbs back with the 100 ms release, taking about 0.2 s.

*Pumping.* A fast release makes the gain spring back soon after each loud note, so the quiet tail of every note swells as the gain recovers. Producers call the sound *pumping*, and some music uses it on purpose.

A compressor is easiest to hear on a note that starts loud and decays, such as a pluck. The second version goes through a compressor with a very low threshold, −55 dB, ratio 8, release 0.2 s and 30 dB of makeup gain, then is scaled by 0.5 and passes a `Limiter`, the next section's unit, for a reason the measurement shows:

```python {run}
from euterpe.view import listen
from euterpe.sound import Compressor, Limiter, Pluck

held = Compressor(Pluck(196.0, damping=0.99), threshold=-55.0, ratio=8.0, attack=0.005, release=0.2, makeup=30.0)
display(listen(Pluck(196.0, damping=0.99) * 0.5, 4.5, "A pluck at 196 Hz, dry"))
listen(Limiter(held * 0.5, ceiling=-1.5), 4.5, "The same pluck compressed: threshold -55 dB, ratio 8, makeup 30 dB")
```

The block measures 0.1 s every half second of the compressor's input, the plain pluck, and of its output, both before the 0.5 and the limiter, so the rows compare directly. The third row is what the rule predicts from the input row: −55 + (input + 55) / 8 above the threshold, the input itself below it, plus the 30 dB of makeup:

```python {run output=code}
import numpy as np

from euterpe.sound import Compressor, Pluck, render

db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)))
level = lambda x: [db(x[i * 24000 : i * 24000 + 4800]) for i in range(6)]
into = level(render(Pluck(196.0, damping=0.99), 3.0))
out = level(render(Compressor(Pluck(196.0, damping=0.99), threshold=-55.0, ratio=8.0, attack=0.005, release=0.2, makeup=30.0), 3.0))
rule = [(v if v < -55 else -55 + (v + 55) / 8) + 30 for v in into]
for name, row in (("second", [0, 0.5, 1, 1.5, 2, 2.5]), ("input", into), ("output", out), ("rule", rule)):
    print(f"{name:>6}:", "  ".join(f"{v:6.1f}" for v in row))
```

From 0.5 s to 2.0 s the input falls 28.4 dB, about 19 dB a second, and the output falls 3.2 dB, about 2.1 dB a second, close to the 19 / 8 = 2.4 dB a second of the rule: the note holds its tail as if it were still being played. The output sits about 3.5 dB below the rule's row because of the release: as the note falls, the gain should rise by 19 × 7 / 8 = 16.6 dB a second, and a gain that follows with a 0.2 s time constant trails about 0.2 s behind, 16.6 × 0.2 = 3.3 dB short (set `release=0.001` and the two rows agree within 0.1 dB). At 0 s the output is −0.2 dB, nearly full scale: the first 5 ms pass before the gain has come down, and the makeup lifts them 30 dB, which is why the version you heard is halved and limited. Between 2.0 and 2.5 s the input falls below −55 dB, from −53.4 to −62.5, and from there the output only adds the makeup and falls as fast as the note.

### Limiter

A *limiter* is a compressor that never lets a sample pass its ceiling. `Limiter(src, ceiling, release)` does that by looking ahead: it delays the source by 5 ms, 240 samples, so it sees each peak before it plays it, and lowers the gain over those 240 samples to arrive exactly at the ceiling. After the peak the gain returns to 1 with time constant `release`. It is the last unit before a file is written, the guard against clipping.

Here a sine at four times full scale, which would clip badly, goes through a limiter at −1 dBFS:

```python {run output=code}
import numpy as np

from euterpe.sound import Limiter, Sine, render

loud = render(Sine(220.0) * 4.0, 1.0)
safe = render(Limiter(Sine(220.0) * 4.0, ceiling=-1.0), 1.0)
print(f"before: peak {20 * np.log10(np.abs(loud).max()):.2f} dBFS")
print(f"after:  peak {20 * np.log10(np.abs(safe).max()):.2f} dBFS")
print("delay:", np.argmax(safe != 0) - np.argmax(loud != 0), "samples")
```

The peak sits at the ceiling, and the output starts 240 samples, 5 ms, late. The plot shows what the lookahead is for. A sine at 0.3 jumps to 3.0 at 40 ms. The input is drawn shifted 5 ms later, lined up with the output, and the gain is the output divided by it. The gain starts to fall 5 ms before the jump, while the sound is still quiet, so it reaches 0.891 / 3.0 = 0.30 exactly as the loud part arrives, and no sample crosses the dashed ceiling:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import Limiter, Segments, Sine, render

level = lambda: Segments([(0.0, 0.3), (0.04, 0.3), (0.04, 3.0), (0.1, 3.0)])
dry = render(Sine(220.0) * level(), 0.1)
out = render(Limiter(Sine(220.0) * level(), ceiling=-1.0, release=0.05), 0.1)
late = np.concatenate([np.zeros(240), dry[:-240]])        # the input, 5 ms later
t = np.arange(len(out)) / 48 + 0.0                          # milliseconds
gain = np.where(np.abs(late) > 0.05, out / np.where(late == 0, 1, late), np.nan)
fig, (top, bottom) = plt.subplots(2, 1, figsize=(7, 4.4), sharex=True)
top.plot(t, late, color="0.75", linewidth=0.8, label="input, 5 ms later")
top.plot(t, out, linewidth=0.9, label="output")
for c in (0.891, -0.891):
    top.axhline(c, color="C3", linestyle="--", linewidth=1)
top.set_ylim(-3.2, 3.2)
top.legend(fontsize=8, loc="upper left")
bottom.plot(t, gain, linewidth=1)
bottom.axvline(45, color="0.6", linestyle=":", linewidth=1)
bottom.axvline(40, color="0.6", linestyle=":", linewidth=1)
bottom.set_ylabel("gain")
bottom.set_ylim(0, 1.1)
bottom.set_xlim(20, 100)
bottom.set_xlabel("time at the output (ms)")
fig.tight_layout()
show(fig, "A sine jumping from 0.3 to 3.0 through Limiter(ceiling=-1): the gain ramps down over the 5 ms before the jump")
```

A limiter that works this hard flattens the top of every cycle, which is distortion: on a steady loud sine it is a shaper. Its job is to catch rare peaks, not to make a quiet sound loud.

### Gate

A *gate* is the opposite of a compressor: it turns the quiet parts down, to silence. `Gate(src, threshold, release)` passes its source while the level is above `threshold` dB and closes, fading to silence with time constant `release`, when it drops below. It opens in about 1 ms. The classic use is to remove noise between notes: the hiss of an amplifier, the bleed of other instruments into a drum's microphone.

Here a pluck sits on a background of quiet hiss with an RMS of −59 dB (white noise at 0.002: its samples are spread evenly between −1 and 1, so its RMS is 1/√3 = 0.577 of its peak). A gate at −45 dB lets the note through and closes once the note falls below it:

```python {run}
from euterpe.view import listen
from euterpe.sound import Gate, Pluck, WhiteNoise

noisy = lambda: Pluck(262.0, damping=0.99) * 0.6 + WhiteNoise(seed=2) * 0.002
display(listen(noisy(), 3.0, "A pluck over quiet hiss"))
listen(Gate(noisy(), threshold=-45.0, release=0.1), 3.0, "The same through a gate at -45 dB")
```

The hiss is gone from the end, but notice what else the gate takes: the last, quietest part of the note's decay is cut off with it. A gate cannot tell a quiet note from noise at the same level.

## Reverb

Clap your hands in a large hall. The sound reaches your ears first directly, then again from every wall, the ceiling, the floor, and from paths that bounce off several of them. The first few reflections arrive as separate echoes. After a few tens of milliseconds there are so many, so close together, that they blur into a smooth tail that fades away. That tail is *reverberation*, and how long it takes to fade is the main thing that makes a bathroom sound different from a cathedral.

Rooms are measured by their *RT60*: the time the reverberation takes to fall by 60 dB, from loud to about silent. A living room has an RT60 of about 0.4 s, a concert hall about 2 s, a large stone church 5 s or more.

### Feedback delay network

A delay with feedback makes one train of echoes, evenly spaced, which sounds metallic. A room makes echoes whose number grows every millisecond. `FDNReverb(src, decay, size, damping, mix)` copies that with a *feedback delay network*: eight delay lines of different lengths, between 30 and 90 ms at size 1, scaled by `size` (default 0.7) and each moved by up to 10 % by the seed. A stereo source is mixed to mono before the lines. The output of every line is mixed into the input of every other line, each with a sign + or −, so each echo that comes out of one line goes into all eight. One click becomes 8 echoes, then 64, then 512: after a few trips round the network the echoes are too dense to tell apart.

Each line has a gain below 1, chosen from its length so that the tail falls 60 dB in `decay` seconds. A line of L samples is passed 48 000 / L times a second, so its gain is 10^(−3 × L / (48 000 × decay)): in decay seconds that compounds to 10^(−3) in level, −60 dB. `damping` puts a low-pass inside each line, so the high frequencies die faster than the low ones, as they do in a room with soft surfaces. `mix` sets how much reverb is heard against the dry sound.

The plot shows a single click through two reverbs, both with decay 1.5 s: the network, with its defaults size 0.7 and damping 0.3, and the convolution reverb of the next section. The top half shows the first 80 ms, where the network's echoes are still separate spikes; the bottom half shows the level of both over 2.5 s, falling in a straight line in dB, which is what an exponential decay looks like:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import ConvolutionReverb, FDNReverb, Segments, render

click = lambda: Segments([(0.0, 1.0), (1 / 48000, 0.0)])
fdn = render(FDNReverb(click(), decay=1.5, mix=1.0), 2.5)[:, 0]
conv = render(ConvolutionReverb(click(), decay=1.5, mix=1.0), 2.5)[:, 0]
fig, (top, bottom) = plt.subplots(2, 1, figsize=(7, 4.6))
t = np.arange(len(fdn)) / 48000
n = int(0.08 * 48000)
top.plot(t[:n] * 1000, fdn[:n], linewidth=0.7, label="FDN")
top.plot(t[:n] * 1000, conv[:n] - 0.3, linewidth=0.7, label="convolution (shifted down)")
first = np.argmax(np.abs(fdn) > 1e-6) / 48
top.annotate(f"first echo {first:.1f} ms", (first, 0.02), (first + 4, 0.18), fontsize=8, arrowprops={"arrowstyle": "->"})
top.set_xlabel("time (ms)")
top.legend(fontsize=8, loc="upper right")
size = 480
for name, x in (("FDN", fdn), ("convolution", conv)):
    frames = x[: len(x) // size * size].reshape(-1, size)
    bottom.plot(np.arange(len(frames)) * 0.01, 10 * np.log10((frames ** 2).mean(axis=1) + 1e-14), label=name, linewidth=1)
bottom.axvline(1.5, color="0.6", linestyle="--", linewidth=1)
bottom.set_xlabel("time (s)")
bottom.set_ylabel("level (dB, 10 ms)")
bottom.legend(fontsize=8)
fig.tight_layout()
show(fig, "A click through FDNReverb and ConvolutionReverb, both decay 1.5 s: the first 80 ms, and the level over 2.5 s")
```

The convolution reverb's line falls 60 dB from its start to the dashed line at 1.5 s. The network's falls a little faster: its damping removes the high frequencies sooner, and `decay` holds for the low ones. Its first echo arrives after 21.6 ms, marked on the plot: the shortest line, 30 ms × 0.7 = 21 ms, moved a little by the seed. Here is a short pluck, dry, in a small room and in a large hall:

```python {run}
from euterpe.view import listen
from euterpe.sound import FDNReverb, Pluck

display(listen(Pluck(392.0, damping=0.98) * 0.6, 3.0, "A short pluck at 392 Hz, dry"))
display(listen(FDNReverb(Pluck(392.0, damping=0.98), decay=0.5, size=0.3, mix=0.3) * 0.6, 3.0, "In a small room: decay 0.5 s, size 0.3"))
listen(FDNReverb(Pluck(392.0, damping=0.98), decay=3.0, size=1.0, damping=0.5, mix=0.4) * 0.6, 5.0, "In a large hall: decay 3 s, size 1, damping 0.5")
```

`size` scales the delay lines. A small size packs the early echoes close together and the room sounds small even with a long decay, like a tiled bathroom. A large size spreads them, and you start to hear the space before the tail.

The reverb's output is stereo even for a mono source. The left side is one mix of the eight lines and the right side another, with different signs, so the two sides carry different echoes. Through headphones the reverb surrounds the dry note instead of sitting inside it.

### Convolution reverb

The other way to make reverb starts from a recording of a click in a real room: its *impulse response*, everything the room does to one instant of sound. Any sound is a long row of instants, one per sample, and each one makes the room answer with a copy of the impulse response, scaled by that sample. Adding all those copies is called *convolution*, and the result is the sound played in that room. Done that way it costs a lot: with a response 3 s long, 144 000 samples, every output sample needs 144 000 multiplications. The FFT makes it cheaper, because convolving two signals is the same as multiplying their spectra frequency by frequency, and an FFT computes a spectrum in far fewer steps than that; why the two are the same is beyond this book.

`ConvolutionReverb(src, decay, mix, seed)` has no recording to use. It synthesizes the impulse response: white noise, a different one on each side, whose level falls 60 dB in `decay` seconds. The plot above shows it next to the network: dense from the very first millisecond, with no separate early echoes. Listen to both on the same pluck, both with a decay of 2 s:

```python {run}
from euterpe.view import listen
from euterpe.sound import ConvolutionReverb, FDNReverb, Pluck

display(listen(FDNReverb(Pluck(392.0, damping=0.98), decay=2.0, mix=0.35) * 0.6, 4.0, "A pluck through FDNReverb, decay 2 s"))
listen(ConvolutionReverb(Pluck(392.0, damping=0.98), decay=2.0, mix=0.35) * 0.6, 4.0, "The same pluck through ConvolutionReverb, decay 2 s")
```

The convolution tail is smoother and brighter. Its noise holds every frequency at the same level for the whole decay, so the high frequencies last as long as the low ones; the network, with its damping, darkens as it fades, as a real room does. With a recorded response instead of noise, a convolution reverb sounds like one particular real room.

## Stereo

A stereo file has two channels, one for each speaker. A sound placed only in the left channel seems to come from the left; one with the same level in both seems to come from between the speakers.

### Pan

`Pan(src, pos)` places a mono sound: `pos` −1 is fully left, 0 the middle, 1 fully right. Recall from chapter 2 that power goes as amplitude squared. The obvious rule, with p = (pos + 1) / 2 running from 0 to 1, left gain 1 − p and right gain p, makes the sound quieter in the middle: two speakers at half level carry half the power of one at full level, 2 × 0.5² = 0.5, which is −3 dB. So `Pan` uses a *constant-power* rule. It turns `pos` into an angle θ = (pos + 1) × π / 4, from 0 to π / 2, and uses cos θ for the left and sin θ for the right. Since cos² θ + sin² θ = 1, the total power never changes:

```python {run output=code}
import numpy as np

for pos in (-1.0, -0.5, 0.0, 0.5, 1.0):
    theta = (pos + 1) * np.pi / 4
    left, right = np.cos(theta), np.sin(theta)
    print(f"pos {pos:+.1f}: left {left:.3f}, right {right:.3f}, power {left ** 2 + right ** 2:.3f}")
```

In the middle each side gets 0.707, −3 dB. `pos` can be a unit, so a slow sine moves the sound from side to side, an *auto-pan*. Listen to this one through headphones:

```python {run}
from euterpe.view import listen
from euterpe.sound import ADSR, Biquad, Pan, Saw, Sine

tone = Biquad(Saw(220.0), "lowpass", cutoff=1500.0) * ADSR(gate=7.4, release=0.5) * 0.5
listen(Pan(tone, pos=Sine(0.25)), 8.0, "A saw moving from side to side, once every 4 seconds")
```

### Width

`Width(src, width)` changes how wide an existing stereo sound is. It splits the sound into a *mid* channel, (L + R) / 2, the part both sides share, and a *side* channel, (L − R) / 2, the part where they differ. It multiplies the side by `width` and puts the two back together: L = M + S, R = M − S. Width 0 removes the side, so both speakers play the same thing, mono. Width 1 changes nothing. Width 2 doubles the difference, and the sound seems to spread beyond the speakers.

The reverb's tail is a good thing to try it on, because its two sides differ:

```python {run}
from euterpe.view import listen
from euterpe.sound import FDNReverb, Pluck, Width

for width in (0.0, 1.0, 2.0):
    wet = FDNReverb(Pluck(330.0, damping=0.98), decay=2.0, mix=0.5) * 0.5
    display(listen(Width(wet, width=width), 3.0, f"A reverberant pluck at width {width:g}"))
```

At width 0 the tail sits in the middle of your head; at 2 it spreads around it. The dry pluck itself is the same on both sides, all mid, so its position does not change.

## Putting a chain together

Effects are usually chained in a fixed order, the order a guitarist puts pedals on the floor: first what shapes the tone (distortion), then what moves it (chorus), then what places it in time and space (delay, reverb), and last a limiter that guards the output. Every unit in this chain is one met in this chapter:

```python {run}
from euterpe.view import listen
from euterpe.sound import Chorus, Delay, FDNReverb, Limiter, Pan, Pluck, Saturator

note = Pluck(147.0, damping=0.995, brightness=0.7)
tone = Chorus(Saturator(note, drive=3.0, bias=0.2), rate=0.6, depth=0.002)
space = FDNReverb(Pan(Delay(tone, time=0.375, feedback=0.4, mix=0.3), pos=-0.3), decay=2.5, mix=0.3)
listen(Limiter(space * 0.9, ceiling=-1.0), 7.0, "A pluck at 147 Hz: saturator, chorus, delay, pan, reverb and limiter")
```

`FDNReverb` mixes its source to mono, so the `Pan` before it places the dry part of the sound, and the reverb fills both sides. Change the order and the sound changes. Distortion after the reverb would distort every echo of the tail together, and each echo would intermodulate with the others; in the chain above, the chorus comes before the delay, so every echo repeats the shimmer of the note. With the delay first, each echo would pass through the chorus at a different moment of its sweep and shimmer differently.

## Summary

- An effect is a unit whose source is another unit, so effects chain.
- `Delay(src, time, feedback, mix)` adds the source again after `time` seconds; `feedback` repeats it, each echo `feedback` times the last. Below about 30 to 50 ms the copy is not heard as an echo but as a comb filter, with peaks every 1 / time Hz.
- A delay that changes while it plays shifts the pitch of the copy by the rate of change. `Chorus` uses a 20 ms delay that swings a few cents of pitch, which thickens a sound; `Flanger` sweeps a delay of 0.5 ms to 0.5 ms + depth, which slides a whole comb of peaks up and down; `Phaser` sweeps a chain of allpasses, which slides a few notches, half as many as stages, rounded down.
- `Shaper(src, kind, drive)` bends each sample through tanh, a soft cubic or a hard clip. An odd curve adds odd harmonics only; more drive and a harsher curve make them louder. `Saturator` shifts the wave before the curve, which adds even harmonics too. Two notes through a curve also produce sums and differences of their frequencies, intermodulation.
- `Compressor(src, threshold, ratio, attack, release, makeup)` divides by `ratio` how far the level goes above `threshold`: it shrinks the range between loud and soft. `Limiter(src, ceiling, release)` looks 5 ms ahead and keeps every sample under `ceiling`. `Gate(src, threshold, release)` silences what is quieter than `threshold`.
- Reverb is the dense tail of echoes a room adds; RT60 is the time it takes to fall 60 dB. `FDNReverb(src, decay, size, damping, mix)` makes it with eight delay lines feeding each other; `ConvolutionReverb(src, decay, mix, seed)` convolves the source with a synthesized impulse response of decaying noise.
- `Pan(src, pos)` places a mono sound between the speakers at constant power, cos θ left and sin θ right. `Width(src, width)` scales the difference between the sides: 0 is mono, 2 twice as wide.

## Exercises

1. In the first echo block, change `feedback=0.45` to `feedback=0.8`, and the render length from `3.0` to `6.0` to hear the echoes out. How many dB quieter is each echo than the one before, and which echo is the first one 30 dB below echo 1?
2. In the flanger block, change `feedback=0.7` to `feedback=-0.7`. Where are the peaks of the comb when the delay is at its shortest, 0.5 ms?
3. In the compressor's measurement block on the stepped saw, change `ratio=4.0` to `ratio=2.0`. Use the rule to predict the output level of the second second, then run the block to check it.
4. In the saturator's measurement block, change `bias=0.2` to `bias=0.0`. What happens to the 2nd, 4th and 6th harmonics, and why?
5. An FDN line is 1 440 samples long (30 ms) and decay is 2 s. What is its gain, how many dB does one trip lose, and how many trips does the sound make in 2 s?
6. In the width block, replace the reverb with a pluck panned fully right, `wet = Pan(Pluck(330.0, damping=0.98), pos=1.0) * 0.5` (add `Pan` to the import), and listen at width 0. Where is the sound, and how much power does it keep?

### Answers

1. Each echo is 0.8 times the one before: 20 × log₁₀ 0.8 = −1.94 dB. Echo k is (k − 1) × 1.94 dB below echo 1, and 30 / 1.94 = 15.5, so k − 1 must be 16: echo 17 is the first one 30 dB down. At 0.3 s apart it comes 16 × 0.3 = 4.8 s after echo 1.
2. With negative feedback the copy is flipped on each trip and mixed in upside down, so a frequency is reinforced when an odd number of half periods fits into the delay. The peaks move to the odd multiples of 1 / (2 × 0.0005) = 1 000 Hz: 1 000, 3 000, 5 000 Hz, and the dips to 0, 2 000, 4 000 Hz. The sweep sounds hollower, with no peak at the bottom of the spectrum.
3. The second second goes in at −9.2 dB, 20.8 dB above the threshold. Ratio 2 halves that: −30 + 20.8 / 2 = −19.6 dB. The block prints a value within a few tenths of that.
4. They fall to about −90 dB, some 70 dB below the odd ones, so they are gone to the ear; what is left comes from the start of the render, while the 10 Hz high-pass settles. With bias 0 the curve is tanh(drive / 2 × x), an odd curve, so the two halves of the sine are bent the same way and only odd harmonics remain. The odd harmonics now match the `tanh` row of the shaper's table exactly, since the curve is the same.
5. The gain is 10^(−3 × 1 440 / (48 000 × 2)) = 10^(−0.045) = 0.902, so one trip loses 20 × log₁₀ 0.902 = −0.9 dB. A trip takes 30 ms, so in 2 s the sound makes 2 / 0.03 = 66.7 trips, and 66.7 × 0.9 = 60 dB: the RT60 is 2 s, as set.
6. Panned fully right, the left side is 0 and the right side is the pluck, x. Width 0 keeps only the mid, (0 + x) / 2, on both sides, so the sound moves to the middle with each side at x / 2. Its power is 2 × 0.5² = 0.5 of what it was, −3 dB: the constant-power rule of `Pan` does not hold for Width.

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
