# Filters and subtractive synthesis

Chapter 3 showed that the timbre of a steady tone is its spectrum: which harmonics it has and how loud each one is. Chapter 4 shaped the level of a note over time, but left its spectrum fixed, and ended on a pluck that did not sound like a string, because in a real string the high harmonics die sooner than the low ones. A *filter* is a unit that changes the level of each frequency in its source: some frequencies pass, others are made quieter. This chapter measures what filters do to a spectrum, uses them to carve tones out of noise and saws, moves them over time with envelopes and slow sines, and ends on a piece of acid house. This is where it ends up:

```python {run echo=false}
# The teaser: the start of the finale, built by the code of this chapter's named blocks, which it
# reads from this file so the two never differ.
import re
from pathlib import Path

from euterpe.view import listen

text = Path("chapters/05-filters.md").read_text()
scope = {}
for name in ("acid", "finale"):
    code = re.search(r"```python \{[^}\n]*name=" + name + r"\b[^}\n]*\}\n(.*?)\n```", text, re.S).group(1)
    exec("\n".join(line for line in code.split("\n") if ".take(" not in line), scope)  # definitions only
listen(scope["song"], 8.0, "The first 8 s of the chapter's finale")
```

A squelching bass line under a choir of robots singing "ah" and "oh", with a hiss of hi-hats: every part is a saw or noise from earlier chapters, carved by filters.

## What a filter does to a spectrum

The clearest source to filter is one that has every frequency in it. `WhiteNoise(seed)` is a stream of random samples, each one drawn between −1 and 1 independently of the others. Its spectrum is flat: on average, every band 100 Hz wide holds the same energy, from 0 Hz up to 24 000 Hz. `seed` picks the random numbers, so the same seed always gives the same noise. Chapter 6 has more kinds of noise; here white noise is just the test signal.

`LowPass(src, cutoff, q)` is the filter this chapter uses most. It keeps the frequencies below `cutoff`, in Hz, and makes those above it quieter. The next block plays one and a half seconds of noise, then the same noise through a low-pass at 500 Hz. Both have a 0.3 s release, so they end without a click.

```python {run}
from euterpe.sound import ADSR, LowPass, WhiteNoise

noise = WhiteNoise(seed=1) * ADSR(gate=1.5, release=0.3) * 0.3
low = LowPass(WhiteNoise(seed=1), cutoff=500.0) * ADSR(gate=1.5, release=0.3) * 1.5
display(noise.take(2.0, "White noise"))
display(low.take(2.0, "The same noise through a low-pass at 500 Hz"))
```

The first is a hiss, like air escaping. The second is a dull rumble, like wind heard through a closed window. Both are random; the filter only changed how much of each frequency there is. The second is multiplied by 1.5 instead of 0.3 because the filter removed most of the energy: nearly everything above 500 Hz, which in white noise is 23 500 / 24 000 = 98 % of it.

The plot shows the spectrum of both sounds, in dB, on a logarithmic frequency axis, so each octave takes the same width.

```python {run continue echo=false}
from euterpe.sound import LowPass, WhiteNoise
from euterpe.view import spectrum

spectrum(
    WhiteNoise(seed=1).take(1.0), LowPass(WhiteNoise(seed=1), cutoff=500.0).take(1.0),
    labels=["white noise", "low-pass at 500 Hz"], upto=24_000,
    caption="The spectrum of white noise, and of the same noise through a low-pass at 500 Hz, before the gains",
)
```

The noise is flat. The filtered noise keeps the same level up to about 500 Hz, then falls along a straight line: on a logarithmic axis, a fall of the same number of dB per octave.

### The response, one frequency at a time

The filters in this chapter are *linear*: a sine that goes in comes out as a sine at the same frequency, only louder or quieter, and shifted in time, and a sum of sines that goes in comes out as the sum of what each sine alone would give. A filter acts on each sine separately. Chapter 3 showed that every sound is a sum of sines, so knowing what a filter does to each single frequency tells what it does to any sound, and a filter can be measured one frequency at a time.


`gain_db(filter, freq)`, from `euterpe.book`, measures one frequency. `filter` is a function that takes a source and returns it filtered; `lambda s: LowPass(s, cutoff=1000.0)` is such a function, written in one line. `gain_db` sends a sine at `freq` through it, skips the first 0.1 s while the filter settles, and returns the *gain*, the peak level out over the peak level in, in dB.

To write down how, call the n-th input sample x[n], the n-th output sample y[n], and n the sample index, so y[n − 1] is the output one sample earlier. `OnePoleLowPass(src, cutoff)` is the simplest low-pass: y[n] = y[n − 1] + k × (x[n] − y[n − 1]). Each output moves a fraction k of the way from the previous output to the new input, with k = 1 − e^(−2π × cutoff / 48 000), so a higher cutoff follows the input more closely. The *order* of a filter is the number of past outputs it feeds back into each new one. `OnePoleLowPass` feeds back one, y[n − 1], so its order is 1. A *biquad* (short for *biquadratic*) feeds back two, y[n − 1] and y[n − 2]; it also uses the last two inputs, but its order is 2. Each order adds 6 dB per octave of slope: above the cutoff, each feedback stage halves the amplitude again for every doubling of the frequency, and halving the amplitude is −6 dB. So `OnePoleLowPass` should fall 6 dB per octave and `LowPass` 12. Here are both, at a cutoff of 1 000 Hz, measured at six frequencies:

```python {run output=code}
from euterpe.book import gain_db
from euterpe.sound import LowPass, OnePoleLowPass

for f in (250, 500, 1000, 2000, 4000, 8000):
    print(f"{f:5} Hz:  LowPass {gain_db(lambda s: LowPass(s, 1000.0), f):6} dB   OnePoleLowPass {gain_db(lambda s: OnePoleLowPass(s, 1000.0), f):6} dB")
```

The list of gains over every frequency is the filter's *frequency response*. Up to 500 Hz the sine passes almost unchanged. At the cutoff, 1 000 Hz, both are 3 dB down: the cutoff of a filter is, by convention, the frequency where half the power is gone. From there on, each octave up costs the biquad about 12 dB (−12.4, −24.6, −37.1) and the one-pole about 6 (−7.0, −12.2). A gentle slope sounds like a small change of colour; a steep one removes a part of the spectrum.

## Subtractive synthesis

A saw has every harmonic of its frequency, the n-th at 1/n of the first one's amplitude (chapter 3). A low-pass on a saw makes the harmonics above the cutoff quieter, so the cutoff sets how bright the tone is. Starting from a source rich in harmonics and taking some away with filters is called *subtractive synthesis*. It was the method of most analogue synthesizers of the 1970s, because oscillators that make saws and squares, and filters, were easy to build from a few transistors.

Here is a saw at 110 Hz unfiltered, then through a low-pass at 2 000, 600 and 200 Hz:

```python {run}
from euterpe.sound import ADSR, LowPass, Saw

display((Saw(110.0) * ADSR(gate=1.2, release=0.2) * 0.3).take(1.5, "A saw at 110 Hz"))
for cutoff in (2000.0, 600.0, 200.0):
    tone = LowPass(Saw(110.0), cutoff=cutoff) * ADSR(gate=1.2, release=0.2) * 0.3
    display(tone.take(1.5, f"The saw through a low-pass at {cutoff:.0f} Hz"))
```


The pitch never changes: the first harmonic, 110 Hz, is below every cutoff. The tone goes from buzzy, to warm, to a soft hum close to a sine. A `LowPass` with the default q has a simple formula for its gain at f Hz: 1 / √(1 + (f / cutoff)⁴). The fourth power is the second order: one octave above the cutoff, (f / cutoff)⁴ = 16, a gain of 1/4, −12 dB. Multiplied by the saw's 1/n, at 200 Hz it leaves the second harmonic about 10 dB below the first and the third about 18 dB below, where in the unfiltered saw they are 6 dB (1/2) and 9.5 dB (1/3) down. The plot shows each harmonic's level, measured.

```python {run echo=false}
from euterpe.sound import LowPass, Saw
from euterpe.view import spectrum

cutoffs = (2000.0, 600.0, 200.0)
spectrum(
    Saw(110.0).take(1.0), *[LowPass(Saw(110.0), cutoff=c).take(1.0) for c in cutoffs],
    f0=110.0, harmonics=50, upto=5500, labels=["no filter"] + [f"low-pass {c:.0f} Hz" for c in cutoffs],
    caption="The first 50 harmonics of a saw at 110 Hz, up to 5500 Hz, unfiltered and through three low-passes",
)
```

Each stem is one harmonic; the first 50, up to 5 500 Hz, are enough to show where each low-pass bends. Without a filter the harmonics fall by 6 dB per octave, the 1/n of the saw. Below each cutoff the filtered harmonics keep those levels; above it they fall 12 dB per octave faster.

## Resonance

The second parameter of `LowPass`, `q`, shapes the response near the cutoff. In a low-pass or high-pass, a sine exactly at the cutoff comes out q times as large as it went in. The default, q = 0.707, is 1/√2: the amplitude at which half the power is gone, because power goes as amplitude squared and (1/√2)² = 1/2. So the 3 dB down at the cutoff of the first measurement and the rule "the gain at the cutoff is q" are the same fact. A larger q makes a peak at the cutoff, 20 × log10(q) dB high: frequencies near it come out louder than they went in. The filter is said to *resonate*. The name q comes from electronics, where it is the *quality factor* of a resonant circuit.

At q = 4 a sine at the cutoff comes out 12 dB louder (20 × log10 4 = 12.0); at q = 12, 21.6 dB louder. Away from the cutoff q matters less, and the larger q is, the narrower the peak, as the response plot below shows. In a band-pass, q sets the width of the band instead: the band is cutoff / q Hz wide, measured between the two frequencies where the gain is 3 dB below the centre, so a band-pass at 1 000 Hz with q = 10 keeps a band 100 Hz wide.

On a saw, a resonant low-pass makes the harmonic nearest the cutoff stand out, and the ear hears it as a second, whistling pitch on top of the note:

```python {run}
from euterpe.sound import ADSR, LowPass, Saw

tones = {}
for q, gain in ((0.707, 0.3), (4.0, 0.23), (12.0, 0.17)):
    tones[q] = LowPass(Saw(110.0), cutoff=800.0, q=q) * ADSR(gate=1.2, release=0.2) * gain
    display(tones[q].take(1.5, f"A saw through a low-pass at 800 Hz, q {q}"))
```

The peak adds energy, so a larger q makes the note louder. The gains 0.3, 0.23 and 0.17 compensate, so that the three differ in tone and not in loudness.

At q = 12 the whistle is near 770 Hz, the seventh harmonic of 110 Hz, the one closest to the cutoff.

```python {run echo=false}
from euterpe.sound import LowPass, Sine
from euterpe.view import response

qs = (0.707, 4.0, 12.0)
response(
    *[LowPass(Sine(1.0), cutoff=800.0, q=q) for q in qs], labels=[f"q {q}" for q in qs],
    caption="The response of a low-pass at 800 Hz with three values of q",
)
```

## The other biquads

`LowPass` is one of four biquads. Each one is the same structure with other numbers in it (its *coefficients*), taken from Robert Bristow-Johnson's *Audio EQ Cookbook*, the formulas most audio software uses for these filters.

- `LowPass` keeps what is below `cutoff`.
- `HighPass` keeps what is above it, and falls 12 dB per octave below it.
- `BandPass` keeps a band around `cutoff`, at 0 dB in its centre, and falls on both sides.
- `Notch` removes a narrow band around `cutoff` and keeps everything else.

Here are the four on the same noise, all at 1 000 Hz with q = 2, so the band-pass keeps, and the notch removes, a band about 500 Hz wide. Each has its own gain so that the four play at about the same loudness: the low-pass and the band-pass keep only a small part of the noise's energy, so they need more gain (0.8 and 1.4); the high-pass and the notch keep most of it, so they need less (0.2).

```python {run}
from euterpe.sound import ADSR, BandPass, HighPass, LowPass, Notch, WhiteNoise

tones = {}
for kind, gain in ((LowPass, 0.8), (HighPass, 0.2), (BandPass, 1.4), (Notch, 0.2)):
    name = kind.__name__
    tones[name] = kind(WhiteNoise(seed=1), cutoff=1000.0, q=2.0) * ADSR(gate=1.2, release=0.2) * gain
    display(tones[name].take(1.5, f"Noise through a {name} at 1000 Hz"))
```


The low-pass rumbles, the high-pass hisses, the band-pass is a noise with a vague pitch near 1 000 Hz, like breath through a tube. The notch sounds almost like the unfiltered noise: it removes a band 500 Hz wide out of 24 000 Hz, and the ear barely misses it. A notch is a repair tool more than a sound: it removes one bad frequency, such as a 50 Hz hum from the mains, and leaves the rest.

A high-pass also fixes the side effect chapter 4 found: a pulse whose duty moves has a DC offset, a component near 0 Hz. A high-pass's gain falls to exactly 0 at 0 Hz, so a constant offset is removed completely. Here the offset is not quite constant: the duty moves over one second, so the offset moves with it, slowly. Slow means close to 0 Hz, well below 20 Hz, about the lowest frequency the ear hears, so a high-pass at 20 Hz removes it too. A `OnePoleHighPass` has the gain 1 / √(1 + (cutoff / f)²) at f Hz, which is 0 at f = 0, 1/√2 (−3 dB) at the cutoff, and close to 1 above it: at 110 Hz, the note below, it takes away 0.14 dB, which no one can hear. The same pulse as in chapter 4, linted before and after the high-pass:

```python {run output=code}
from euterpe.lint import lint_audio
from euterpe.sound import ADSR, OnePoleHighPass, Square, render

def pulse():
    duty = ADSR(attack=0.0, decay=1.0, sustain=0.0, gate=2.0) * 0.4 + 0.1
    return Square(110.0, duty=duty) * ADSR(gate=1.6, release=0.3) * 0.3

for unit in (pulse(), OnePoleHighPass(pulse(), 20.0)):
    print([f.message for f in lint_audio(render(unit, 2.0)).findings if f.rule == "A-DC"])
```

The pulse alone has an offset of 0.105; after the high-pass, `lint_audio` finds none.

## A cutoff that moves

A filter's cutoff is a parameter like any other, so an envelope or a slow oscillator can move it, as chapter 4 moved pitch and duty. A biquad reads a moving cutoff or q once every 64 samples (1.3 ms) and recomputes its coefficients there; that is fast enough that no step can be heard. Outside 0 Hz to 24 000 Hz, or with q at or below 0, its feedback would grow without end, so the cutoff is clipped to between 1 Hz and 23 000 Hz and q to at least 0.01.

First an envelope. The cutoff starts at 200 Hz, jumps to 4 200 Hz in 5 ms, and falls back to 200 Hz in 0.4 s:

```python {run}
from euterpe.sound import ADSR, LowPass, Saw

sweep = ADSR(attack=0.005, decay=0.4, sustain=0.0, gate=1.2, curve=0.7) * 4000 + 200
tone = LowPass(Saw(110.0), cutoff=sweep, q=3.0) * ADSR(gate=1.2, release=0.2) * 0.25
display(tone.take(1.5, "A saw whose low-pass falls from 4200 to 200 Hz"))
```

The note starts bright and darkens within half a second, with a short "yow" as the resonant peak slides down through the harmonics. This is the effect chapter 4 was missing: the high harmonics die before the low ones, as in a plucked string.


Retrigger that sweep on every note of a fast phrase and it becomes the sound of *acid house*, the dance music of the late 1980s built on one small bass synthesizer with a resonant low-pass. Here a bar of four beats is split into sixteen steps, an eighth of a second each at 120 beats a minute, and `PATTERN` gives each step's note in semitones above A1, 55 Hz. Each note gets its own sweep from 2 750 Hz down to 250 Hz in 0.15 s, with q = 8:

```python {run name=acid}
from euterpe.instruments import play
from euterpe.sound import ADSR, LowPass, Saw

STEP = 0.125  # seconds: a sixteenth of a bar at 120 beats a minute
PATTERN = [0, 0, 12, 0, 0, 10, 0, 12, 0, 0, 7, 0, 3, 0, 12, 10]  # steps above A1, 55 Hz


def acid(n):
    cutoff = ADSR(attack=0.003, decay=0.15, sustain=0.0, gate=n.duration, curve=0.7) * 2500 + 250
    level = ADSR(attack=0.003, decay=0.1, sustain=0.6, release=0.03, gate=n.duration)
    return LowPass(Saw(n.freq), cutoff=cutoff, q=8.0) * level * 0.2


def line(bars):
    return play(acid, [(STEP * i, 55 * 2 ** (PATTERN[i % 16] / 12), STEP * 0.8) for i in range(16 * bars)])


line(2).take(4.2, "An acid line: the swept low-pass retriggered on every step")
```

The resonant peak "squelches" through the harmonics on every step. The line sits at 55 and 110 Hz, yet it is heard on small speakers that cannot play 55 Hz at all: the harmonics at 110, 165, 220 Hz and up are 55 Hz apart, and the ear infers the pitch from that spacing even when the first harmonic is missing. This is called the *missing fundamental*.

Then a slow sine. `Sine(1.5) * 700 + 1000` swings between 300 and 1 700 Hz, one and a half times a second. On a resonant low-pass, it gives the sound of a guitarist's *wah-wah* pedal, which moves a resonant filter with the foot:

```python {run continue}
from euterpe.sound import ADSR, LowPass, Saw, Sine
from euterpe.view import listen

wah = Sine(1.5) * 700 + 1000
tone = LowPass(Saw(110.0), cutoff=wah, q=6.0) * ADSR(gate=2.6, release=0.3) * 0.15
listen(tone, 3.0, "A wah: the cutoff swings between 300 and 1700 Hz")
```

A slow oscillator used to move a parameter is called an *LFO*, a low-frequency oscillator: low here means below about 20 Hz, too slow to hear as a pitch, so it is heard as movement.

```python {run continue echo=false}
tone.take(3.0).spectrogram(
    lo=55, hi=4000,
    caption="The wah over time: each horizontal line is a harmonic; the dark band is the moving peak",
)
```

The picture is a *spectrogram*: time runs left to right, frequency bottom to top, and darker ink is a higher level. Each horizontal line is one harmonic of 110 Hz. The dark band that rises and falls is the resonant peak, inking the harmonics it passes.

## Filters made of delays

A different family of filters is built from one delayed copy of the signal. `Comb(src, delay, feedback)` adds its own output back to itself `delay` seconds later, scaled by `feedback`: each output sample is y[n] = x[n] + feedback × y[n − D], where D is the delay in samples. A sine whose period fits a whole number of times into the delay comes back in step with itself, and each trip adds to it; a sine whose period puts it half a cycle out of step comes back and partly cancels. So the response has peaks at every multiple of 1 / delay Hz, evenly spaced like the teeth of a comb, and dips halfway between them. Each trip round the loop adds feedback times what the last trip added, so at a peak the sum is 1 + g + g² + … = 1 / (1 − g) times the input, for feedback g, and at a dip, where every other trip subtracts, 1 − g + g² − … = 1 / (1 + g). With feedback 0.9 the peaks are 1 / (1 − 0.9) = 10 times the input, 20 dB, and the dips 1 / 1.9 of it.

Evenly spaced peaks at multiples of one frequency are exactly the harmonics of chapter 3. So a comb on noise makes a pitched note out of a sound that has no pitch:

```python {run continue}
from euterpe.sound import ADSR, Comb, LowPass, WhiteNoise

def comb_note(feedback, gain):
    dark = LowPass(WhiteNoise(seed=1), cutoff=3000.0)
    return Comb(dark, delay=1 / 220, feedback=feedback) * ADSR(gate=1.5, release=0.3) * gain

display(comb_note(0.5, 0.5).take(2.0, "Noise through a comb tuned to 220 Hz, feedback 0.5"))
display(comb_note(0.98, 0.08).take(2.0, "The same comb, feedback 0.98"))
```

With feedback 0.5 the noise has a faint pitch in it. With 0.98 the peaks are 1 / 0.02 = 50 times the input, and narrow, and the noise turns into a buzzing note at 220 Hz. That is also why the second note needs a gain of 0.08 instead of 0.5: the comb makes it much louder. The low-pass before the comb removes the harsh high peaks. The delay is a whole number of samples: 48 000 / 220 = 218.2, rounded to 218, so the note is at 48 000 / 218 = 220.2 Hz. Chapter 7 builds a plucked string from this loop, with a filter inside it and a fractional delay that makes the pitch exact.

`Allpass(src, delay, gain)` is a comb with a second, forward path that cancels its peaks and dips: y[n] = −gain × x[n] + x[n − D] + gain × y[n − D]. Every frequency comes out at the level it went in.

The clearest way to see it is to send in a single sample of 1, an *impulse*, and read what comes out every D samples. `Segments` draws straight lines through `(time, level)` points, so a line from 1 at 0 s to 0 one sample later is an impulse. The delay of 3 ms is D = 144 samples:

```python {run continue output=code}
import numpy as np

from euterpe.sound import Allpass, Segments, render

impulse = Segments([(0.0, 1.0), (1 / 48_000, 0.0)])
y = render(Allpass(impulse, delay=0.003, gain=0.7), 0.2)
print([round(float(v), 3) for v in y[::144][:6]])
print("energy out:", round(float((y ** 2).sum()), 3))
```

The impulse comes out at once as −0.7 (the −gain × x[n] path), then as an echo of 1 − 0.7² = 0.51 after 3 ms, and each later echo is 0.7 times the one before. The energies add up to 0.49 + 0.51² × (1 + 0.49 + 0.49² + …) = 0.49 + 0.51 = 1, the energy of the impulse that went in; the sum printed is 1.0. The same holds at every frequency: `gain_db` reads 0 dB for this allpass at any frequency you try. What an allpass changes is time: the energy comes out spread over a dense ring of echoes, each frequency delayed by its own amount. Chapter 3 called this the phase of each component: the allpass changes only phases. On a steady tone the ear does not hear phase, so an allpass is almost inaudible; on a click it smears the attack into a short ring. The example below is four clicks a quarter second apart. Each is made with `Segments` from `(time, level)` points joined by straight lines, where two points at the same time make a jump: 3 ms at +0.5, then 3 ms at −0.5, so that its average is 0 and it has no DC offset. Chapter 8 chains allpasses to make reverb.

```python {run continue}
from euterpe.sound import Allpass, Segments

def clicks():
    points = []
    for t in (0.1, 0.35, 0.6, 0.85):
        points += [(t, 0.0), (t, 0.5), (t + 0.003, 0.5), (t + 0.003, -0.5), (t + 0.006, -0.5), (t + 0.006, 0.0)]
    return Segments(points)

display(clicks().take(1.2, "Four clicks"))
display(Allpass(clicks(), delay=0.003, gain=0.7).take(1.2, "The clicks through an allpass"))
```

## Formants and vowels

The human voice is a subtractive synthesizer. The vocal folds in the throat buzz, and their buzz has many harmonics, like a saw. The throat, mouth and lips above them form a tube whose shape boosts some bands of frequencies and weakens others. Those bands are the *formants*. Moving the tongue and lips changes the shape of the tube, so it moves the formants, and the ear tells the vowels apart by where the first two or three formants lie, whatever the pitch.

`Formant(src, vowel)` is three band-pass filters side by side, at the first three formants of an adult male voice for the vowels `"a"` (as in *father*), `"e"` (*bed*), `"i"` (*beet*), `"o"` (*bought*) and `"u"` (*boot*). The frequencies are rounded from the averages that Gordon Peterson and Harold Barney measured in 1952, in Hz:

| vowel | first | second | third |
|---|---|---|---|
| a | 730 | 1 090 | 2 440 |
| e | 530 | 1 840 | 2 480 |
| i | 270 | 2 290 | 3 010 |
| o | 570 | 840 | 2 410 |
| u | 300 | 870 | 2 240 |

Each band has q = 8, so it is a few hundred Hz wide at most, and the three are mixed at 1, 0.5 and 0.25, so the higher formants are 6 and 12 dB quieter. Everything outside the bands is cut, so `Formant` needs a source with many harmonics, a saw or noise, to have anything to shape. The same saw at 110 Hz through each of them:

```python {run continue}
from euterpe.sound import ADSR, Formant, Saw

for vowel in "aeiou":
    display((Formant(Saw(110.0), vowel) * ADSR(gate=0.8, release=0.15) * 1.2).take(1.0, f"A saw at 110 Hz through the vowel {vowel}"))
```

Listen to them in a row: a buzzing voice says "ah, eh, ee, aw, oo". The pitch is the same in all five; only the bands changed. "ee" has its first formant very low, at 270 Hz, and its second high, at 2 290 Hz; "oo" has both low, at 300 and 870 Hz, so it is the darkest.

## Putting it all together

Two more parts join the acid line. The choir is two saws 0.5 % apart, which drift in and out of step: two sines a little apart in frequency add when in step and cancel half a cycle later, so their sum rises and falls slowly. This slow rise and fall is called *beating*, and with every harmonic beating at its own rate the tone seems to move. The choir plays a chord per bar, A minor then F (chapter 4's chords), through `Formant`, singing "a" on one bar and "o" on the next. The hi-hats are white noise through a high-pass at 8 kHz, a 40 ms tick on every off-beat; each has its own seed, so no two are the same noise. Twelve bars, 24 seconds:

```python {run continue name=finale}
from euterpe.sound import Formant, HighPass, WhiteNoise

CHORDS = [(0, 3, 7), (-4, 0, 3)]  # A minor and F: steps above A3
VOWELS = "ao"


def choir(n):
    vowel = VOWELS[int(n.time // (16 * STEP)) % 2]
    return Formant(Saw(n.freq) + Saw(n.freq * 1.005), vowel) * ADSR(attack=0.3, sustain=1.0, release=0.4, gate=n.duration) * 0.25


def hat(n):
    env = ADSR(attack=0.001, decay=0.04, sustain=0.0, release=0.0, gate=0.05, curve=0.8)
    return HighPass(WhiteNoise(seed=round(n.time / STEP)), cutoff=8000.0) * env * 0.8


BARS = 12
voices = play(choir, [(16 * STEP * b, 220 * 2 ** (s / 12), 16 * STEP) for b in range(BARS) for s in CHORDS[b % 2]])
hats = play(hat, [(STEP * (4 * i + 2), 8000.0, 0.05) for i in range(4 * BARS)])
song = line(BARS) + voices + hats
song.take(24.5, "Acid line, robot choir and hi-hats: three filters at work")
```

Every number in `acid` is a knob on a synthesizer's front panel: the filter envelope's `decay` sets how long each squelch lasts, `q` how much it sings, `* 2500 + 250` the range it sweeps. But every source in this piece is a saw or white noise. Chapter 6 brings three new raw materials: tones made by moving one sine's frequency with another (FM), noises of other colours, and wavetables.

## Summary

- A filter changes the level of each frequency in its source. A linear filter acts on each sine separately, so it is described by its frequency response: its gain at each frequency. `gain_db(filter, freq)`, from `euterpe.book`, measures it at one frequency.
- `WhiteNoise(seed)` has a flat spectrum, every frequency at the same level on average; the same seed gives the same noise.
- The order of a filter is the number of past outputs it feeds back; each order adds 6 dB per octave of slope.
- `LowPass`, `HighPass`, `BandPass` and `Notch`, each `(src, cutoff, q)`, are second-order filters, biquads. The low-pass and high-pass are 3 dB down at `cutoff` and fall 12 dB per octave beyond it. `OnePoleLowPass(src, cutoff)` and `OnePoleHighPass(src, cutoff)` fall 6 dB per octave.
- `q` above 0.707 adds a resonant peak at the cutoff, 20 × log10(q) dB high. In a band-pass it sets the width, about cutoff / q Hz.
- Subtractive synthesis starts from a source with many harmonics (a saw, noise) and removes some with filters. The cutoff sets brightness.
- A cutoff can be moved by an envelope (a bright start that darkens, retriggered on each note for acid house) or an LFO (a wah). A biquad reads a moving cutoff or q once every 64 samples.
- `Comb(src, delay, feedback)` has peaks at every multiple of 1 / delay Hz, so it puts a pitch into noise. `Allpass(src, delay, gain)` keeps every level and changes only the timing.
- Vowels are formants, bands that the vocal tract boosts. `Formant(src, vowel)` puts the formants of five vowels on any source.
- A high-pass at 20 Hz removes a DC offset.

## Exercises

1. In `acid`, change the filter envelope's `sustain=0.0` to `sustain=1.0`. What happens to the line, and why?
2. In the wah, change `Sine(1.5)` to `Sine(6.0)`. What does the effect sound like now?
3. In the comb note, change `delay=1 / 220` to `delay=1 / 330`. What note do you hear, and how far is it from 330 Hz, in cents? (48 000 / 330 = 145.45 samples; from chapter 2, the distance from f1 to f2 is 1200 × log₂(f2 / f1) cents.)

### Answers

1. The cutoff stays at 2 750 Hz for every step, so there is no squelch: each note is equally bright and buzzy, and the line loses what made it acid. The sweep disappears because the decay now falls from 1 to 1.
2. The peak sweeps up and down six times a second instead of one and a half. It is too fast to hear as a pedal being rocked: pitch stays put while the brightness of the tone wobbles six times a second, a rapid warble rather than a wah.
3. A note near E4, 330 Hz. The delay rounds to 145 samples, so the note is at 48 000 / 145 = 331.0 Hz, 1.0 Hz sharp, 1200 × log₂(331.0 / 330) = 5 cents (a twentieth of a semitone): close, but not exact, which is why chapter 7 adds a fractional delay.

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
