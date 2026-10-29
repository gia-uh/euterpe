# Envelopes

Every sound in chapters 1 to 3 had the same level from its first sample to its last. Real notes do not. A piano note jumps to full level when the hammer strikes and then fades, whether or not the key is held. An organ note holds its level for as long as the key is down and stops when it is released. A violin note can swell in slowly. How the level of a note changes over time is called its *envelope*. This chapter builds envelopes, hears what each part of one does, and then uses an envelope to move other parameters, such as pitch. This is where it ends up:

```python {run echo=false}
# The teaser: the start of the finale, built by the code of this chapter's named blocks, which it
# reads from this file so the two never differ.
import re
from pathlib import Path

from euterpe.view import listen

text = Path("chapters/04-envelopes.md").read_text()
scope = {}
for name in ("kick", "floor", "pump", "finale"):
    code = re.search(r"```python \{[^}\n]*name=" + name + r"\b[^}\n]*\}\n(.*?)\n```", text, re.S).group(1)
    exec("\n".join(line for line in code.split("\n") if ".take(" not in line), scope)  # definitions only
listen(scope["song"], 8.0, "The first 8 s of the chapter's finale")
```

A dance groove: a kick drum on every beat, chords that duck out of its way, a bass and a hi-hat between the kicks. Every part is a plain wave from chapters 1 to 3; what makes each one a drum, a pluck or a pad is its envelope.

## A hard start clicks

A sound that starts at full level on its first sample jumps from silence to its first value. Chapter 3 showed what a jump does to a spectrum: the saw jumps once per cycle, and that jump gives it harmonics at every multiple of its frequency. A single jump at the start of a note is no different. It contains energy at every frequency, and the ear hears it as a click.

To make the jump as large as possible, the next sine starts at phase 0.25, a quarter of a cycle, where it is at its peak. It is switched on at 0.25 s and off at 0.75 s: 440 × 0.25 = 110 whole cycles and 440 × 0.75 = 330, so at both jumps the sine is back at its peak. Its level comes from `Segments(points)`, Euterpe's simplest envelope. `points` is a list of `(time, level)` pairs, in seconds; `Segments` draws a straight line from each point to the next, holds the first level before the first point and holds the last level after the last one. Two points at the same time make a jump: before that instant the level is the first point's, and from that sample on it is the second's.

The first sound is silent until 0.25 s, jumps to full level, and jumps back to silence at 0.75 s. The second takes 10 ms to rise and 10 ms to fall.

```python {run}
from euterpe.sound import Segments, Sine
from euterpe.view import listen

hard = Sine(440.0, phase=0.25) * Segments([(0.25, 0), (0.25, 1), (0.75, 1), (0.75, 0)]) * 0.5
soft = Sine(440.0, phase=0.25) * Segments([(0.25, 0), (0.26, 1), (0.74, 1), (0.75, 0)]) * 0.5
display(listen(hard, 1.0, "A sine switched on and off at its peak"))
listen(soft, 1.0, "The same sine with a 10 ms rise and fall")
```

Listen to the start and the end of each. The first one clicks twice, once at each jump. The second has the same tone and no clicks, although 10 ms is too short to hear as a fade.

`render`, `take` and `listen` reset a unit and pull it from its start each time, so the next block can render `hard` and `soft` again. The Fourier transform of chapter 3 measures the difference between them. A sine at 440 Hz should have no energy far from 440 Hz, so this block prints how much of each sound's energy lies above 1 000 Hz, in decibels relative to the total. With one second of sound, `energy[f]` is the energy at f Hz, and `energy[1000:]` is everything from 1 000 Hz up.

```python {run continue output=code}
import numpy as np

from euterpe.sound import render

for unit in (hard, soft):
    x = render(unit, 1.0)
    energy = np.abs(np.fft.rfft(x)) ** 2
    print(round(10 * np.log10(energy[1000:].sum() / energy.sum()), 1), "dB above 1 kHz")
```

With the jumps, −33 dB of the energy lies above 1 kHz: one part in 2 000, which the ear hears clearly as a click because it arrives all at once. With 10 ms ramps it is −69 dB, one part in eight million. The plot shows where that energy goes: the jump spreads the line at 440 Hz into a skirt that reaches every frequency, and the ramp keeps it close.

```python {run continue echo=false}
from euterpe.view import row, spectrum, waveform

sounds, names = (hard.take(1.0), soft.take(1.0)), ["jump", "10 ms ramp"]
row(
    waveform(*sounds, span=(0.245, 0.265), labels=names),
    spectrum(*sounds, upto=4000, labels=names),
    caption="Left: 20 ms around the start of each sound. Right: their spectra up to 4 kHz",
)
```

The rule this gives is that every note needs a beginning and an end that take some time. A few milliseconds remove the click; longer times change the character of the note, as the rest of this chapter shows.

## ADSR

Most synthesizers shape a note with four numbers, named after the four stages of the envelope they make: *attack*, *decay*, *sustain* and *release*, or ADSR.

- Attack: the time, in seconds, to rise from 0 to full level, 1, when the key goes down.
- Decay: the time to fall from 1 to the sustain level.
- Sustain: the level, from 0 to 1, held while the key stays down. Sustain is a level, not a time.
- Release: the time to fall from the current level to 0 once the key comes up.

The envelope cannot know by itself how long the key is held, so `ADSR` takes a fifth number, `gate`: the time in seconds at which the key comes up. The name comes from synthesizer hardware, where the *gate* is the signal that is on while a key is down. A sixth number, `curve`, bends the stages; the section on curves below explains it. Every number has a default: `ADSR()` is the same as `ADSR(attack=0.01, decay=0.1, sustain=0.7, release=0.3, gate=1.0, curve=0.0)`, a note held for one second.

```python {run echo=false}
from euterpe.sound import ADSR

ADSR(attack=0.1, decay=0.2, sustain=0.6, release=0.4, gate=0.7).take(1.3).waveform(
    marks=[(0.1, "decay"), (0.3, "sustain"), (0.7, "gate ends")],
    caption="ADSR with attack 0.1 s, decay 0.2 s, sustain 0.6, release 0.4 s and the gate ending at 0.7 s",
)
```

The level rises to 1 at 0.1 s, falls to 0.6 at 0.3 s and holds it until the gate ends at 0.7 s, then reaches 0 at 1.1 s. If the gate ends before the decay or even the attack has finished, the release starts from the level reached at that moment: a note shorter than its attack never reaches full level.

An envelope is a unit like any other, so it is applied the way chapter 2 applied a gain: `Saw(220.0) * ADSR(...)` multiplies every sample of the saw by the envelope's value at that sample.

### Percussive and sustained

Instruments fall into two groups by their envelope.

In a *percussive* instrument a single strike or pluck puts energy in, and the sound then dies away whatever the player does: piano, guitar, harp, drums, bells. Its envelope has a short attack, a long decay and a sustain of 0. In the examples below the gate ends after the decay is over, so the release has nothing left to do. In a *sustained* instrument the player feeds energy in for as long as the note lasts, with a bow, breath or an electric motor: violin, flute, organ. Its envelope has a sustain level above 0 and holds it until the gate ends.

The same saw at 220 Hz sounds like four different instruments under four envelopes. A short attack (2 ms) starts a note with a firm edge, a long one (0.6 s) swells in; a short decay to sustain 0 is a tap, a long one a pluck; a sustain of 1 holds the note like an organ; a long release lets it ring on after the key comes up.

```python {run}
from euterpe.sound import ADSR, Saw

shapes = {
    "a pluck": ADSR(attack=0.002, decay=0.8, sustain=0.0, release=0.0, gate=1.5, curve=0.8),
    "a short tap": ADSR(attack=0.001, decay=0.12, sustain=0.0, release=0.0, gate=1.5, curve=0.8),
    "an organ": ADSR(attack=0.005, decay=0.0, sustain=1.0, release=0.03, gate=1.2),
    "a bowed swell": ADSR(attack=0.6, decay=0.3, sustain=0.7, release=0.6, gate=1.2, curve=0.5),
}
for name, env in shapes.items():
    display((Saw(220.0) * env * 0.3).take(2.0, f"Saw at 220 Hz, {name}"))
```

The pluck and the tap are percussive; they differ only in their decay, 0.8 s against 0.12 s. The organ and the swell are sustained; they differ in their attack and release. Chapter 3 said timbre is the spectrum of a steady tone. A note is not steady, and the envelope is part of what tells instruments apart: the four notes above share one saw, so one spectrum, and still sound like four instruments.

The pluck still does not sound much like a guitar. In a real string the high harmonics die faster than the low ones, so the tone grows darker as it fades, while here every harmonic fades together. Changing the spectrum over time takes a filter, the subject of chapter 5.

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

The ear hears loudness in ratios, as chapter 2 showed: each halving of the amplitude is the same step, −6 dB. A straight-line fade does not halve at an even pace. The `curve` parameter bends each stage to fix that.

What `curve` computes: a stage that goes from level A to level B in T seconds is, after a fraction p = t / T of its time, at A + (B − A) × w(p), where w(p) = (1 − e^(−6 × curve × p)) / (1 − e^(−6 × curve)). At `curve=0` this is w(p) = p, a straight line. The division makes w(1) = 1 for every curve, so each stage ends on its target on time. `curve` goes from −1 to 1. A positive curve moves fast at first and slows as it nears its target, the shape of an exponential: the attack jumps up and creeps to 1, the decay and release fall fast and then level off near the bottom. A negative curve does the reverse. At `curve=1` a decay from 1 to 0 is close to e^(−6p), which loses the same 6 × 20 × log₁₀(e) = 52 dB over the stage at an even pace, until it bends down to reach exactly 0, −∞ dB, at its end.

Exponential decays are the ones nature makes. A struck string, a bell or a drum skin loses a fixed fraction of its energy in each cycle of its vibration, so its level falls by the same number of dB every second. Here are the same plucked notes with a straight and with a curved decay:

```python {run}
from euterpe.sound import ADSR, Triangle
from euterpe.view import listen

display(listen(Triangle(330.0) * ADSR(attack=0.002, decay=1.5, sustain=0.0, gate=2.0, curve=0.0) * 0.5, 2.0, "A 1.5 s decay, straight"))
listen(Triangle(330.0) * ADSR(attack=0.002, decay=1.5, sustain=0.0, gate=2.0, curve=1.0) * 0.5, 2.0, "A 1.5 s decay, curve 1")
```

The gate ends at 2.0 s, after the decay has reached 0, so both last exactly 1.5 s. The straight one stays loud and then stops; the curved one fades evenly and sounds like a struck object.

```python {run echo=false}
from euterpe.sound import ADSR
from euterpe.view import level, row, waveform

curves = (-0.5, 0.0, 0.5, 1.0)
envs = [ADSR(attack=0.0, decay=1.5, sustain=0.0, gate=2.0, curve=c).take(1.6) for c in curves]
names = [f"curve {c}" for c in curves]
row(
    waveform(*envs, labels=names), level(*envs, labels=names),
    caption="A 1.5 s decay with four curves, as a level (left) and in decibels (right)",
)
```

On the left, in linear level, curve 1 falls fast and levels off. On the right, in decibels, the same curve is close to a straight line until its last quarter second: the even fade the ear hears. The straight line, curve 0, holds near the top in decibels and then drops away.

## An envelope as a modulation source

An envelope is a unit, and chapter 2 showed that a unit can be the parameter of another unit: it is read again at every sample. So an envelope can move any parameter, not only the level.

The first example moves pitch. `ADSR(attack=0.0, decay=0.15, sustain=0.0, curve=0.7) * 200 + 50` starts at 250 and falls to 50 within 0.15 s. Used as the frequency of a sine, with a second, percussive envelope for the level, it makes a bass drum, or *kick*: the falling pitch is the thump. The function `kick` builds a new drum on each call. It must: a unit keeps its state (how far each envelope has gone), so one unit may appear only once in a graph, and `render` refuses a graph that uses one twice with a `ValueError`.

```python {run name=kick}
from euterpe.sound import ADSR, Sine


def kick(note=None):
    pitch = ADSR(attack=0.0, decay=0.15, sustain=0.0, gate=1.0, curve=0.7) * 200 + 50
    level = ADSR(attack=0.001, decay=0.5, sustain=0.0, release=0.0, gate=1.0, curve=0.6)
    return Sine(pitch) * level * 0.6


kick().take(1.0, "A bass drum: a sine falling from 250 to 50 Hz")
```

Music counts time in *beats*, and groups them in *bars*, most often four beats to a bar. Dance music puts the kick on every beat, which is called *four on the floor*. Chapter 2's `play` places a sound at each note's time: here every note is one kick, at 120 beats a minute, a beat every half second. `kick` takes the note, as `play` requires, and ignores it.

```python {run continue name=floor}
from euterpe.instruments import play

BEAT = 0.5  # seconds: 120 beats a minute


def kicks(bars):
    return play(kick, [(BEAT * b, 50.0, BEAT) for b in range(4 * bars)])


kicks(2).take(4.5, "Four on the floor: a kick on every beat for two bars")
```

`Segments` can draw any path, so it can move a pitch from one note to another. Here the frequency holds 220 Hz for 0.5 s, slides to 330 Hz over the next 0.5 s and holds there:

```python {run continue}
from euterpe.sound import ADSR, Saw, Segments

glide = Segments([(0.0, 220.0), (0.5, 220.0), (1.0, 330.0)])
display((Saw(glide) * ADSR(attack=0.01, gate=1.6, release=0.3) * 0.3).take(2.0, "A saw sliding from 220 to 330 Hz"))
```

An envelope can also move timbre. Chapter 3's exercise showed that the `duty` of a `Square` sets which harmonics it has. Here the duty starts at 0.5, a square with only odd harmonics, and an envelope moves it down to 0.1, a narrow pulse that lacks only every tenth harmonic, over the first second:

```python {run continue}
from euterpe.sound import ADSR, Square

duty = ADSR(attack=0.0, decay=1.0, sustain=0.0, gate=2.0) * 0.4 + 0.1
pulse = Square(110.0, duty=duty) * ADSR(gate=1.6, release=0.3) * 0.3
display(pulse.take(2.0, "A square whose duty moves from 0.5 to 0.1"))
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

Producers use a follower to make one sound make room for another, a technique called *ducking*, or *side-chaining*, because the level of one sound, fed in from the side, controls the gain of another. Below, four chords are multiplied by `1 - follower`: units can be subtracted, and negated with `-unit`, with numbers or units on either side, just as they can be added and multiplied. The follower listens to the kicks. A chord is three notes played together; `CHORDS` lists each as steps above A3, as in chapter 3's hymn: A minor (0, 3 and 7 steps, a *minor chord*, darker than the major one), F, C and G, the four chords of countless pop songs. Each note is two saws 0.3 % apart, which beat slowly and sound fuller, under an organ envelope that holds for the whole bar.

```python {run continue name=pump}
from euterpe.sound import EnvelopeFollower, Saw

CHORDS = [(0, 3, 7), (-4, 0, 3), (3, 7, 10), (-2, 2, 5)]  # A minor, F, C, G: steps above A3


def pad(n):
    return (Saw(n.freq) + Saw(n.freq * 1.003)) * ADSR(attack=0.01, sustain=1.0, release=0.1, gate=n.duration) * 0.08


def chords(bars):
    return play(pad, [(4 * BEAT * b, 220 * 2 ** (s / 12), 4 * BEAT) for b in range(bars) for s in CHORDS[b % 4]])


duck = 1 - EnvelopeFollower(kicks(4), attack=0.002, release=0.15)
display((chords(4) + kicks(4)).take(8.5, "Four chords over the kick"))
(chords(4) * duck + kicks(4)).take(8.5, "The same, the chords ducked by the kick")
```

How far do the chords drop? `duck` is a unit like any other, so it can be rendered on its own, and its smallest value is the lowest gain it gives them:

```python {run continue output=code}
import numpy as np

from euterpe.sound import render

lowest = render(duck, 8.0).min()
print(round(float(lowest), 3), round(float(20 * np.log10(lowest)), 1), "dB")
```

In the second player the chords drop to 0.4 of their level, about 8 dB, on every kick, and swell back up between kicks: they *pump*, the sound of French house and of much dance music since. Chapter 8's compressor measures level the same way, with an RMS detector instead of peaks.

## Putting it all together

Two more parts complete the groove, both on the *off-beats*, halfway between two kicks. The hi-hat is four inharmonic partials high up, as in chapter 3's metal bar, under a 50 ms percussive envelope: a short metallic tick. The bass is a saw on the root of each chord, an octave below it, plucked with a 0.3 s decay. Twelve bars, 24 seconds:

```python {run continue name=finale}
from euterpe.sound import Additive


def hat(n):
    env = ADSR(attack=0.001, decay=0.05, sustain=0.0, release=0.0, gate=0.1, curve=0.8)
    return Additive(3000.0, [(1, 1.0), (1.47, 0.8), (1.83, 0.7), (2.31, 0.6)]) * env * 0.2


def bass(n):
    return Saw(n.freq) * ADSR(attack=0.002, decay=0.3, sustain=0.0, gate=0.4, curve=0.8) * 0.25


BARS = 12
offbeats = [BEAT * b + BEAT / 2 for b in range(4 * BARS)]
hats = play(hat, [(t, 3000.0, 0.1) for t in offbeats])
line = play(bass, [(t, 110 * 2 ** (CHORDS[int(t // (4 * BEAT)) % 4][0] / 12), 0.4) for t in offbeats])
song = chords(BARS) * (1 - EnvelopeFollower(kicks(BARS), attack=0.002, release=0.15)) + kicks(BARS) + hats + line
song.take(24.5, "Four on the floor, pumping: kick, ducked chords, off-beat bass and hi-hat")
```

Every sound in it is an envelope on a wave: a pitch envelope makes the kick, a percussive one the hat and the bass, a held one the chords, and a follower makes them pump. Listen to the chords and the bass, though: they are raw saws, bright and buzzy from the first instant to the last. A real synthesizer bass grows darker as it fades, and its chords can be warm or thin; that takes removing harmonics while the note plays, with a filter, in chapter 5.

## Summary

- The envelope of a note is how its level changes over time. A jump in level contains every frequency and is heard as a click; a rise or fall of a few milliseconds removes it.
- `Segments(points)` is an envelope through `(time, level)` points, with straight lines between them. Two points at the same time make a jump to the second one's level.
- `render`, `take` and `listen` reset a unit and play it from its start; within one graph a unit may appear only once, so a function builds a fresh one for each use.
- `ADSR(attack, decay, sustain, release, gate, curve)`: rise to 1 in `attack` s, fall to `sustain` in `decay` s, hold until `gate` s, fall to 0 in `release` s from wherever the level is when the gate ends.
- `curve` bends each stage by w(p) = (1 − e^(−6 × curve × p)) / (1 − e^(−6 × curve)). 0 is a straight line; positive values approach an exponential, which loses the same number of dB every second, as struck and plucked objects do.
- Percussive instruments have a sustain of 0: they die away on their own. Sustained instruments hold a level until the gate ends. The envelope is part of an instrument's character, as its spectrum is.
- An envelope is a unit, so it can move any parameter: pitch (a drum), duty (timbre), or another sound's gain. Units can be added, subtracted, multiplied and negated.
- `EnvelopeFollower(src, attack, release)` measures the envelope of an existing sound; `1 - follower` ducks one sound under another. `lint_audio` warns with `A-TAIL` when a sound is still playing as its file ends, and with `A-DC` when its average is not 0.

## Exercises

1. In `kick`, change `* 200 + 50` to `* 0 + 50`, so that the pitch no longer falls. What is left of the drum?
2. In the block with four shapes, change the pluck's `curve=0.8` to `curve=-0.8`. How does the pluck sound now, and why?
3. In the first block of the chapter, change the soft sine's ramps from 10 ms to 1 ms: `(0.251, 1)` and `(0.749, 1)`. Then run the measuring block again. Is the click back?
4. In the finale, change the hat's `decay=0.05` to `decay=0.4`, and its `gate=0.1` to `gate=0.5`. What does it become?

### Answers

1. A low sine at 50 Hz that fades: a dull hum, with little of a strike in it. The fast fall of pitch at the start is what gives a bass drum its attack; the ear hears the quick sweep from 250 Hz as the impact.
2. The decay starts slowly and hurries at the end, so the note stays loud for most of its 0.8 s and then collapses, as if muted by a hand. No struck object does that, so it no longer sounds plucked.
3. The share of energy above 1 kHz rises to −48 dB, between the jump's −33 dB and the 10 ms ramp's −69 dB. A faint tick may be audible at the start and the end; a 1 ms ramp is 48 samples, short enough to keep some of the jump's high frequencies.
4. The same partials ring long enough to be heard as several pitches at once, like chapter 3's bar: an open hi-hat, or a small bell, washing over the groove. Only the envelope changed. A real hi-hat is made mostly of noise, which chapter 6 adds.

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
