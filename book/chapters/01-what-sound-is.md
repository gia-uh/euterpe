# What sound is

A sound is a change in air pressure that reaches your ear. This chapter follows that change from the air into a computer: how it is measured, how many numbers a second of sound takes, what goes wrong when there are too few, and how coarse each number can be before you hear it.

## Pressure over time

Air at sea level presses on everything with about 101 325 pascals. A sound is a small, fast change on top of that value. Ordinary speech moves the pressure at your ear by about 0.02 pascals, two parts in ten million. The change travels away from its source at about 343 metres per second, at room temperature.

Your eardrum moves with the pressure, and the inner ear turns that motion into nerve signals. So a sound, for our purposes, is one number that changes over time: the pressure at one point. A microphone measures that number, a loudspeaker produces it, and a program can compute it.

The simplest sound repeats one shape forever. The shape is a sine wave, and the number of times it repeats each second is its frequency, measured in hertz (Hz). Here is a sine wave at 440 Hz, two seconds long, at half of full scale (full scale is the largest value a sound file can hold).

Euterpe calls anything that produces sound a *unit*. `Sine(440.0)` is a unit. `Sine(440.0) * 0.5` builds a new unit that takes each value of the sine and multiplies it by 0.5; in the same way `a + b` builds a unit that adds two units value by value, and a plain number on either side counts as a constant. Building units computes nothing yet. `listen` computes two seconds of sound from the unit it is given and puts a player on this page.

```python {run}
from euterpe.view import listen
from euterpe.sound import Sine

tone = Sine(440.0) * 0.5
listen(tone, 2.0, "A sine wave at 440 Hz")
```

`listen` lives in `euterpe.view`, with the drawings that show a sound, apart from the sounds themselves in `euterpe.sound`. It returns a player: the book and a notebook show the last line of a block, and `display(listen(...))` shows one anywhere else.

A tone held at one steady frequency in a piece of music is a *note*. This one is the note musicians call A, the one orchestras tune to (chapter 2 explains note names). A sine is the plainest tone there is: it sounds like a tuning fork or a soft whistle. Every other sound in this book is built from sines, or analysed as a sum of them, so it is worth knowing well.

One cycle at 440 Hz lasts 1/440 of a second, about 2.27 milliseconds. In that time the sound travels 343 / 440 = 0.78 metres, which is the length of one wave in the air. Here are the first 5 milliseconds as a plot:

```python {run echo=false}
from euterpe.sound import Sine

(Sine(440.0) * 0.5).take(0.005).waveform(caption="The first 5 ms of the 440 Hz sine: a little over two cycles")
```

The vertical axis is not in pascals. Inside a computer a sound is a number between −1 and 1, and the loudspeaker and its volume knob decide how many pascals that becomes. That is why a value of 1 is called *full scale*: it means the most the file can hold, not a pressure. The largest value a wave reaches is its *amplitude*: the sine above has amplitude 0.5, half of full scale.

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
from euterpe.sound import Sine

(Sine(440.0) * 0.5).take(0.001).waveform(samples=True, caption="The first millisecond: 48 samples of the 440 Hz sine")
```

At 440 Hz there are 48 000 / 440, about 109 samples per cycle. The minimum is a little more than 2 samples per cycle, and the next section shows why. Below that, the samples no longer pin down the wave.

## The Nyquist limit

Take a sine at some frequency f and a second sine at 48 000 − f. Put the second one into the formula:

sin(2π · (48 000 − f) · n / 48 000) = sin(2π · n − 2π · f · n / 48 000)

Two facts finish the argument. First, a sine repeats every full cycle, sin(x + 2π) = sin(x), and n is a whole number, so taking away 2π · n changes nothing. Second, a sine run backwards is the same shape upside down: sin(−x) = −sin(x). Together:

sin(2π · (48 000 − f) · n / 48 000) = −sin(2π · f · n / 48 000)

The samples of the sine at 48 000 − f are the samples of the sine at f, upside down: every sample has the opposite sign. The ear cannot hear that difference. Turning a sine upside down is the same as shifting it in time by half a cycle, and the ear does not hear a constant shift in time of a steady tone (a shift of where its cycle starts, called its *phase* and measured in cycles); it hears the frequency and the amplitude. So after sampling, a sine at 48 000 − f sounds exactly like a sine at f, although each of its samples is the negative of the other's.

With numbers: a sine at 44 000 Hz advances 44/48 of a cycle from one sample to the next. Since a full cycle brings it back to where it was, 44/48 of a cycle forward lands on the same point as 4/48 of a cycle backward, and 4/48 of a cycle per sample is what a 4 000 Hz sine advances. Going backward through a sine traces it upside down. Comparing the two, one millisecond of samples:

```python {run output=code}
import numpy as np

n = np.arange(48)  # one millisecond of sample numbers
high = np.sin(2 * np.pi * 44_000 * n / 48_000)
low = np.sin(2 * np.pi * 4_000 * n / 48_000)
print(np.abs(high - (-low)).max())  # largest difference between high and low upside down
```

The difference is rounding error in the last digits of the floats. In the plot, the thin line is the 44 000 Hz wave and the thick one is the 4 000 Hz wave turned upside down; the samples, the dots, lie on both.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.view import figure


def draw():
    ms = np.linspace(0, 0.5, 4000)
    n = np.arange(25)
    fig, ax = plt.subplots(figsize=(7, 2.5))
    ax.plot(ms, np.sin(2 * np.pi * 44_000 * ms / 1000), color="#9aa0a8", linewidth=0.7, label="44 000 Hz")
    ax.plot(ms, -np.sin(2 * np.pi * 4_000 * ms / 1000), linewidth=2, label="4 000 Hz, upside down")
    ax.plot(n / 48, np.sin(2 * np.pi * 44_000 * n / 48_000), "o", markersize=4, label="the samples")
    ax.set_xlabel("time (ms)", fontstyle="italic")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=3, fontsize=8, frameon=False)
    return fig


figure(draw, caption="Half a millisecond: a 44 000 Hz sine and a 4 000 Hz sine share their samples")
```

Adding 48 000 Hz to a frequency adds exactly one cycle per sample, which also changes nothing at the moments the samples are taken. Together with the pairing of f and 48 000 − f, the samples of a sine at f are shared by infinitely many frequencies: f + 48 000, f + 96 000 and so on, and, upside down, 48 000 − f, 96 000 − f and so on. Exactly one of them lies between 0 and 24 000 Hz, and playback, as the next section shows, produces that one. That midpoint, half the sample rate, is the *Nyquist frequency*. A wave above it does not disappear: it *folds back* to the one frequency of its family below 24 000 Hz. This is called *aliasing*. The frequency it lands at is the distance from f to the nearest multiple of 48 000: 44 000 Hz lands at 4 000 Hz, 50 000 Hz at 2 000 Hz.

In samples per cycle, the rule is the same. A frequency f gets 48 000 / f samples per cycle, and f below 24 000 means more than 2 samples per cycle. Exactly 2 is not enough: a sine at 24 000 Hz is sampled at sin(π · n), which is 0 for every whole n, so its samples are all zeros.

### What playback puts between the samples

If 44 000 Hz and 4 000 Hz have the same samples, why does a loudspeaker play 4 000 Hz? The answer uses a fact that chapter 3 shows: any wave that repeats is a sum of sines, and any other sound can be built from sines too. So a wave can be described by which frequencies it contains, and a wave that "contains nothing above 24 000 Hz" is one built only from sines below 24 000 Hz.

The *sound card* is the part of a computer that drives the loudspeaker, and its *converter* turns the list of samples into a voltage that varies smoothly. It draws through the samples the one smooth wave that contains nothing above 24 000 Hz. It does that with a *filter*, a process that weakens some frequencies and keeps others: this one keeps everything below 24 000 Hz and removes everything above. Through the samples of the 44 000 Hz sine, the only wave below 24 000 Hz is the 4 000 Hz one, so that is what you hear.

Why is there exactly one such wave? For a single sine, the last section showed it: of all the frequencies that share its samples, one lies below 24 000 Hz. The *Nyquist–Shannon sampling theorem* says the same holds for any sum of sines: through a list of samples passes exactly one wave built only from sines below half the sample rate. This chapter takes the theorem as given; it is proved later in the book.

This does not contradict "between two samples there is nothing". The file stores nothing there. Playback fills the gaps under one assumption: the sound had nothing above half the sample rate. When that holds, the fill is exact and the original wave comes back. When it does not hold, playback assumes it anyway, and a wave above the limit comes out as its partner below. Real converters come close to this ideal filter, not all the way.

Euterpe's *oscillators*, the units that make a repeating wave (`Sine` and the `Saw` below, with more in later chapters), guard against this at the source: asked for a frequency at or above 24 000 Hz, they output silence. The check is on the frequency you pass in and nothing else. `Saw(10_000.0)` is allowed, although most of what it contains lies above 24 000 Hz, as the next section shows.

### Why a saw wave folds back

A sine has one frequency, so it is easy to keep below the limit. Most sounds are not sines. A *saw wave* rises steadily from −1 to 1 and then drops back at once, once per cycle. Chapter 3 shows that such a wave is a sum of sines at every whole multiple of its frequency, called its *harmonics*: harmonic k is at k times the frequency and has 1/k of the first one's amplitude. A 10 000 Hz saw contains 10 000 Hz at amplitude 1, 20 000 Hz at 1/2, 30 000 Hz at 1/3, and so on without end. The first harmonic is the frequency you hear as the note.

Why does a saw have harmonics so far up? Because of the drop. A sine of frequency f takes half a cycle, 1 / (2f) seconds, to go from its lowest value to its highest, and it cannot get there faster. A sum of sines can change only as fast as its sines do, so the ideal saw, which drops in no time, needs harmonics without end (chapter 3). Sampled, it drops in one sample, 1/48 000 of a second, which takes sines above 24 000 Hz; the samples store only what lies below, and the rest folds back. A drop spread over two samples, 1/24 000 of a second, is half a cycle at 12 000 Hz, slow enough for sines below 24 000 Hz to draw.

Every harmonic above 24 000 Hz folds back. Here is the rule from the last section as a function, applied to the first seven harmonics of the 10 000 Hz saw:

```python {run output=code}
def fold(f, rate=48_000):
    """Where a frequency f lands after sampling at rate: its distance to the nearest multiple of rate."""
    return abs((f + rate / 2) % rate - rate / 2)

for k in range(1, 8):
    print(f"harmonic {k}: {10_000 * k:>6} Hz, heard at {fold(10_000 * k):>6.0f} Hz")
```

Adding `rate / 2` before the remainder `%` and taking it away after gives the signed distance from f to the nearest multiple of `rate`, between −24 000 and 24 000. `abs` drops the sign, which only turns the sine upside down.

The 5th harmonic, 50 000 Hz, is heard at 2 000 Hz, far below the note itself. A folded harmonic usually does not sit at a multiple of the note's frequency, so it does not blend into the note's tone. It sounds like a separate whistle that does not belong to the note.

To hear the difference, Euterpe's `Saw` can be told to skip its correction. With `antialias=False` it computes the wave the direct way: take the position in the cycle, from 0 to 1, and scale it to run from −1 to 1, with the whole drop between two samples. The normal `Saw` adds a small correction to the sample just before each drop and the sample just after it: it turns each cliff into a two-sample slope. The correction is called *polyBLEP*, for polynomial band-limited step. The plot shows a few samples around one drop of a 1 100 Hz saw:

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.sound import Saw, render
from euterpe.view import figure


def draw():
    plain = render(Saw(1_100.0, antialias=False), 0.002)
    smooth = render(Saw(1_100.0), 0.002)
    drop = int(np.argmax(np.diff(plain) < 0)) + 1  # the first sample after the drop
    n = np.arange(drop - 4, drop + 4)
    fig, ax = plt.subplots(figsize=(7, 2.5))
    ax.plot(n - drop, plain[n], "o-", label="antialias=False")
    ax.plot(n - drop, smooth[n], "s--", label="Saw, with polyBLEP")
    ax.set_xlabel("sample number (0 = the first sample after the drop)", fontstyle="italic")
    ax.legend(loc="lower left", frameon=False)
    return fig


figure(draw, caption="Eight samples around one drop of a 1 100 Hz saw: polyBLEP moves the two samples next to the drop")
```

Both saws below sweep from 1 000 Hz up to 23 000 Hz in four seconds (the captions write 1 000 Hz as 1 kHz, a kilohertz). Their frequency is not a number but a unit: a parameter may be either, and a saw given a unit reads its frequency from it again at every sample. The unit is half a cycle of a slow sine. `Sine(0.125)` completes one cycle every 8 seconds, so in 4 seconds it covers half a cycle. `phase`, from 0 to 1, sets where the sine starts: at phase 0 it starts at 0 and rises, and at phase 0.75 it starts three quarters through its cycle, at its lowest value, −1. Over the next half cycle it rises to 1. Times 11 000, that runs from −11 000 to 11 000; plus 12 000, from 1 000 to 23 000.

```python {run}
from euterpe.view import listen
from euterpe.sound import Saw, Sine

sweep = Sine(0.125, phase=0.75) * 11_000 + 12_000      # 1 000 Hz to 23 000 Hz in 4 s

display(listen(Saw(sweep) * 0.5, 4.0, "A saw sweeping from 1 to 23 kHz, band-limited"))
listen(Saw(sweep, antialias=False) * 0.5, 4.0, "The same sweep without the correction: aliasing")
```

Listen to the first sweep: one tone rises until it is too high to hear. Most adults stop hearing somewhere between 15 000 and 20 000 Hz, so the end of it may sound like silence. In the second sweep, other tones move down while the note moves up, and they stay audible after the note itself is gone. Those are folded harmonics.

A *spectrogram* shows the same thing as a picture. It cuts the sound into slices of 1 024 samples, about 21 ms each, measures how strong each frequency is in each slice, and draws one column per slice. Time runs left to right, frequency bottom to top, and brightness is the strength:

```python {run echo=false}
from euterpe.sound import Saw, Sine
from euterpe.view import spectrogram


def sweep():
    return Sine(0.125, phase=0.75) * 11_000 + 12_000


spectrogram(
    (Saw(sweep()) * 0.5).take(4.0),
    (Saw(sweep(), antialias=False) * 0.5).take(4.0),
    labels=["Saw", "Saw, antialias=False"], lo=500, hi=24_000,
    caption="The two sweeps: harmonics fold back from 24 kHz without the correction",
)
```

In the right panel each harmonic reaches the top edge, 24 000 Hz, and comes back down as a falling line. Those falling lines are the extra tones you heard. The left panel has them too, darker: polyBLEP reduces aliasing, it does not remove it. For most notes of real music that is enough: they sit far below 23 000 Hz, and the lower the note, the higher the number k of the first harmonic that folds, so its amplitude 1/k is smaller.

## How fine each sample is

Each sample is a number, and a file stores it with a fixed number of bits. With b bits a sample can take 2 to the power b different values (`2 ** b` in Python). CD audio uses 16 bits, 65 536 values. Rounding every sample to the nearest allowed value is called *quantisation*. The rounding error, the difference between the exact value and the rounded one, is a small signal added to the sound. It is never more than half the step between two neighbouring values. The range from −1 to 1 is 2 wide, so with b bits the step is 2 / (2**b − 1) and the largest error half of that. At 16 bits the largest error is 1/65 535 of full scale, too quiet to hear in normal listening, which is why 16 bits was enough for the CD.

A 32-bit float is finite too, so the samples Euterpe computes are already quantised, though far more finely than any file stores them. When `render(..., to="tone.wav")` writes a WAV file, an uncompressed file of samples, it stores 24-bit integers: each sample is multiplied by 8 388 608 (`2 ** 23`), rounded to a whole number and stored in 3 bytes. 24-bit signed integers go from −8 388 608 to 8 388 607, so a sample of exactly 1 is stored as 8 388 607. The largest error is half the step, 1/16 777 216 of full scale, far below hearing.

`BitCrush` rounds each sample to `2 ** bits - 1` levels spread evenly between −1 and 1. That is one level fewer than the bits allow, so that the levels are symmetric and 0 is one of them: silence stays silent. With one level fewer there is one gap fewer, so its step is 2 / (2**bits − 2): 1 at 2 bits, where the levels are −1, 0 and 1. Here is the 440 Hz sine with 16, 6, 4 and 2 bits:

```python {run}
from euterpe.view import listen
from euterpe.sound import BitCrush, Sine

for bits in (16, 6, 4, 2):
    display(listen(BitCrush(Sine(440.0), bits=bits) * 0.5, 2.0, f"The 440 Hz sine with {bits} bits"))
```

`BitCrush` acts on the full-scale sine, and `* 0.5` scales after. The order matters, because the levels stay between −1 and 1 whatever the input. At 2 bits they are −1, 0 and 1, and every sample of a half-scale sine is nearer to 0 than to either end: `BitCrush(Sine(440.0) * 0.5, bits=2)` rounds every sample to 0 and plays silence. Crushing first uses all the levels; scaling after turns them into −0.5, 0 and 0.5.

At 16 bits it sounds like the sine at the top of the chapter. At 6 bits a faint hiss sits under the tone. At 4 bits the tone is harsh. At 2 bits the wave has three levels, −0.5, 0 and 0.5, but it spends two thirds of each cycle at 0.5 or −0.5 and only a third at 0, so it sounds close to a *square wave*, a wave that jumps between two values and spends half of each cycle at each. The plot shows one cycle of each, before the scaling:

```python {run echo=false}
from euterpe.sound import BitCrush, Sine
from euterpe.view import waveform

waveform(
    *[BitCrush(Sine(440.0), bits=bits).take(1 / 440) for bits in (16, 4, 2)],
    labels=["16 bits", "4 bits", "2 bits"],
    caption="One cycle of the 440 Hz sine with 16, 4 and 2 bits",
)
```

Rounding changes the shape of the wave, so it adds frequencies that were not there. At 440 Hz a cycle is 48 000 / 440 = 109.09 samples, so the samples land at different points of the wave in each cycle. At 6 bits the error is small and depends on where each sample lands, so it does not repeat in a short pattern: its energy spreads thinly over many frequencies, heard as *hiss*, like a radio between stations. At 2 bits the error is as large as the wave and follows its shape in every cycle. An error that repeats with every cycle is made of harmonics of 440 Hz, heard as a *buzz* at the note's own *pitch*: the perceived height of a sound, set by its frequency.

## Summary

- A sound is air pressure that changes over time. In a computer it is a list of numbers between −1 and 1, the samples.
- Euterpe takes 48 000 samples per second. Between two samples nothing is stored; playback fills the gaps with the smooth wave that has nothing above half the sample rate.
- A sine at f and one at 48 000 − f have the same samples, upside down. So the highest frequency a sample rate can hold is half of it, the Nyquist frequency, 24 000 Hz here: more than two samples per cycle. A higher frequency folds back to a lower one.
- A sharp jump needs high frequencies. A saw's drop gives it harmonics far above its own frequency, and they fold back as tones that do not belong to the note. polyBLEP turns each drop into a two-sample slope, which weakens the folded tones without removing them.
- Each sample is rounded to a finite number of levels. Fewer bits mean a larger rounding error: a hiss when the error is small, a buzz when it is as large as the wave.

## Exercises

1. In the first example, change `440.0` to `220.0`, then to `880.0`, and listen. How does each compare with 440 Hz?
2. In the folding example, change `10_000` to `7_000` in both places and `range(1, 8)` to `range(1, 11)`, for the first ten harmonics of a 7 000 Hz saw. Ten is enough: the 10th has a tenth of the first one's amplitude, and those after it are quieter still. Which of the ten land below 7 000 Hz, the note itself? Then, in the sweep example, change `11_000 + 12_000` to `3_000 + 4_000`, a sweep from 1 000 to 7 000 Hz, and listen to the saw with `antialias=False`: do falling tones remain?
3. In the `BitCrush` example, change `bits=bits` to `bits=bits, downsample=8` and listen. `BitCrush` now keeps every 8th sample and repeats it for the next 7, so only 6 000 different values remain each second: in effect a sample rate of 6 000 Hz, with a Nyquist frequency of 3 000 Hz. What happens to the sine's note? Then replace `Sine` with `Saw`, in the import line too. The saw's 7th harmonic, 3 080 Hz, is now above the Nyquist frequency: where does it land? Compute `fold(3_080, rate=6_000)` with the function from the folding example, then do the same for the 13th harmonic, 5 720 Hz. Are the results multiples of 440 Hz?

### Answers

1. 220 Hz sounds lower and 880 Hz higher, and both sound like the same note as 440 Hz: the A one octave down and one octave up. Chapter 2 calls a doubling of the frequency an octave.
2. Harmonic 6 lands at 6 000 Hz and harmonic 7 at 1 000 Hz. The others land at 7 000, 14 000, 21 000, 20 000, 13 000, 8 000, 15 000 and 22 000 Hz. In the narrower sweep the falling tones remain, fainter: at every frequency of the sweep some harmonics lie above 24 000 Hz, and the lower the note, the higher the number k of the first one that folds, so its amplitude 1/k is smaller.
3. The sine keeps its note: 440 Hz is below 3 000 Hz, so nothing folds, and the held steps add a faint high whine. 3 080 Hz lands at 2 920 Hz and 5 720 Hz at 280 Hz. Neither is a multiple of 440 Hz (2 920 / 440 is about 6.6), which is why the crushed saw sounds out of tune with itself.

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
