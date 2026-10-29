# Keys and synthesizers

This is where the chapter ends up:

```python {run echo=false}
# The teaser: the turn of the finale, from the held chord to the drop, built by the code of
# this chapter's last section, which it reads from this file so the two never differ.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import RATE, render

text = Path("chapters/12-keys-and-synthesizers.md").read_text()
for name in ("call", "dim", "chords", "subject", "acid", "finale"):
    exec(re.search(r"```python \{[^}\n]*name=" + name + r"\b[^}\n]*\}\n(.*?)\n```", text, re.S).group(1))
display(Clip(first[int((drop - 4.5) * RATE):], caption="Toccata and Fugue in D minor, the turn"))
```

An organ holds a chord in a church while its speaker starts to spin, and then the same piece drops onto a dance floor: Bach's *Toccata and Fugue in D minor* (BWV 565). Chapter 11 ended on a tone the amplifier kept alive. Every sound here holds for as long as a key is down, with no string at all: an organ made of sines, an electric piano made of FM, and the synthesizer patches built from an oscillator and a filter. Each section plays a piece of the Toccata, and the last one plays it all.

## The organ

A pipe organ sounds a note on several ranks of pipes at once. A rank is named by the length of its lowest pipe in feet: the 8′ rank plays the note itself, the 4′ an octave up, the 16′ an octave down, and the 2⅔′ an octave and a fifth up. The electric organ copied this with *drawbars*: nine sliders, one per rank, each pulled out from 0 to 8. Organists write a setting as nine digits, `888000000` for the first three fully out. Each rank is one sine at a ratio of the note, chapter 3's additive synthesis. `Organ(drawbars)` is that sum of sines, each drawbar step 3 dB quieter than the next. The Toccata opens on a *call*: a quick A–G–A (a *mordent*), a run down to C♯ and up to D, played in octaves. The piece tells it three times, an octave lower each time. Here it is once on the 8′ alone, a flute stop, and once on the first six drawbars:

```python {run continue name=call}
from euterpe.instruments import Note, Organ
from euterpe.pitch import A5, Cs5, D5, E5, F5, G5

# (beat, pitch, beats) of the call, from the score; a free tempo, so a beat is any length
CALL = [(0.0, A5, 0.0625), (0.0625, G5, 0.0625), (0.125, A5, 0.375), (0.625, G5, 0.0625), (0.6875, F5, 0.0625),
        (0.75, E5, 0.0625), (0.8125, D5, 0.0625), (0.875, Cs5, 0.6), (1.5, D5, 0.5)]


def call(at, beat, down=0, octaves=True):
    """The call from at, beat seconds a beat, down octaves lower, doubled an octave below."""
    out = []
    for b, p, d in CALL:
        for q in [p - 12 * down] + ([p - 12 * (down + 1)] if octaves else []):
            out.append(Note(at + b * beat, q, d * beat))
    return out
```

```python {run continue}
from euterpe.view import listen

display(listen(Organ("008000000").play(call(0.0, 0.9)), 2.5, "The call on the 8′ drawbar alone"))
display(listen(Organ("888888000").play(call(0.0, 0.9)), 2.5, "The call on the first six drawbars"))
```

The flute stop is pure and thin. Six drawbars give the full, buzzing organ sound, and the 16′ adds weight an octave down. The nine drawbars and their ratios to the note:

| drawbar | 16′ | 5⅓′ | 8′ | 4′ | 2⅔′ | 2′ | 1⅗′ | 1⅓′ | 1′ |
|---|---|---|---|---|---|---|---|---|---|
| ratio | 0.5 | 1.5 | 1 | 2 | 3 | 4 | 5 | 6 | 8 |

Two more knobs come from the electric organ: `click` is the short burst of noise of the key's contacts closing, on every note; `percussion=3` adds a third harmonic that strikes and dies in 0.3 s, only on notes played when no other key is held, as on the real instrument.

## The rotating speaker

The organ's sound became famous through its speaker, the *Leslie*: a horn for the highs and a drum for the lows, both spinning. As the horn's mouth turns towards you, the sound comes from a source moving closer, so its pitch rises; turning away, it falls (the Doppler effect). Its level swells and dips with it. That is chapter 8's chorus, a moving delay, plus a moving gain, and two microphones on opposite sides hear it half a turn apart. `Leslie(src, speed)` spins slowly at speed 0 (about 0.8 turns a second, *chorale*) and fast at 1 (about 6.7, *tremolo*):

```python {run continue}
from euterpe.sound import Leslie

organ = Organ("888888000")
display(listen(Leslie(organ.play(call(0.0, 0.9)), speed=0.0), 2.5, "The call through a slow Leslie"))
display(listen(Leslie(organ.play(call(0.0, 0.9)), speed=1.0), 2.5, "The call through a fast Leslie"))
```

The motors take time: the light horn reaches its new speed in about a second, the heavy drum in four. Organists switch speed in the middle of a chord for that ramp. After its three calls the Toccata builds a chord one note at a time over a low D: C♯, E, G, B♭, a *diminished seventh*, the most unstable chord there is, every note a minor third from the next. Held, with the speaker switched to fast at 2 s:

```python {run continue name=dim}
from euterpe.pitch import Bb3, Cs3, Cs4, D2, E3, E4, G3

DIM = [Cs3, E3, G3, Bb3, Cs4, E4]  # over a low D
```

```python {run continue}
from euterpe.sound import Segments

chord = [Note(0.0, D2, 6.0)] + [Note(0.3 * i, p, 6.0 - 0.3 * i) for i, p in enumerate(DIM, 1)]
fast_at_2 = Segments([(0.0, 0.0), (2.0, 0.0), (2.01, 1.0)])
display(listen(Leslie(organ.play(chord), speed=fast_at_2), 6.5, "The diminished chord, the Leslie spinning up"))
```

## The electric piano

An electric piano strikes a short metal bar, a *tine*, with a hammer, and a pickup hears it. FM synthesis (chapter 6) imitates it with two pairs of sines. In the first, a modulator at the note's own frequency has an index that starts high and settles in about a second: the attack is bright with harmonics and the tail is almost a sine. In the second, the modulator is 14 times the note and its index dies in 50 ms: a short ping of sidebands near the 13th and 15th harmonics, the metal of the tine. `ElectricPiano` scales both indexes by velocity, so a soft note is round and a hard one rings.

In the finale it plays dance music, so the piece needs a pulse. At 128 beats per minute a beat lasts 60 / 128 = 0.47 s and a *bar* is four beats. `chords` plays the Toccata's harmony, a bar of D minor and a bar of A major in turn, either held or as a stab on every *off-beat*, halfway between two beats:

```python {run continue name=chords}
from euterpe.pitch import A3, Cs3, D3, E3, F3

S = 60 / 128 / 4  # a sixteenth of a bar at 128 bpm
BAR = 16 * S
CHORDS = [[D3, F3, A3], [Cs3, E3, A3]]  # D minor, A major


def chords(at, bars, offbeats=False, velocity=0.6):
    """The harmony for bars bars from at, an octave up: held, or as a stab on each off-beat."""
    out = []
    for k in range(bars):
        for p in CHORDS[k % 2]:
            if offbeats:
                out += [Note(at + k * BAR + (j + 0.5) * BAR / 4, p + 12, BAR / 8, velocity) for j in range(4)]
            else:
                out.append(Note(at + k * BAR, p + 12, BAR, velocity))
    return out
```

```python {run continue}
from euterpe.instruments import ElectricPiano

ep = ElectricPiano()
display(listen(ep.play(chords(0.0, 4, offbeats=True, velocity=0.25)), 4 * BAR + 0.5, "Off-beat chords, soft"))
display(listen(ep.play(chords(0.0, 4, offbeats=True, velocity=1.0)), 4 * BAR + 0.5, "Off-beat chords, hard"))
```

Soft, the chords are round, almost sines. Hard, each one starts with the tine's ping and a bright attack that fades into the same round tail.

## Subtractive patches

A synthesizer *patch* is chapter 5's recipe: an oscillator rich in harmonics, a filter that removes some, and an envelope on the level (chapter 4). What makes patches sound alive is a second envelope, on the filter's cutoff: each note opens the filter and lets it close again. The filter is a new one. Chapter 5's `LowPass` falls 12 dB per octave above its cutoff; `Ladder` chains four simple low-passes and falls 24 dB per octave, the filter of the classic analog synthesizers. Its output is fed back to its input, and `resonance`, from 0 to 1, sets how strongly: the feedback adds at the cutoff and builds a peak there, until at 1 the filter whistles on its own.

```python {run continue}
from euterpe.sound import Ladder, LowPass, Sine
from euterpe.view import response

response(LowPass(Sine(1.0), 800.0), Ladder(Sine(1.0), 800.0), Ladder(Sine(1.0), 800.0, resonance=0.9),
         labels=["LowPass", "Ladder", "Ladder, resonance 0.9"], caption="Two low-passes at 800 Hz")
```

The ladder's peak also lowers everything below it: the analog filter does the same, and a resonant patch sounds thinner. `Patch` is an instrument made of these parts; its presets differ in their oscillators and their two envelopes. The shortest is `SynthPluck`: a saw whose filter snaps shut in 0.15 s. It plays the Toccata's fugue, whose *subject* (its theme) alternates a repeated A with a line that falls and climbs again, sixteen notes a bar:

```python {run continue name=subject}
from euterpe.instruments import SynthPluck
from euterpe.pitch import A3, A4, B3, Cs4, D4, E4, F4, G4

SUBJECT = [A4, G4, A4, F4, A4, E4, A4, D4, A4, Cs4, A4, D4, A4, E4, A4, F4,
           A4, A3, A4, B3, A4, Cs4, A4, D4, A4, Cs4, A4, D4, A4, E4, A4, F4]


def subject(at, bars, up=0):
    """The subject from at, one note per sixteenth, repeated for bars bars, up semitones higher."""
    return [Note(at + i * S, SUBJECT[i % 32] + up, S * 0.9) for i in range(16 * bars)]
```

`Lead` plays one note at a time with a saw and a square an octave down, a vibrato that grows in, and a *glide*: a new note joined to the last slides to its pitch in 50 ms. `Pad` is the opposite: three slightly detuned saws in stereo, a filter that opens over a second, and a slow attack and release, so chords swell and fade. The subject on the pluck, then the call on the lead, at dance tempo, over held chords on the pad:

```python {run continue}
from euterpe.instruments import Lead, Pad

lead, pad = Lead().play(call(0.0, BAR / 2, octaves=False)), Pad().play(chords(0.0, 2))
display(listen(SynthPluck().play(subject(0.0, 4, up=12)), 4 * BAR + 0.4, "The fugue's subject on SynthPluck"))
display(listen(lead * 1.6 + pad, 2 * BAR + 1.5, "The call on Lead over Pad"))
```

## Detune and the supersaw

Two saws a few cents apart beat: each harmonic becomes two lines close together, and their sum swells and fades a few times a second, faster for higher harmonics. `Unison(osc, freq, voices, detune, width)` plays several copies of one oscillator spread over plus and minus `detune` semitones and across the stereo field. `Supersaw` is seven of them, 0.2 semitones either way, under an open filter: the lead sound of trance music. The subject with one saw, then with seven:

```python {run continue}
from euterpe.instruments import Supersaw

display(listen(Supersaw(voices=1).play(subject(0.0, 2, up=12)), 2 * BAR + 0.4, "The subject on one saw"))
display(listen(Supersaw().play(subject(0.0, 2, up=12)), 2 * BAR + 0.4, "The subject on seven detuned saws"))
```

One saw sits thin in the middle. Seven fill the space between the speakers and shimmer, as a section of players does, none quite in tune with the others.

## The acid bass

The last patch is a bass whose filter sits near the edge of whistling: `AcidBass`, one saw driven into chapter 8's `Saturator`, then a `Ladder` at resonance 0.85 whose cutoff jumps up on every note and falls back in a quarter of a second. Each note says "wow".

An acid line is played from a *step sequencer*: sixteen steps a bar, each with a pitch and two marks. An `Accent` opens the filter twice as far, closes it faster and plays louder. A slide holds the step before it and, with `Legato`, glides into the new pitch in 60 ms instead of starting again. Here the pattern is a list: `x` accents a step, `~` slides into it. Under it, the kick drum of chapter 14's `Kit`, met properly there, on every beat:

```python {run continue name=acid}
from euterpe.instruments import Accent, Kit, Legato
from euterpe.pitch import A2, Bb2, C3, D2, D3, E2, F2

ACID = [(D2, "x"), (D2, "."), (D3, "."), (D2, "."), (F2, "x"), (D2, "."), (A2, "."), (D2, "."),
        (C3, "x"), (D3, "~"), (D2, "."), (A2, "."), (Bb2, "x"), (A2, "~"), (F2, "."), (E2, ".")]


def acid(at, bars):
    """The pattern for bars bars from at: a step is held into a slide, or lasts half a sixteenth."""
    out = []
    for i in range(16 * bars):
        p, mark = ACID[i % 16]
        slides = ACID[(i + 1) % 16][1] == "~"
        art = Accent() if mark == "x" else Legato() if mark == "~" else None
        out.append(Note(at + i * S, p, S * (1.05 if slides else 0.5), 0.8, art))
    return out


kit = Kit()
```

```python {run continue}
for resonance in (0.2, 0.85):
    four = kit.play(kit.pattern({kit.kick: "x...x...x...x..."}, S, repeat=4))
    bass = AcidBass(resonance=resonance).play(acid(0.0, 4))
    display(listen(bass * 1.4 + four * 1.4, 4 * BAR + 0.3, f"The acid pattern over a kick, resonance {resonance}"))
```

At resonance 0.2 the cutoff's sweep is a plain wah on each note. At 0.85 the peak at the cutoff sings as it falls, loudest on the accents, and the slides bend it.

## Putting it all together

The finale follows the Toccata from the church to the dance floor in five parts. The organ plays the three calls, an octave lower each time, and builds the diminished chord over the low D. The chord holds while the Leslie spins up and the pad rises under it through a ladder opening from 300 Hz to 6 kHz. Then the drop, at 128 bpm: kick, acid bass, off-beat electric piano and the subject on the pluck, eight bars. The peak takes the subject to the supersaw, holds the harmony on the pad and plays the call on the lead, eight bars more. Everything stops on the diminished chord, and the organ resolves it to D minor, left on the pad. The organ and pad go through one reverb, with the pluck, supersaw and lead; the drums, bass and piano stay dry and close. Rendering 54 s of nine parts takes about a minute, and the book gives each block two, so the song renders in two calls: `render(song, seconds, reset=False)` continues from where the last call stopped, sample for sample.

```python {run continue name=finale}
from euterpe.instruments import AcidBass, ElectricPiano, Lead, Organ, Pad, Supersaw, SynthPluck
from euterpe.pitch import A3, D3, D4, F3
from euterpe.sound import FDNReverb, Ladder, Leslie, Segments
from euterpe.sound.core import render

dim_at = 6.6 * 0.9
church = call(0.0, 0.9) + call(2.2 * 0.9, 0.9, 1) + call(4.4 * 0.9, 0.9, 2)
church += [Note(dim_at, D2, 7.5)] + [Note(dim_at + 0.45 + 0.225 * i, p, 7.0 - 0.225 * i) for i, p in enumerate(DIM)]
drop = dim_at + 7.5
peak, end = drop + 8 * BAR, drop + 16 * BAR
church += [Note(end + BAR, p, 5.0) for p in (D2, D3, F3, A3, D4)]
spin = Segments([(0.0, 0.0), (drop - 4.0, 0.0), (drop - 3.99, 1.0), (end + BAR, 1.0), (end + BAR + 0.01, 0.0)])
rise = Segments([(drop - 4.0, 300.0), (drop, 6000.0)])

wet = [Leslie(Organ("888888000").play(church), speed=spin) * 0.8,
       Ladder(Pad().play([Note(drop - 4.0, p, 4.0, 0.8) for p in (D3, Bb3, Cs4, E4, G3)]), rise, 0.6) * 1.2,
       SynthPluck().play(subject(drop, 8, up=12)) * 1.4,
       Supersaw().play(subject(peak, 8, up=12) + [Note(end, p + 12, BAR * 0.9, 1.0) for p in DIM]) * 1.5,
       Pad().play(chords(peak, 8) + [Note(end + BAR + 1.0, p, 6.0, 0.8) for p in (D3, F3, A3, D4)]) * 0.9,
       Lead().play(call(peak, BAR / 2, octaves=False) + call(peak + 4 * BAR, BAR / 2, octaves=False)) * 1.6]
beat = kit.pattern({kit.kick: "x...x...x...x..."}, S, drop, repeat=16) + kit.pattern({kit.kick: "x"}, S, end)
dry = [kit.play(beat) * 1.4, AcidBass().play(acid(drop, 16)) * 1.4, ElectricPiano().play(chords(drop, 16, offbeats=True))]
song = (sum(dry) + FDNReverb(sum(wet), decay=2.5, mix=0.3)) * 0.35
length = end + BAR + 8.5
first = render(song, drop + 5.0)
```

```python {run continue}
import numpy as np
from euterpe.sound.clip import Clip

rest = render(song, length - (drop + 5.0), reset=False)
display(listen(Clip(np.concatenate([first, rest])), caption="Toccata and Fugue in D minor (BWV 565), from organ to synthesizers"))
```

Listen for the speaker's ramp under the held chord, the drop landing on the kick and the squelch, the subject moving from the pluck to the wide supersaw, and the call coming back on the lead above it.

The pad holds the last chord: three detuned saws, a synthesizer's idea of a string section, and a convincing one from a distance. Up close it is too even. Every note starts the same way and holds without change, because nothing plays it: no bow pressing on a string, no breath in a tube. Chapter 13 drives a string and a column of air with a continuous force, and finds where synthesis stops.

## Summary

- `Organ(drawbars)` is additive synthesis on nine ratios, the ranks of a pipe organ, with key click and percussion; `Leslie(src, speed)` spins its sound with Doppler and tremolo, and ramps between speeds.
- `ElectricPiano` is two FM pairs: a body whose index settles in a second and a tine at ratio 14 whose index dies in 50 ms. Velocity scales both.
- `Ladder(src, cutoff, resonance)` falls 24 dB per octave and builds a peak at its cutoff as resonance grows.
- A `Patch` is oscillators, a ladder whose cutoff follows an envelope, and an amp envelope. `SynthPluck`, `Lead`, `Pad`, `Supersaw` and `AcidBass` differ in those parts.
- `Unison` stacks detuned copies of an oscillator across the stereo field; seven saws make the supersaw.
- An instrument's `glide` sets how long a slur takes; `AcidBass` reads `Accent` and slides on `Legato`.

## Exercises

1. In the organ block, change `"888888000"` to `"800000008"`. Which two lines remain, how far apart are they, and what does the call sound like?
2. In the supersaw block, change `Supersaw()` to `Supersaw(detune=1.0)`. What happens to the pitch of the subject, and why?
3. In the acid block, change `AcidBass()` to `AcidBass(resonance=0.99)`. What do you hear on the accented steps?

### Answers

1. The 16′ and the 1′ drawbars: ratios 0.5 and 8, four octaves apart. Each note is a low sine and a whistle far above it, with nothing between; the call sounds hollow and squeaky at once.
2. The copies now spread a whole semitone either way, so the subject sounds out of tune with itself, a cluster of near pitches instead of one. Detune shimmers only while the copies stay within a fraction of a semitone.
3. The filter rings at its cutoff almost on its own, so each accent adds a whistle that sweeps down from high to low, louder than the saw under it.

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
