# The electric guitar and its amp

This is where the chapter ends up:

```python {run echo=false}
# The teaser: the end of the finale, built by the code of this chapter's last section, which it
# reads from this file so the two never differ.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import RATE, render

text = Path("chapters/11-electric-guitar.md").read_text()
for name in ("riff", "band", "finale"):
    exec(re.search(r"```python \{[^}\n]*name=" + name + r"\b[^}\n]*\}\n(.*?)\n```", text, re.S).group(1))
x = render(song, length)
display(Clip(x[int(pass4 * RATE):], caption="In the Hall of the Mountain King, the last pass"))
```

Two distorted guitars, a bass and drums play Grieg's *In the Hall of the Mountain King*, faster and faster, and the last note is held by the amplifier until it turns into its octave. Every sound in it is a plucked string from chapter 10 followed by effects from Part I. By the end of the chapter each part of it is yours, and the last section builds the whole piece.

## A string with no body

An acoustic guitar's string is too thin to move much air; the wooden box does that, and colours the sound with its modes (chapter 10). An electric guitar is a solid plank of wood. Its strings move almost no air at all, and what we hear comes from a *pickup* under them, through an *amplifier* and a *speaker*. `ElectricGuitar` is built like `Guitar`, six steel strings plucked with a plectrum, but with no body at all, and strings that lose a little less on each trip (`Steel(damping=0.998)`, against 0.997), as the heavier strings of an electric do. With `pickup=None` it is the bare string:

```python {run}
from euterpe.instruments import ElectricGuitar, Guitar

acoustic, solid = Guitar(), ElectricGuitar(pickup=None)
display(acoustic.play(acoustic.pick(5, 0, 0.0, 2.0)).take(2.5, "Open A on the acoustic guitar"))
display(solid.play(solid.pick(5, 0, 0.0, 2.0)).take(2.5, "Open A on a solid body, straight off the string"))
```

Without the box the note is thinner, and it rings longer: no box drinks its energy, and its strings lose less. That bare, dry string is the raw material for the rest of the chapter.

## The pickup

A pickup is a magnet wrapped in a coil of wire. The steel string moving over it changes the magnetic field, and that induces a voltage in the coil. It hears the string at one point only. A harmonic with a *still point* there (chapter 7) does not move the field and is not heard, exactly as a pluck at a still point cannot start that harmonic (chapter 7). A pickup at a quarter of the string misses the 4th, 8th and 12th harmonics; one close to the bridge misses only harmonics far up.

The coil adds a second effect: it is a resonant lowpass, so the highs fall off above a few kHz with a small peak first. `Pickup(position, resonance, q)` is the two together. `Neck()` sits a quarter of the way along the open string, with its resonance at 2.5 kHz; `Bridge()` sits at 6 % with its resonance at 4.5 kHz. A fret shortens the string, so the same pickup sits at a larger fraction of it: the neck pickup reaches half the string at the 12th fret. `play` gives every note a string, as `Guitar` does (chapter 10), so the pickup always knows which one it hears.

Before comparing them, we need something to play. A *riff* is a short phrase a band repeats, and the one this chapter builds on is the theme of *In the Hall of the Mountain King* (Edvard Grieg, 1875). Its first eight bars, written as pitches and their lengths in beats. Their notes come from a scale built on B, so B is the note the tune comes home to. Tempo is counted in beats per minute (bpm): at 100 bpm a beat lasts 0.6 s, and `bars` turns a tempo into the start time of each bar.

```python {run continue name=riff}
from euterpe.instruments import Note
from euterpe.pitch import A3, B2, B3, C3, Cs3, D3, E3, F3, Fs3

THEME = [[B2, Cs3, D3, E3], [Fs3, D3, (Fs3, 2)], [F3, Cs3, (F3, 2)], [E3, C3, (E3, 2)],
         [B2, Cs3, D3, E3], [Fs3, D3, Fs3, B3], [A3, Fs3, D3, Fs3], [(A3, 4)]]


def bars(bpm, n, at=0.0):
    """(start, beat) for n bars of four beats from at; bpm is one tempo, or a list, one per bar."""
    out = []
    for i in range(n):
        beat = 60 / (bpm[i] if isinstance(bpm, list) else bpm)
        out.append((at, beat))
        at += 4 * beat
    return out


def riff(bpm, n=8, at=0.0, transpose=0):
    """(time, pitch, seconds, beats) for each note of the theme's first n bars."""
    events = []
    for bar, (t, beat) in zip(THEME, bars(bpm, n, at)):
        for note in bar:
            pitch, beats = note if isinstance(note, tuple) else (note, 1)
            events.append((t, pitch + transpose, beats * beat, beats))
            t += beats * beat
    return events


def notes(events, up=0, **kw):
    """A Note for each event, up semitones higher, held for 90 % of its length."""
    return [Note(t, p + up, d * 0.9, **kw) for t, p, d, _ in events]
```

A list of tempos, one per bar, will make the music speed up at the end. Here are the first four bars, an octave up, on each pickup:

```python {run continue}
from euterpe.instruments import Bridge, Neck

first = riff(100, 4)
for pickup, name in ((Neck(), "neck"), (Bridge(), "bridge")):
    guitar = ElectricGuitar(pickup=pickup)
    display(guitar.play(notes(first, up=12)).take(10.5, f"The riff's first bars, {name} pickup"))
```

The neck pickup is round and soft; the bridge pickup is thin and bright. On one open string, with the harmonics marked:

```python {run continue}
from euterpe.view import spectrum

neck, bridge = ElectricGuitar(pickup=Neck()), ElectricGuitar(pickup=Bridge())
spectrum(neck.play(neck.pick(5, 0, 0.0, 1.0)).take(1.0), bridge.play(bridge.pick(5, 0, 0.0, 1.0)).take(1.0),
         f0=110.0, harmonics=17, labels=["neck", "bridge"], caption="Open A through each pickup")
```

The neck's line drops into holes at 440, 880 and 1320 Hz, the 4th, 8th and 12th harmonics, and falls away above 2.5 kHz. The bridge's first hole is near 1850 Hz, between the 16th and 17th harmonics (1 / 0.06 ≈ 16.7), and its line keeps its highs.

## The amp

A guitar amplifier does two jobs. It makes the pickup's tiny voltage loud enough for a speaker, and, turned up, it *distorts*: its tubes cannot swing as far as the signal asks, and they bend the top of the wave over. Chapter 8 built that bend: `Saturator` is a tube-like curve, and its `bias` makes the two halves bend differently, which adds even harmonics. An amp is two steps: a highpass at 100 Hz, so the low strings do not push the curve harder than the high ones, then gain into the curve:

```python {run continue}
from euterpe.sound import HighPass, Saturator

guitar = ElectricGuitar()
by_hand = Saturator(HighPass(guitar.play(notes(first, up=12)), 100.0), drive=25.0, bias=0.1)
display(by_hand.take(10.5, "The riff into a highpass and a Saturator at drive 25"))
```

That is distortion, and it is ugly: a hiss rides on every note. The curve adds harmonics far above anything a guitar plays, up to 20 kHz. We fix that in the next section.

First, `Amp(src, gain, bass, mid, treble, level)` packages this chain. `gain` is the curve's drive: low gain is *clean*, and around 8 the louder notes start to break up, which players call *crunch*. After the curve come three tone knobs, each in dB, 0 leaving the sound alone: `bass` lifts or cuts everything below 200 Hz, `treble` everything above 3 kHz, and `mid` a bell around 800 Hz. They are three new filters, `LowShelf`, `HighShelf` and `Peak`, each a biquad of chapter 5 that changes one region and leaves the rest at 0 dB. Cutting the mids, *scooping* them, is the hollow sound of metal rhythm guitar:

```python {run continue}
from euterpe.sound import Amp

for gain, mid, name in ((1.0, 0.0, "clean"), (8.0, 0.0, "crunch"), (8.0, -9.0, "crunch, mids scooped")):
    amp = Amp(ElectricGuitar().play(notes(first, up=12)), gain=gain, mid=mid)
    display(amp.take(10.5, f"The riff, amp at gain {gain:g}, mid {mid:g} dB: {name}"))
```

## The cabinet

A guitar speaker is not a hi-fi speaker. It sits in a wooden box, the *cabinet*, and its paper cone cannot follow fast vibrations: above about 5 kHz it stops moving at all. That is not a flaw. Distortion only sounds like a guitar through a speaker that throws its fizz away. `Cabinet(src, size)` is that speaker: a highpass at 80 Hz, a resonance of the box at 110 Hz, a lift of the cone at 2.5 kHz, and two lowpasses at 5 kHz, 24 dB per octave above it. `size` moves the low end down for a bigger box.

```python {run continue}
from euterpe.sound import Cabinet

display(Cabinet(Amp(ElectricGuitar().play(notes(first, up=12)), gain=25.0)).take(10.5, "The riff, amp at gain 25, through the cabinet"))
```

The same drive as the ugly version above, and now it is the sound of a rock guitar. Its response is a highpass and lowpasses from chapter 5 with two `Peak` bells; a filter's `response` feeds it its own test signal, so `Const(0.0)`, a silent source, only fills the slot. A box twice the size moves the low end an octave down:

```python {run continue}
from euterpe.sound.core import Const
from euterpe.view import response

response(Cabinet(Const(0.0)), Cabinet(Const(0.0), size=2.0), labels=["size 1", "size 2"],
         caption="A guitar cabinet: 80 Hz to 5 kHz, with the box and the cone")
```

## Why fifths

Guitarists name a chord of a root and its fifth, with the octave on top, by the root and a 5: A5 here is a chord, not the pitch A5 of chapter 2. They play these *power chords* through distortion, almost never a full major chord, which adds a *major third*, 4 semitones above the root. Listen to both through the same amp:

```python {run continue}
from euterpe.pitch import A2, Cs3, E3

chords = {"A5, a power chord": [A2, E3, A2 + 12], "A major": [A2, Cs3, E3]}
for name, pitches in chords.items():
    guitar = ElectricGuitar()
    display(Cabinet(Amp(guitar.play(guitar.strum(pitches, 0.0, 2.0)), gain=25.0)).take(2.5, f"{name}, gain 25"))
```

The power chord is one solid tone; the major chord growls and wobbles. The reason is in the curve. Through it, two notes played together give more than their harmonics: they also give tones at the sums and differences of their frequencies (chapter 8 called it intermodulation). Take A2 at 110 Hz and E3 at 164.8 Hz, a fifth up: their difference is 54.8 Hz and their sum 274.8 Hz, within 0.2 Hz of 55 and 5 × 55. Every product of the pair sits on, or a fraction of a hertz from, a multiple of 55 Hz, the harmonic series of A1 an octave below the root, so the chord sounds like one bigger note. The third, C♯3 at 138.6 Hz, gives 28.6 Hz and 248.6 Hz: they belong to a grid two octaves lower and miss even that by about 1 Hz, so they fall between the chord's harmonics and beat against them. In the spectrum, the power chord's lines sit on the 55 Hz grid, and the major chord's fall between:

```python {run continue}
def distorted(pitches):
    guitar = ElectricGuitar()
    return Amp(guitar.play(guitar.strum(pitches, 0.0, 1.0)), gain=25.0).take(1.0)

spectrum(*(distorted(p) for p in chords.values()), f0=55.0, harmonics=16, upto=1000.0,
         labels=list(chords), caption="A power chord and a major chord through the same amp")
```

## Palm muting and the bass

Resting the side of the picking hand on the strings by the bridge, *palm muting*, kills each note within a fraction of a second and darkens it. `PalmMute()` is an articulation (chapter 9): the string keeps only 90 % of its vibration on each trip, and the pluck is less bright. Eighths on the low E, open and then muted, through the amp:

```python {run continue}
from euterpe.instruments import PalmMute
from euterpe.pitch import E2

for art, name in ((None, "open"), (PalmMute(), "palm-muted")):
    guitar = ElectricGuitar()
    chug = [Note(i * 0.214, E2, 0.19, 0.9, articulation=art) for i in range(16)]
    display(Cabinet(Amp(guitar.play(chug), gain=20.0), size=1.4).take(3.8, f"Eighths on low E, {name}"))
```

Open, the notes smear into one roar; muted, each is a tight *chug*, the engine of metal rhythm guitar. Under all this a band needs a bass. `ElectricBass` is chapter 10's bass with a neck pickup and no box, damping each note when the next one is due:

```python {run continue}
from euterpe.instruments import ElectricBass

bass = ElectricBass()
display(Cabinet(Amp(bass.play(notes(first, up=-12, velocity=0.9)), gain=1.5), size=1.4).take(10.5, "The riff on the electric bass"))
```

## Feedback

Turn an amp up loud enough and stand near the speaker: its sound shakes the guitar, the shaken string feeds the pickup, and the loop keeps the note from dying. Often the string settles on one of its harmonics instead of its fundamental, and the note blooms up an octave. `ElectricGuitar.feedback(string, fret, at, length, harmonic)` plays such a note. Its limit is in `ElectricGuitar`'s docstring: the loop is not computed. The string is held, and a sine at its harmonic swells over it from 0.8 s on.

```python {run continue}
guitar = ElectricGuitar()
held = guitar.strum([B2, Fs3, B3], 0.0, 0.6, velocity=1.0) + guitar.feedback(2, 0, 0.6, 4.5)
display(Cabinet(Amp(guitar.play(held), gain=25.0)).take(5.5, "A B5 chord, then the B string held by the amp"))
```

## Putting it all together

The finale plays the theme four times, as Grieg's orchestra does: its first half twice, then all of it twice, each pass faster and louder, each one adding a layer this chapter built. The drums are chapter 14's `Kit`, met properly there; here it only keeps time. Its `pattern` reads one bar written as a grid, a row per drum and a character per eighth note: `x` strikes, `.` rests. `band` plays one pass:

```python {run continue name=band}
from euterpe.instruments import ElectricBass, ElectricGuitar, Kit, Neck, PalmMute
from euterpe.sound import Amp, Cabinet, ConvolutionReverb, Pan

kit = Kit()
BEAT = {kit.kick: "x...x...", kit.hihat: "x.x.x.x."}
ROCK = {kit.kick: "x...x.x.", kit.snare: "..x...x.", kit.hihat: "xxxxxxxx"}
CRASH = {kit.crash: "x.......", **ROCK}


def band(bpm, n, at, transpose=0, gain=1.0, mute=False, chords=False, drums=None, guitars=1):
    """One pass of the theme from at: the bass, one guitar (or two, panned apart), and drums
    from a one-bar grid of eighths. Returns its parts and the time it ends."""
    events = riff(bpm, n, at, transpose)
    parts = [Cabinet(Amp(ElectricBass().play(notes(events, up=-12, velocity=0.9)), gain=1.5), size=1.4)]
    for k in range(guitars):
        guitar = ElectricGuitar(pickup=Neck(), seed=k) if mute else ElectricGuitar(seed=k)
        played = []
        for t, p, d, beats in events:
            if chords and beats >= 2:
                played += guitar.strum([p, p + 7, p + 12], t, d * 0.95, velocity=0.9)
            else:
                played += notes([(t, p, d, beats)], up=12 if mute else 0, velocity=0.85,
                                articulation=PalmMute() if mute else None)
        amp = Cabinet(Amp(guitar.play(played), gain=gain, mid=2.0 if gain > 10 else 0.0))
        parts.append(Pan(amp, 0.6 * (2 * k - 1)) if guitars > 1 else amp)
    if drums:
        parts.append(kit.play([h for start, beat in bars(bpm, n, at) for h in kit.pattern(drums, beat / 2, start)]))
    return parts, events[-1][0] + events[-1][2]
```

The four passes. The first sneaks in: the bass, and the guitar palm-muted and clean on the neck pickup, an octave up, as the orchestra's plucked strings open the piece. The second adds kick and hi-hat and lets the guitar ring, at crunch. The third moves the theme up a fifth, so it comes home to F♯, as Grieg does, turns the gain to 25, lifts the mids 2 dB so the guitar cuts through, and plays power chords on the long notes. The fourth doubles the guitar with a second one of another `seed`, panned to the other side (*double tracking*, how heavy guitars are recorded), crashes on every *downbeat*, the first beat of a bar, and speeds up every two bars from 170 to 200 bpm. Then a last chord, and feedback:

```python {run continue name=finale}
parts, end = band(96, 4, 0.0, mute=True)
more, end = band(116, 4, end, gain=8.0, drums=BEAT); parts += more
more, end = band(140, 8, end, transpose=7, gain=25.0, chords=True, drums=ROCK); parts += more
pass4 = end
more, end = band([170, 170, 180, 180, 190, 190, 200, 200], 8, end, gain=25.0, chords=True, drums=CRASH,
                 guitars=2); parts += more
guitar = ElectricGuitar()
ending = guitar.strum([B2, Fs3, B3], end, 0.5, velocity=1.0) + guitar.feedback(2, 0, end + 0.5, 4.5)
parts.append(Cabinet(Amp(guitar.play(ending), gain=25.0)))
song = ConvolutionReverb(sum(parts) * 0.3, decay=1.2, mix=0.15)
length = end + 5.5
```

```python {run continue}
display(song.take(length, "In the Hall of the Mountain King (Grieg), for a rock band"))
```

Listen for each layer arriving: the muted guitar of the first pass, the crunch of the second, the power chords of the third, the two guitars spread left and right in the fourth. The ending is the amp holding a note that a string alone would let die.

That held note is where this chapter's tools stop. The amp turned a dying string into a tone that holds, but it took a string to start it, and everything here has the shape of a pluck: loud, then fading. Chapter 12 builds instruments whose tone holds for as long as a key is down, with no string at all: the organ, the electric piano and the synthesizer.

## Summary

- `ElectricGuitar` and `ElectricBass` are chapter 10's strings with no body, heard through a `Pickup`. A pickup misses the harmonics with a still point under it (`Neck()` at a quarter of the string, `Bridge()` near the bridge) and rolls the highs off with its coil.
- `Amp(src, gain, bass, mid, treble, level)` is a highpass, a `Saturator` and a tone stack of `LowShelf`, `Peak` and `HighShelf`. Gain moves it from clean through crunch to distortion.
- `Cabinet(src, size)` keeps 80 Hz to 5 kHz: it throws away the fizz that makes raw distortion ugly.
- Through distortion a fifth's sums and differences fall on the harmonic series of the note an octave below the root, and a third's do not: hence power chords.
- `PalmMute()` damps a plucked note at once; `ElectricGuitar.feedback` holds a note and blooms it into a harmonic.

## Exercises

1. In the pickup spectrum block, add `Pickup` to an import (`from euterpe.instruments import Pickup`) and change `Neck()` to `Pickup(position=0.5)`. Which harmonics of the open A (110 Hz) vanish, and what does the string sound like?
2. In the fifths block, change `gain=25.0` to `gain=2.0`. Does the major chord still growl? Why?
3. In the cabinet's response block, change `size=2.0` to `size=4.0`. Where do the box's resonance and the highpass move, and does the fizz come back?

### Answers

1. A pickup at the middle of the string sits on a still point of every even harmonic, so 220, 440, 660 Hz and the rest vanish, leaving 110, 330, 550 Hz. With only odd harmonics the note sounds hollow, like the square wave of chapter 3.
2. Much less. At gain 2 the chord barely reaches the bend of the curve, so the products at sums and differences are weak; the growl comes from the bend, not from the third itself.
3. Both move down by the factor: the resonance to 110 / 4 = 27.5 Hz and the highpass to 80 / 4 = 20 Hz, so the low end reaches below anything a guitar plays. The fizz does not come back: the two lowpasses stay at 5 kHz whatever the size.

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
