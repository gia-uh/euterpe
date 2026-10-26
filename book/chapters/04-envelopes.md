# Envelopes

Every sound in chapters 1 to 3 had the same level from its first sample to its last. Real notes do not. A piano note jumps to full level when the hammer strikes and then fades, whether or not the key is held. An organ note holds its level for as long as the key is down and stops when it is released. A violin note can swell in slowly. How the level of a note changes over time is called its *envelope*. This chapter builds envelopes, hears what each part of one does, and then uses an envelope to move other parameters, such as pitch.

## A hard start clicks

A sound that starts at full level on its first sample jumps from silence to its first value. Chapter 3 showed what a jump does to a spectrum: the saw jumps once per cycle, and that jump gives it harmonics at every multiple of its frequency. A single jump at the start of a note is no different. It contains energy at every frequency, and the ear hears it as a click.

To make the jump as large as possible, the next sine starts at phase 0.25, a quarter of a cycle, where it is at its peak. It is switched on at 0.25 s and off at 0.75 s: 440 × 0.25 = 110 whole cycles and 440 × 0.75 = 330, so at both jumps the sine is back at its peak. Its level comes from `Segments(points)`, Euterpe's simplest envelope. `points` is a list of `(time, level)` pairs, in seconds; `Segments` draws a straight line from each point to the next, holds the first level before the first point and holds the last level after the last one. Two points at the same time make a jump: before that instant the level is the first point's, and from that sample on it is the second's.

The first sound is silent until 0.25 s, jumps to full level, and jumps back to silence at 0.75 s. The second takes 10 ms to rise and 10 ms to fall.

```python {run}
from euterpe.book import listen
from euterpe.sound import Segments, Sine

hard = Sine(440.0, phase=0.25) * Segments([(0.25, 0), (0.25, 1), (0.75, 1), (0.75, 0)]) * 0.5
soft = Sine(440.0, phase=0.25) * Segments([(0.25, 0), (0.26, 1), (0.74, 1), (0.75, 0)]) * 0.5
listen(hard, 1.0, "A sine switched on and off at its peak")
listen(soft, 1.0, "The same sine with a 10 ms rise and fall")
```

Listen to the start and the end of each. The first one clicks twice, once at each jump. The second has the same tone and no clicks, although 10 ms is too short to hear as a fade.

The next block renders `hard` and `soft` again, after `listen` has already played them. That works because a unit keeps its state (here, how far `Segments` has gone through its points, and the sine's phase), and `render` and `listen` reset that state and pull the unit from its start each time. The same state is why one unit may appear only once inside one graph: each place that pulled from it would advance it, and each would get only part of its samples. `render` checks the graph and refuses such a unit with a `ValueError`:

```python {run continue output=code}
from euterpe.sound import ADSR, Saw, render

env = ADSR()
try:
    render(Saw(220.0) * env + Sine(440.0) * env, 1.0)
except ValueError as error:
    print(error)
```

The fix is the one the message gives: build a second `ADSR` with the same numbers for the second use.

The Fourier transform of chapter 3 measures the difference between `hard` and `soft`. A sine at 440 Hz should have no energy far from 440 Hz, so this block prints how much of each sound's energy lies above 1 000 Hz, in decibels relative to the total. With one second of sound, `energy[f]` is the energy at f Hz, and `energy[1000:]` is everything from 1 000 Hz up.

```python {run continue output=code}
import numpy as np

for unit in (hard, soft):
    x = render(unit, 1.0)
    energy = np.abs(np.fft.rfft(x)) ** 2
    print(round(10 * np.log10(energy[1000:].sum() / energy.sum()), 1), "dB above 1 kHz")
```

With the jumps, −33 dB of the energy lies above 1 kHz: one part in 2 000, which the ear hears clearly as a click because it arrives all at once. With 10 ms ramps it is −69 dB, one part in eight million. The plot shows where that energy goes: the jump spreads the line at 440 Hz into a skirt that reaches every frequency, and the ramp keeps it close.

```python {run continue echo=false}
import matplotlib.pyplot as plt

from euterpe.book import show
from euterpe.sound import RATE

fig, (left, right) = plt.subplots(1, 2, figsize=(8, 2.6))
for unit, name in ((hard, "jump"), (soft, "10 ms ramp")):
    x = render(unit, 1.0)
    i = np.arange(int(0.245 * RATE), int(0.265 * RATE))
    left.plot(i / RATE * 1000, x[i], linewidth=1, label=name)
    amp = np.abs(np.fft.rfft(x)) * 2 / len(x)
    right.plot(np.arange(len(amp)), 20 * np.log10(np.maximum(amp, 1e-7)), linewidth=0.8, label=name)
left.set_xlabel("time (ms)")
left.set_title("the start")
right.set_xlim(0, 4000)
right.set_ylim(-120, 0)
right.set_xlabel("frequency (Hz)")
right.set_ylabel("dB")
right.set_title("the spectrum")
right.legend(loc="upper right", fontsize=8)
show(fig, "Left: 20 ms around the start of each sound. Right: their spectra up to 4 kHz")
```

The rule this gives is that every note needs a beginning and an end that take some time. A few milliseconds remove the click; longer times change the character of the note, as the rest of this chapter shows.

## ADSR

Most synthesizers shape a note with four numbers, named after the four stages of the envelope they make: *attack*, *decay*, *sustain* and *release*, or ADSR.

- Attack: the time, in seconds, to rise from 0 to full level, 1, when the key goes down.
- Decay: the time to fall from 1 to the sustain level.
- Sustain: the level, from 0 to 1, held while the key stays down. Sustain is a level, not a time.
- Release: the time to fall from the current level to 0 once the key comes up.

The envelope cannot know by itself how long the key is held, so `ADSR` takes a fifth number, `gate`: the time in seconds at which the key comes up. The name comes from synthesizer hardware, where the *gate* is the signal that is on while a key is down. A sixth number, `curve`, bends the stages; the section on curves below explains it. Every number has a default: `ADSR()` is the same as `ADSR(attack=0.01, decay=0.1, sustain=0.7, release=0.3, gate=1.0, curve=0.0)`, a note held for one second.

```python {run output=code}
from euterpe.sound import ADSR, RATE, render

env = render(ADSR(attack=0.1, decay=0.2, sustain=0.6, release=0.4, gate=0.7), 1.2)
for t in (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.1):
    print(t, "s:", round(float(env[int(t * RATE)]), 3))
```

The level rises to 0.5 halfway through the attack, reaches 1 at 0.1 s, falls to 0.8 halfway through the decay and reaches 0.6 at 0.3 s. It holds 0.6 until the gate ends at 0.7 s, then falls to 0.3 halfway through the release, and reaches 0 at 1.1 s.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import ADSR, RATE, render

env = render(ADSR(attack=0.1, decay=0.2, sustain=0.6, release=0.4, gate=0.7), 1.3)
t = np.arange(len(env)) / RATE
fig, ax = plt.subplots(figsize=(7, 2.6))
ax.plot(t, env, linewidth=1.5)
for x0, x1, name in ((0, 0.1, "A"), (0.1, 0.3, "D"), (0.3, 0.7, "S"), (0.7, 1.1, "R")):
    ax.axvspan(x0, x1, alpha=0.08 if name in "AS" else 0.16, color="grey")
    ax.text((x0 + x1) / 2, 1.05, name, ha="center")
ax.axvline(0.7, color="grey", linestyle="--", linewidth=0.8)
ax.text(0.71, 0.1, "gate ends", fontsize=8)
ax.set_ylim(0, 1.15)
ax.set_xlabel("time (s)")
ax.set_ylabel("level")
show(fig, "ADSR with attack 0.1 s, decay 0.2 s, sustain 0.6, release 0.4 s and the gate ending at 0.7 s")
```

An envelope is a unit like any other, so it is applied the way chapter 2 applied a gain: `Saw(220.0) * ADSR(...)` multiplies every sample of the saw by the envelope's value at that sample.

### Each stage alone

Each pair below changes one stage and keeps the others short, on a saw at 220 Hz. A saw has many harmonics, so changes in its level are easy to hear.

The attack first: 2 ms, and then 0.8 s.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Saw

listen(Saw(220.0) * ADSR(attack=0.002, decay=0.0, sustain=1.0, release=0.05, gate=1.2) * 0.3, 1.5, "Attack 2 ms")
listen(Saw(220.0) * ADSR(attack=0.8, decay=0.0, sustain=1.0, release=0.05, gate=1.2) * 0.3, 1.5, "Attack 0.8 s")
```

The short attack starts the note at once, with a firm edge but no click: 2 ms is 96 samples, enough to round off the jump. The long attack swells in, and the start of the note is hard to place in time. In fast music, with notes 0.1 s apart, an attack of 0.8 s would let each note reach only an eighth of its level before the next one starts, and the notes would blur together.

Then the decay and the sustain. Both notes rise in 5 ms and fall for 0.6 s; the first falls to a sustain level of 0.8, the second to 0.1.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Saw

listen(Saw(220.0) * ADSR(attack=0.005, decay=0.6, sustain=0.8, release=0.05, gate=1.4) * 0.3, 1.5, "Decay 0.6 s to sustain 0.8")
listen(Saw(220.0) * ADSR(attack=0.005, decay=0.6, sustain=0.1, release=0.05, gate=1.4) * 0.3, 1.5, "Decay 0.6 s to sustain 0.1")
```

With sustain 0.8 the decay is a small dip after the start; the note sounds held. With sustain 0.1 the note has a loud start, an *accent*, and then a quiet tail that lasts as long as the key is down.

Last, the release. Both notes hold full level until the gate ends at 0.5 s; the first then stops in 5 ms, the second fades over 1 s.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Saw

listen(Saw(220.0) * ADSR(attack=0.005, decay=0.0, sustain=1.0, release=0.005, gate=0.5) * 0.3, 2.0, "Release 5 ms")
listen(Saw(220.0) * ADSR(attack=0.005, decay=0.0, sustain=1.0, release=1.0, gate=0.5) * 0.3, 2.0, "Release 1 s")
```

The short release ends the note the moment the key comes up. The long one lets the note ring on after it, the way a piano does with its sustain pedal down, or a voice in a large hall.

If the gate ends before the decay has finished, or even before the attack has, the release starts from the level the envelope has reached at that moment, not from the sustain level. A note shorter than its attack never reaches full level:

```python {run output=code}
from euterpe.sound import ADSR, RATE, render

env = render(ADSR(attack=0.2, decay=0.1, sustain=0.5, release=0.1, gate=0.1), 0.3)
print(env.max(), env[int(0.15 * RATE)], env[int(0.25 * RATE)])
```

The attack would take 0.2 s, but the gate ends at 0.1 s, halfway, so the level peaks at 0.5, falls to 0.25 halfway through the release, and is 0 at 0.25 s.

### The release and the A-TAIL warning

A sound whose file ends while it is still playing has, in effect, a release of zero: the player that reaches the end of the file jumps to silence. Chapter 2's `lint_audio` warns about that with the rule `A-TAIL`, which looks at the last 50 ms of the audio. This block lints a saw with no envelope and the same saw with a release that ends inside the file:

```python {run output=code}
from euterpe.lint import lint_audio
from euterpe.sound import ADSR, Saw, render

for unit in (Saw(220.0) * 0.3, Saw(220.0) * ADSR(gate=0.6, release=0.3) * 0.3):
    report = lint_audio(render(unit, 1.0))
    print([f"{f.rule}: {f.message}" for f in report.findings if f.severity == "warn"])
```

The first ends at full level, 10.5 dB below full scale, and gets the warning. The second has finished its release at 0.9 s, so its last 50 ms are silent and the list is empty. Every example in this book from here on ends with a release inside the file.

## Curves

The ear hears loudness in ratios, as chapter 2 showed: each halving of the amplitude is the same step, −6 dB. A straight-line fade does not halve at an even pace. This block prints, in dB, a decay from 1 to 0 over 2 s every quarter second, first with a straight line, then with the `curve` parameter at 0.5 and at 1.

```python {run output=code}
import numpy as np

from euterpe.sound import ADSR, RATE, render

for curve in (0.0, 0.5, 1.0):
    env = render(ADSR(attack=0.0, decay=2.0, sustain=0.0, gate=3.0, curve=curve), 2.0)
    print(curve, [round(float(20 * np.log10(env[int(t * RATE)])), 1) for t in (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75)])
```

All the numbers here are in dB. The straight line, `curve=0`, loses 1.2 to 1.9 dB in each of its first four quarter seconds, then 2.5, 3.5 and 6.1: to the ear it holds, then drops away. With `curve=1` the level loses 6.5 to 7 dB in each quarter second up to 1.25 s, an even fade to the ear. Only near the end, 7.8 dB and then 9.8 dB per quarter second, does it fall faster, because it must reach a level of exactly 0, which is −∞ dB, at 2 s.

What `curve` computes: a stage that goes from level A to level B in T seconds is, after a fraction p = t / T of its time, at A + (B − A) × w(p), where w(p) = (1 − e^(−6 × curve × p)) / (1 − e^(−6 × curve)). At `curve=0` this is w(p) = p, a straight line. The division makes w(1) = 1 for every curve, so each stage ends on its target on time. `curve` goes from −1 to 1. Seen as a linear level, a positive curve moves fast at first and slows as it nears its target, the shape of an exponential: the attack jumps up and creeps to 1, the decay and release fall fast and then level off near the bottom. A negative curve does the reverse: each stage starts slowly and hurries at the end. In dB the same positive-curve decay is close to a straight line, as the table shows, and steepens only at its end. Both descriptions are of the same curve; the left plot below shows the linear view and the right one the dB view.

Exponential decays are the ones nature makes. A struck string, a bell or a drum skin loses a fixed fraction of its energy in each cycle of its vibration, so its level falls by the same number of dB every second. Here are the same plucked notes with a straight and with a curved decay:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Triangle

listen(Triangle(330.0) * ADSR(attack=0.002, decay=1.5, sustain=0.0, gate=2.0, curve=0.0) * 0.5, 2.0, "A 1.5 s decay, straight")
listen(Triangle(330.0) * ADSR(attack=0.002, decay=1.5, sustain=0.0, gate=2.0, curve=1.0) * 0.5, 2.0, "A 1.5 s decay, curve 1")
```

The gate ends at 2.0 s, after the decay has reached 0, so both last exactly 1.5 s. The straight one stays loud and then stops; the curved one fades evenly and sounds like a struck object.

```python {run echo=false}
import matplotlib.pyplot as plt
import numpy as np

from euterpe.book import show
from euterpe.sound import ADSR, RATE, render

fig, (lin, db) = plt.subplots(1, 2, figsize=(8, 2.6))
for curve in (-0.5, 0.0, 0.5, 1.0):
    env = render(ADSR(attack=0.0, decay=1.5, sustain=0.0, gate=2.0, curve=curve), 1.6)
    t = np.arange(len(env)) / RATE
    lin.plot(t, env, linewidth=1, label=f"curve {curve}")
    db.plot(t, 20 * np.log10(np.maximum(env, 1e-5)), linewidth=1)
lin.set_xlabel("time (s)")
lin.set_ylabel("level")
lin.legend(fontsize=8)
db.set_ylim(-60, 2)
db.set_xlabel("time (s)")
db.set_ylabel("dB")
show(fig, "A 1.5 s decay with four curves, as a level (left) and in decibels (right)")
```

On the left, in linear level, curve 1 falls fast and levels off. On the right, in decibels, the same curve is close to a straight line until its last quarter second: the even fade the ear hears.

## Percussive and sustained

Instruments fall into two groups by their envelope.

In a *percussive* instrument a single strike or pluck puts energy in, and the sound then dies away whatever the player does: piano, guitar, harp, drums, bells. Its envelope has a short attack, a long decay and a sustain of 0. In the examples below the gate ends after the decay is over, so the release has nothing left to do. In a *sustained* instrument the player feeds energy in for as long as the note lasts, with a bow, breath or an electric motor: violin, flute, organ. Its envelope has a sustain level above 0 and holds it until the gate ends.

The same saw at 220 Hz sounds like four different instruments under four envelopes:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Saw

shapes = {
    "a pluck": ADSR(attack=0.002, decay=0.8, sustain=0.0, release=0.0, gate=1.5, curve=0.8),
    "a short tap": ADSR(attack=0.001, decay=0.12, sustain=0.0, release=0.0, gate=1.5, curve=0.8),
    "an organ": ADSR(attack=0.005, decay=0.0, sustain=1.0, release=0.03, gate=1.2),
    "a bowed swell": ADSR(attack=0.6, decay=0.3, sustain=0.7, release=0.6, gate=1.2, curve=0.5),
}
for name, env in shapes.items():
    listen(Saw(220.0) * env * 0.3, 2.0, f"Saw at 220 Hz, {name}")
```

The pluck and the tap are percussive; they differ only in their decay, 0.8 s against 0.12 s. The organ and the swell are sustained; they differ in their attack and release. Chapter 3 said timbre is the spectrum of a steady tone. A note is not steady, and the envelope is part of what tells instruments apart: the four notes above share one saw, so one spectrum, and still sound like four instruments.

The pluck still does not sound much like a guitar. In a real string the high harmonics die faster than the low ones, so the tone grows darker as it fades, while here every harmonic fades together. Changing the spectrum over time takes a filter, the subject of chapter 5.

## An envelope as a modulation source

An envelope is a unit, and chapter 2 showed that a unit can be the parameter of another unit: it is read again at every sample. So an envelope can move any parameter, not only the level.

The first example moves pitch. `ADSR(attack=0.0, decay=0.15, sustain=0.0, curve=0.7) * 200 + 50` starts at 250 and falls to 50 within 0.15 s. Used as the frequency of a sine, with a second, percussive envelope for the level, it makes a bass drum: the falling pitch is the thump. The two envelopes are separate units, because one unit may appear only once in a graph.

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Sine

pitch = ADSR(attack=0.0, decay=0.15, sustain=0.0, gate=1.0, curve=0.7) * 200 + 50
level = ADSR(attack=0.001, decay=0.5, sustain=0.0, release=0.0, gate=1.0, curve=0.6)
listen(Sine(pitch) * level * 0.8, 1.0, "A bass drum: a sine falling from 250 to 50 Hz")
```

`Segments` can draw any path, so it can move a pitch from one note to another. Here the frequency holds 220 Hz for 0.5 s, slides to 330 Hz over the next 0.5 s and holds there:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Saw, Segments

glide = Segments([(0.0, 220.0), (0.5, 220.0), (1.0, 330.0)])
listen(Saw(glide) * ADSR(attack=0.01, gate=1.6, release=0.3) * 0.3, 2.0, "A saw sliding from 220 to 330 Hz")
```

An envelope can also move timbre. Chapter 3's exercise showed that the `duty` of a `Square` sets which harmonics it has. Here the duty starts at 0.5, a square with only odd harmonics, and an envelope moves it down to 0.1, a narrow pulse that lacks only every tenth harmonic, over the first second:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, Square

duty = ADSR(attack=0.0, decay=1.0, sustain=0.0, gate=2.0) * 0.4 + 0.1
pulse = Square(110.0, duty=duty) * ADSR(gate=1.6, release=0.3) * 0.3
listen(pulse, 2.0, "A square whose duty moves from 0.5 to 0.1")
```

The pitch stays at 110 Hz while the tone changes from hollow to thin and nasal. A sound whose timbre moves over the note sounds less like a machine than one whose timbre stays fixed.

There is one side effect. A pulse spends more of each cycle at −1 than at +1, so its average over a cycle is not 0 but 2 × duty − 1. An average that is not 0 is called a *DC offset*: a constant added to the wave, a component at 0 Hz. `lint_audio` reports it with the rule `A-DC`:

```python {run continue output=code}
from euterpe.lint import lint_audio
from euterpe.sound import render

print([f.message for f in lint_audio(render(pulse, 2.0)).findings if f.rule == "A-DC"])
```

The ear does not hear a constant, but it shifts the whole wave up or down, so one side of it comes closer to ±1 and clips sooner. The distance between a sound's peak and full scale, 1, is called its *headroom*, and a DC offset uses some of it up without making the sound any louder. Chapter 5's filters remove it.

### Following an envelope

`EnvelopeFollower(src, attack=0.005, release=0.1)` works the other way round: it measures the envelope of a sound that already exists. Its output is the size of the source's peaks, updated at every sample. When the source gets louder, the output rises towards the new peaks with a time scale of `attack` seconds; when the source gets quieter, it falls with a time scale of `release` seconds. A *time scale* here is the time the output takes to cover about 63 % (1 − 1/e) of the way to a new, steady target, the way the voltage on a capacitor charging through a resistor (an RC circuit) does; after three time scales it has covered 95 %.

`note_env` below is a plain Python function that builds a new envelope each time it is called. The block needs the same envelope twice, once inside the followed sound and once to compare with, and one unit may appear only once, so it calls `note_env()` twice. The block follows a sine whose level comes from an ADSR, and prints the follower next to the ADSR itself:

```python {run output=code}
from euterpe.sound import ADSR, RATE, EnvelopeFollower, Sine, render

def note_env():
    return ADSR(attack=0.05, decay=0.3, sustain=0.4, release=0.3, gate=0.6)

followed = render(EnvelopeFollower(Sine(220.0) * note_env()), 1.0)
env = render(note_env(), 1.0)
for t in (0.1, 0.3, 0.5, 0.7, 0.8):
    print(t, "s:", round(float(followed[int(t * RATE)]), 3), round(float(env[int(t * RATE)]), 3))
```

The first column is the follower, the second the envelope. While the envelope rises, decays and holds (0.1 to 0.5 s), the follower stays within about 0.05 of it, reading a little low: 0.846 against 0.9, 0.497 against 0.5, 0.366 against 0.4. Once the gate ends at 0.6 s and the level falls fast, the follower lags behind it and reads high: 0.274 against 0.267 at 0.7 s, 0.177 against 0.133 at 0.8 s. A shorter release would keep up with the fall, but it would also start to follow each cycle of the sine.

Producers use a follower to make one sound make room for another, a technique called *ducking*, or *side-chaining*, because the level of one sound, fed in from the side, controls the gain of another. Below, a held organ chord of two saws is multiplied by `1 - follower`: units can be subtracted, and negated with `-unit`, with numbers or units on either side, just as they can be added and multiplied. The follower listens to a bass drum that strikes at 0.5 s. `Segments` places the drum at 0.5 s, since an `ADSR` always starts at 0:

```python {run}
from euterpe.book import listen
from euterpe.sound import ADSR, EnvelopeFollower, Saw, Segments, Sine

def drum():
    pitch = Segments([(0.5, 250.0), (0.6, 50.0)])
    level = Segments([(0.5, 0.0), (0.501, 1.0), (1.0, 0.0)])
    return Sine(pitch) * level * 0.6

def chord():
    return (Saw(220.0) + Saw(330.0)) * ADSR(gate=1.6, release=0.3) * 0.15

duck = 1 - EnvelopeFollower(drum(), attack=0.002, release=0.15)
listen(chord() + drum(), 2.0, "An organ chord and a drum")
listen(chord() * duck + drum(), 2.0, "The same, the chord ducked by the drum's envelope")
```

How far does the chord drop? `duck` is a unit like any other, so it can be rendered on its own, and its smallest value is the lowest gain it gives the chord:

```python {run continue output=code}
import numpy as np

from euterpe.sound import render

lowest = render(duck, 2.0).min()
print(round(float(lowest), 3), round(float(20 * np.log10(lowest)), 1), "dB")
```

In the second player the chord drops to 0.45 of its level, about 7 dB, when the drum strikes, and comes back as the drum fades, so the drum is heard more clearly at the same level. Chapter 7's compressor measures level the same way, with an RMS detector instead of peaks.

## Summary

- The envelope of a note is how its level changes over time. A jump in level contains every frequency and is heard as a click; a rise or fall of a few milliseconds removes it.
- `Segments(points)` is an envelope through `(time, level)` points, with straight lines between them. Two points at the same time make a jump to the second one's level.
- `render` and `listen` reset a unit and play it from its start; within one graph a unit may appear only once.
- `ADSR(attack, decay, sustain, release, gate, curve)`: rise to 1 in `attack` s, fall to `sustain` in `decay` s, hold until `gate` s, fall to 0 in `release` s from wherever the level is when the gate ends.
- `curve` bends each stage by w(p) = (1 − e^(−6 × curve × p)) / (1 − e^(−6 × curve)). 0 is a straight line; positive values approach an exponential, which loses the same number of dB every second, as struck and plucked objects do.
- Percussive instruments have a sustain of 0: they die away on their own. Sustained instruments hold a level until the gate ends. The envelope is part of an instrument's character, as its spectrum is.
- An envelope is a unit, so it can move any parameter: pitch (a drum), duty (timbre), or another sound's gain. Units can be added, subtracted, multiplied and negated.
- `EnvelopeFollower(src, attack, release)` measures the envelope of an existing sound. `lint_audio` warns with `A-TAIL` when a sound is still playing as its file ends, and with `A-DC` when its average is not 0.

## Exercises

1. In the bass drum, change `* 200 + 50` to `* 0 + 50`, so that the pitch no longer falls. What is left of the drum?
2. In the block with four shapes, change the pluck's `curve=0.8` to `curve=-0.8`. How does the pluck sound now, and why?
3. In the first block of the chapter, change the soft sine's ramps from 10 ms to 1 ms: `(0.251, 1)` and `(0.749, 1)`. Then run the measuring block again. Is the click back?
4. Build a closed hi-hat from what chapters 3 and 4 taught: four inharmonic partials high up, as in chapter 3's metal bar, under a very short percussive envelope.

    ```python
    from euterpe.book import listen
    from euterpe.sound import ADSR, Additive

    partials = [(1, 1.0), (1.47, 0.8), (1.83, 0.7), (2.31, 0.6)]
    env = ADSR(attack=0.001, decay=0.05, sustain=0.0, release=0.0, gate=1.0, curve=0.8)
    listen(Additive(3000.0, partials) * env * 0.15, 0.5, "A closed hi-hat")
    ```

    Then change `decay=0.05` to `decay=0.4`. What does it become?

### Answers

1. A low sine at 50 Hz that fades: a dull hum, with little of a strike in it. The fast fall of pitch at the start is what gives a bass drum its attack; the ear hears the quick sweep from 250 Hz as the impact.
2. The decay starts slowly and hurries at the end, so the note stays loud for most of its 0.8 s and then collapses, as if muted by a hand. No struck object does that, so it no longer sounds plucked.
3. The share of energy above 1 kHz rises to −48 dB, between the jump's −33 dB and the 10 ms ramp's −69 dB. A faint tick may be audible at the start and the end; a 1 ms ramp is 48 samples, short enough to keep some of the jump's high frequencies.
4. With a 50 ms decay it is a short metallic tick, close to a closed hi-hat; a real one is made mostly of noise, which chapter 6 adds. With a 0.4 s decay the same partials ring long enough to be heard as several pitches at once, like chapter 3's bar: an open hi-hat, or a small bell. Only the envelope changed.

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
