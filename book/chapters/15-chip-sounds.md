# Chip sounds

Chapter 14 ended on a promise: the 1980s made drums, basses and melodies from a few square waves and a noise channel. This is where this chapter ends up, the moment a song turns from the old chip to a modern take on it:

```python {run echo=false}
# The teaser: the turn from the classic pass to the modern one in the finale, built by the code of
# this chapter's two named finale blocks, which it reads from this file so the two never differ.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import RATE, render

text = Path("chapters/15-chip-sounds.md").read_text()
scope = {}
for name in ("classic", "modern"):
    code = re.search(rf"```python \{{[^}}\n]*name={name}\b[^}}\n]*\}}\n(.*?)\n```", text, re.S).group(1)
    exec("\n".join(line for line in code.split("\n") if "listen(" not in line), scope)
t0 = scope["t0"]
display(Clip(render(scope["song"], t0 + 4.0)[int((t0 - 4.5) * RATE):], caption="Korobeiniki, from the classic chip to the modern one"))
```

*Korobeiniki*, a Russian folk melody, played on four channels of a handheld game console's sound chip: first with the chip's own limits, then with what a modern composer adds back. A puzzle game of 1989 made it the best-known chip tune there is; the arrangement here is this chapter's own.

## Four channels

A *sound chip* is the part of a console that makes its sound. Each of its *channels* plays one note at a time, and the program writes a few numbers to it, a pitch, a volume, a shape, about 60 times a second. A channel costs transistors, and on a battery handheld every transistor costs money and power. The music had to fit in a few kilobytes of the game's memory, next to the game. So the chip of this chapter has four channels, and each does one thing:

| Channel | Sound | Used for |
|---|---|---|
| `pulse1`, `pulse2` | a square wave with four widths, 16 volume steps | melody, harmony |
| `wave` | a cycle of 32 steps of 16 levels, 4 volumes | bass |
| `noise` | a shift register's noise, 16 volume steps | drums |

Euterpe has each channel as an instrument with polyphony 1 (chapter 9), and two consoles that hold all four: `ClassicChip`, with the chip's limits, and `ModernChip`, without them. The sections below take the channels one by one, in the classic style.

## The pulse

A *pulse* wave is a square wave whose high part takes a fraction of the cycle, its *duty*. Duty 0.5 is chapter 3's square: odd harmonics only. A narrower pulse has more harmonics. The level of harmonic k is proportional to |sin(π k d)| / k, for duty d, so harmonic k vanishes wherever k d is a whole number: duty 0.5 loses every 2nd harmonic, duty 0.25 every 4th, duty 0.125 every 8th. The chip offers four duties, 0.125, 0.25, 0.5 and 0.75; 0.75 is 0.25 upside down and sounds the same. `PulseChannel(duty)` is one of these channels:

```python {run}
from euterpe.instruments import PulseChannel
from euterpe.pitch import A3
from euterpe.view import spectrum

thin = PulseChannel(duty=0.125).play([(0.0, A3, 1.5)]).take(1.5, "A pulse at duty 0.125")
hollow = PulseChannel(duty=0.5).play([(0.0, A3, 1.5)]).take(1.5, "A pulse at duty 0.5")
display(thin, hollow)
spectrum(thin, hollow, f0=220.0, harmonics=16, labels=["duty 0.125", "duty 0.5"],
         caption="The spectra of a pulse at 220 Hz, duty 0.125 and 0.5")
```

Duty 0.5 is round and hollow, with the odd harmonics of chapter 13's clarinet. Duty 0.125 is thin and nasal: its first harmonics are almost equally loud, and the gap comes only at the 8th. Composers kept 0.5 for soft lines and 0.125 or 0.25 for leads that had to cut through.

The volume has 16 steps, 0 to 15, and no smooth fade: the chip's *envelope* moves the volume one step every `pace` 64ths of a second, down to 0. `Fade(start, pace)` is that envelope, and pace 0 holds the volume. The same note at full velocity, so the fade starts at 15, with the fastest fade and the slowest:

```python {run}
from euterpe.instruments import Fade, PulseChannel
from euterpe.pitch import A3

for pace in (1, 7):
    pulse = PulseChannel(duty=0.5, envelope=Fade(15, pace=pace))
    display(pulse.play([(0.0, A3, 2.0, 1.0)]).take(2.0, f"Fade(15, pace={pace}): 15 steps down in {15 * pace / 64:.2f} s"))
```

At pace 1 the note is a short blip, 0.23 s; the steps go by too fast to hear one by one. At pace 7 each step lasts 0.11 s and the fade is a staircase you can count: the sound of every chip-tune note that dies away.

## A clock divided

A channel has no oscillator of its own. The chip has one clock, and a channel counts its ticks: the pulse channels sound at 131 072 / (2048 − n) Hz, where the program writes n, a whole number from 0 to 2047. So the chip can only play the pitches of that formula. Low down they are dense, and one lands close to every note. High up, 2048 − n is small and each step of n jumps far. The block finds the nearest n to each C from C4 to C8 and prints how far that pitch is from the true C, in cents (chapter 2: a hundredth of a semitone):

```python {run output=code}
import numpy as np
from euterpe.pitch import C4, C5, C6, C7, C8

f = np.array([c.freq for c in (C4, C5, C6, C7, C8)])
n = np.round(2048 - 131_072 / f)
print(np.round(1200 * np.log2(131_072 / (2048 - n) / f), 1))
```

C4 is exact, C7 is 10 cents flat and C8 17 cents sharp. Two notes 10 cents apart, played together, beat audibly, and these errors change sign from note to note, so a melody up high goes sour. `quantize=True`, the default, moves every note to the chip's nearest pitch. The opening of *Korobeiniki*, two octaves above where it belongs, as the chip plays it and in tune:

```python {run}
from euterpe.instruments import PulseChannel
from tunes import notes

for quantize in (True, False):
    pulse = PulseChannel(duty=0.25, quantize=quantize)
    display(pulse.play(notes("korobeiniki", 0.0, 0.3, up=24)).take(4.8, f"Korobeiniki two octaves up, quantize={quantize}"))
```

The tune is in `book/tunes.py`, as chapter 13's were: `notes("korobeiniki", at, beat, up)` gives it as `Note`s, `beat` seconds a beat, `up` semitones higher.

## The wave channel

The wave channel plays chapter 6's table: 32 steps, each one of 16 levels, 0 to 15, read once a cycle. The program can write any table, so a composer picks the timbre. `TRIANGLE`, `SAW` and `SQUARE` are three tables in Euterpe; the triangle climbs 0, 1, … 15 and falls back. The channel has no volume steps, only `shift`, which halves the level once or twice: 100, 50 or 25 %. Its clock runs at half the pulses' rate, 65 536 / (2048 − n) Hz, because its table is twice as long, so it reaches an octave lower; that is why it plays the bass. A bass of roots and fifths, A2 and E3, in eighths:

```python {run}
from euterpe.instruments import SAW, TRIANGLE, WaveChannel
from euterpe.pitch import A2, E3

bass = [(0.21 * i, (A2, E3)[i % 2], 0.19) for i in range(16)]
for table, name in ((TRIANGLE, "triangle"), (SAW, "saw")):
    display(WaveChannel(table).play(bass).take(3.5, f"A {name} bass on the wave channel"))
```

A triangle is soft, with only odd harmonics that fall fast, so it sits under a melody without covering it. The saw, 0, 0, 1, 1, … 15, 15, has every harmonic and growls. In both, the steps add a faint buzz, the images near 32 times the pitch that chapter 6 heard. `shift=2` would play either 12 dB softer, the only mix control a composer had for the bass; the players on this page all play at one loudness, so it is not heard here.

## Noise drums

The noise channel is chapter 6's linear-feedback shift register: 15 bits, which repeat every 32 767 steps and hiss, or 7 bits with `short`, which repeat every 127 and buzz at a pitch. A `NoiseDrum(rate, short, fade)` sets how fast the register steps, which register, and a `Fade`. The chip's rates come from a formula too, 262 144 / (r · 2^s) Hz; the drum below steps at 262 144 / 2^5 = 8192 Hz, with each register:

```python {run}
from euterpe.instruments import Fade, NoiseChannel, NoiseDrum

noise = NoiseChannel()
for short in (False, True):
    drum = NoiseDrum(rate=262_144 / 2**5, short=short, fade=Fade(15, pace=3))
    display(noise.play(noise.hit(0.0, drum)).take(0.9, f"Noise at 8192 Hz, short={short}"))
```

The long register is a burst of hiss, a snare or a crash. The short one is a rough tone at 8192 / 127 = 64.5 Hz with a metallic edge, which games used for engines and explosions.

`NoiseChannel` has three drums ready, `kick`, `snare` and `hat`: a low rate that rumbles, a middle one, and a high one that hisses with a short fade. Its `pattern` reads chapter 14's grid. The channel plays one hit at a time, so the hat goes between the kick and the snare. A noise kick is weak, so games often borrowed a pulse channel and swept it down: `sweep` bends the pitch that many semitones a second. A drop of 120 semitones a second over 0.2 s is two octaves, chapter 14's falling kick made from a square:

```python {run}
from euterpe.instruments import ClassicChip, Fade, PulseChannel
from euterpe.pitch import A3

noise, step = ClassicChip().noise, 60 / 144 / 2
display(noise.play(noise.pattern({noise.kick: "x...x...", noise.snare: "..x...x.", noise.hat: ".x.x.x.x"}, step, repeat=4))
        .take(3.4, "The three noise drums: kick, hat, snare, hat"))
thump = PulseChannel(duty=0.5, sweep=-120.0, envelope=Fade(15, pace=1))
kicks = [(4 * step * i, A3, 0.2) for i in range(8)]
grid = {noise.snare: "..x...x.", noise.hat: ".x.x.x.x"}
(noise.play(noise.pattern(grid, step, repeat=4)) + thump.play(kicks)).take(3.4, "The same beat with a pulse kick swept from A3 down two octaves")
```

## One note at a time

A channel plays one note at a time, and the chip has two pulses. A chord of three notes does not fit. The trick of the era was to play the chord's notes in turn, very fast, one per frame of the screen, 60 a second: too fast to hear as a melody, so the ear hears a buzzing chord. `arpeggio(at, pitches, length, step)` makes those notes on any tone channel; the step decides whether it is a chord or a tune:

```python {run}
from euterpe.instruments import PulseChannel
from euterpe.pitch import A3, C4, E4

pulse = PulseChannel(duty=0.125)
for step in (1 / 60, 1 / 8):
    display(pulse.play(pulse.arpeggio(0.0, [A3, C4, E4], 2.0, step)).take(2.0, f"A minor, one note every {step:.3f} s"))
```

At 1/8 s the three notes are a figure, A, C, E, A, C, E. At 1/60 s they fuse into a chord with a fast warble, the chord sound of most game music of the 1980s.

Now the first phrase of *Korobeiniki*, four bars of four beats at 144 beats a minute (bpm), on `pulse1`, over arpeggios of its chords on `pulse2`: A minor, E major, the chord whose B and G♯ pull back to A. A chord changes every half bar, two beats. `ClassicChip()` holds the four channels, and `play` takes each channel's notes by name and mixes them:

```python {run}
from euterpe.instruments import ClassicChip
from euterpe.pitch import A3, B3, C4, E3, E4, Gs3
from tunes import notes

chip, beat = ClassicChip(), 60 / 144
chip.pulse2.duty = 0.125
triads = {"Am": [A3, C4, E4], "E": [E3, Gs3, B3]}
arp = [n for h, c in enumerate("Am E Am Am E E Am Am".split()) for n in chip.pulse2.arpeggio(2 * beat * h, triads[c], 2 * beat, velocity=0.6)]
phrase = notes("korobeiniki", 0.0, beat)[:19]
chip.play(pulse1=phrase, pulse2=arp).take(7.0, "Korobeiniki, the first phrase, melody and arpeggios")
```

## The modern style

Chip music did not die with the consoles. Composers still write it, on the same four channels, but with what the old chip could not do. `ModernChip()` plays them with a smooth volume envelope (chapter 4's `ADSR`) instead of 16 steps, exact pitches instead of the divider's, a vibrato that starts after 0.3 s (chapter 13), a 40 ms slide between notes marked `Legato` (chapter 9), the pulses panned left and right, an echo on them (chapter 8's `Delay`, 0.3 s) and a reverb on the whole (chapter 8's `FDNReverb`). The same phrase on both consoles:

```python {run continue}
from euterpe.instruments import ClassicChip, ModernChip

for chip in (ClassicChip(), ModernChip()):
    display(chip.play(pulse1=phrase).take(7.5, f"The phrase on the {type(chip).__name__}"))
```

The classic note starts and stops like a switch, and every note holds one level. The modern note swells in, the long ones sing with vibrato, and the echo repeats each note softly a dotted eighth later, at this tempo almost exactly 0.3 s.

The modern style's other trick is `detune`: `pulse2` plays a few cents off the pitch, so when both pulses play one line they beat against each other, chapter 12's supersaw with two voices. The phrase on both pulses, in tune and 15 cents apart:

```python {run continue}
from euterpe.instruments import ModernChip

for cents in (0.0, 15.0):
    chip = ModernChip(detune=cents, echo=0.0)
    display(chip.play(pulse1=phrase, pulse2=phrase).take(7.5, f"The phrase doubled, pulse2 detuned {cents:g} cents"))
```

At 0 cents the two pulses are one louder pulse. At 15 cents A4 beats at 440 × (2^(15/1200) − 1) = 3.8 Hz, a slow, wide shimmer.

## Putting it all together

*Korobeiniki* is a folk melody set to Nekrasov's poem of 1861 about travelling pedlars, in A minor, in 4/4. The finale plays it twice. First on `ClassicChip`, 8 bars at 144 bpm: the melody on `pulse1` at duty 0.5, arpeggios of the chords on `pulse2` at 0.125, a bass of roots and fifths in eighths on the wave channel, and a backbeat on the noise channel. The chords are A minor, E major, D minor and C major, a chord every half bar; the bass and the drums are helpers, used by both passes:

```python {run name=classic}
from euterpe.instruments import ClassicChip
from euterpe.pitch import A2, A3, B3, C3, C4, D2, D3, E2, E3, E4, F3, G3, Gs3
from tunes import notes

triads = {"Am": [A3, C4, E4], "E": [E3, Gs3, B3], "Dm": [D3, F3, A3], "C": [C3, E3, G3]}
roots = {"Am": A2, "E": E2, "Dm": D2, "C": C3}
first = "Am E Am Am E E Am Am Dm Dm C C E E Am Am".split()


def bass(chords, at, beat):
    """Root, fifth, root, fifth in eighths: four notes a chord, two beats."""
    return [(at + 2 * beat * h + e * beat / 2, roots[c] + 7 * (e % 2), 0.45 * beat) for h, c in enumerate(chords) for e in range(4)]


def drums(noise, at, beat, bars):
    return noise.pattern({noise.kick: "x...x...", noise.snare: "..x...x.", noise.hat: ".x.x.x.x"}, beat / 2, at, repeat=bars)


chip, beat = ClassicChip(), 60 / 144
chip.pulse2.duty = 0.125
arp = [n for h, c in enumerate(first) for n in chip.pulse2.arpeggio(2 * beat * h, triads[c], 2 * beat, velocity=0.6)]
old = chip.play(pulse1=notes("korobeiniki", 0.0, beat), pulse2=arp, wave=bass(first, 0.0, beat), noise=drums(chip.noise, 0.0, beat, 8))
t0 = 32 * beat
```

Then `ModernChip` takes over at 152 bpm for both themes, 16 bars and a last A. The melody moves to duty 0.25, and the second theme's half notes slide into each other in pairs. `pulse2` plays a harmony a third or a sixth under the melody, detuned, instead of arpeggios: a modern chip has reverb to fill the space between the notes. The classic chip is louder, since its notes do not swell and its mono sum is not panned, so it is turned down to meet the modern one:

```python {run continue name=modern}
from euterpe.instruments import Legato, ModernChip, Note
from euterpe.pitch import A4, A5, B4, C5, D5, E4, E5, F5, G5, Gs4, Gs5
from euterpe.view import listen
from tunes import notes

chip, beat = ModernChip(), 60 / 152
chip.pulse1.duty = 0.25
second = notes("korobeiniki2", t0 + 32 * beat, beat)
for n in second[1::2]:
    n.articulation = Legato()
melody = notes("korobeiniki", t0, beat) + second + [Note(t0 + 64 * beat, A4, 2 * beat)]
under = {E5: C5, D5: B4, C5: A4, B4: Gs4, A4: E4, F5: D5, G5: E5, A5: E5, Gs4: E4, Gs5: E5}
harmony = [Note(n.time, under[n.pitch], n.duration, 0.5) for n in melody]
chords = first + ("Am Am E E " * 4 + "Am Am").split()
new = chip.play(pulse1=melody, pulse2=harmony, wave=bass(chords, t0, beat), noise=drums(chip.noise, t0, beat, 17))
song = old * 0.5 + new * 1.2
listen(song, t0 + 68 * beat + 2.0, "Korobeiniki, on the classic chip, then the modern one")
```

Listen for the arpeggios' warble and the sour high notes of the first pass, then the second pass opening out: the melody slides and sings, the harmony beats against it, and the echo and the room give the four channels a space the classic chip never had.

Every note here was typed as a time in seconds and a pitch name, and the chords as a string of names that the code looked up. A musician writes *Korobeiniki* as bars in a key, A minor, and its bass as a progression of chords that follow rules of their own. Chapter 16, the first of Part III, starts that language: notes, octaves and how they are spelled.

## Summary

- A sound chip has few channels because each costs transistors and power; each plays one note at a time.
- `PulseChannel(duty)`: a pulse at duty 0.125, 0.25, 0.5 or 0.75, which loses every 8th, 4th or 2nd harmonic. `Fade(start, pace)` steps its volume through 16 levels; `sweep` bends its pitch, for kicks and effects.
- Every pitch is a clock divided by a whole number, 131 072 / (2048 − n) Hz, so high notes land up to tens of cents off; `quantize` turns that on.
- `WaveChannel(table, shift)`: a cycle of 32 steps of 16 levels at three volumes, an octave lower, for the bass.
- `NoiseChannel` plays `NoiseDrum`s on a 15- or 7-bit shift register, by `hit` or `pattern`.
- `arpeggio` plays a chord one note at a time; at 60 notes a second the ear hears a chord.
- `ClassicChip` and `ModernChip` hold the four channels; the modern one adds smooth volume, exact pitch, vibrato, slides, detune, echo and reverb.

## Exercises

1. In the first block, change `duty=0.125` to `duty=0.25`. Which harmonics vanish from the spectrum now?
2. In the noise block, change `rate=262_144 / 2**5` to `rate=262_144 / 2**3`. What happens to the hiss, and to the short register's pitch?
3. In the arpeggio block, change `1 / 60` to `1 / 20`. Is it still a chord?

### Answers

1. Every 4th: the 4th, 8th, 12th and 16th, where k × 0.25 is a whole number. The 2nd comes back, so the tone is brighter than duty 0.5 and fuller than 0.125.
2. The register steps 4 times faster, at 32 768 Hz, so the long noise moves up and hisses like a hi-hat. The short register now repeats at 32 768 / 127 = 258 Hz, near C4, a buzzing tone instead of a growl.
3. Barely. At 20 notes a second each note lasts 50 ms, long enough for the ear to follow, so the chord turns into a fast trill of three notes.

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
