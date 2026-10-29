# Plucked strings

Chapter 7 built a plucked string, `Pluck`: a burst of noise circulating in a delay line, losing its high harmonics first. On its own it sounds like a bare wire. A guitar, a harp or a bass is more than its string: something plucks it, a finger or a pick, and the string sounds through a wooden body that colours it. This chapter builds the plucked family from those three parts, then plays four instruments made from them: the guitar, the bass guitar, the harp and a section of strings plucked with the fingers. This is where it ends up:

```python {run echo=false}
# The teaser: the last pass of the finale, built by the code of this chapter's last block, which
# it reads from this file so the two never differ. The block's own player is skipped.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import RATE, render

text = Path("chapters/10-plucked-strings.md").read_text()
scope = {}
code = re.search(r"```python \{[^}\n]*name=finale\b[^}\n]*\}\n(.*?)\n```", text, re.S).group(1)
exec("\n".join(line for line in code.split("\n") if ".take(" not in line), scope)
display(Clip(render(scope["song"], 33.0)[24 * RATE:], caption="The last pass of the chapter's finale"))
```

Pachelbel's Canon, with all four instruments of this chapter playing at once in one hall: the bass guitar, the harp, the plucked strings and the guitar.

## Three parts

`Plucked` is the family's instrument. It takes its parts as arguments, each a small class:

- the **exciter**, what sets the string moving: `Finger()` or `Plectrum()` (a pick), each with a `position` along the string and a `brightness`;
- the **string**: `Steel()`, `Nylon()` or `Gut()`, each with a `damping`, the share of the vibration that survives each trip along the string (chapter 7);
- the **body**: `GuitarBody()`, `BassBody()`, `HarpBody()`, `ViolinBody()`, or `None` for a bare string.

For each note, `voice` makes a `Pluck` from the exciter and the string, sends it through the body, and scales it by the note's velocity. A harder note also starts brighter: the exciter's brightness is multiplied by 0.5 + 0.5 × velocity, from half at velocity 0 to all of it at 1, because a string pulled harder is released with a sharper bend. Here is one A2, first without a body, then through a guitar's:

```python {run}
from euterpe.instruments import GuitarBody, Plucked
from euterpe.pitch import A2

bare = Plucked(body=None).note(A2, 2.0)
boxed = Plucked(body=GuitarBody()).note(A2, 2.0)
display(bare.take(2.0, "A2 on a bare steel string"))
display(boxed.take(2.0, "The same string through a guitar's body"))
```

The note is A2, 110 Hz, the note of the guitar's fifth string played *open*, without a finger pressing it. The bare string is thin and buzzing; through the body it sounds fuller and rounder, and that is the difference between a wire and an instrument.

## The body

A guitar's body is a box of thin wood with a hole in its top. When the string vibrates, it shakes the bridge, the bridge shakes the top, and the top, much larger than the string, moves the air. The box does not pass every frequency the same: like the bar of chapter 7, it has *modes*, frequencies at which it vibrates easily. The lowest is the air in the box going in and out of the hole, near 100 Hz on a guitar. Above it are the modes of the top plate.

`Body(src, freqs, decays, amps, dry)` from `euterpe.sound` models a body as a few modes. The string drives one resonator per mode, the same idea as `Modal` with an `excite` in chapter 7, and the output is the string itself times `dry` plus what the modes ring. Each resonator is a *band-pass* (chapter 5) with its gain, `amps`, at its own frequency and no gain at 0 Hz, so a mode boosts the notes and harmonics near it and leaves the rest. Each mode's decay is the time it takes to fall 60 dB once the string stops driving it, as in `Modal`. `GuitarBody()` holds four modes:

```python {run continue output=code}
from euterpe.instruments import BassBody, GuitarBody, HarpBody, ViolinBody

for body in (GuitarBody(), BassBody(), HarpBody(), ViolinBody()):
    print(f"{type(body).__name__:10} modes at {body.freqs} Hz, decays {body.decays} s, amps {body.amps}, dry {body.dry}")
```

The spectrum shows where the guitar's body works. Its air mode at 100 Hz lifts the note's fundamental at 110 Hz, and its plate modes lift the harmonics near them: 200 Hz is close to the second harmonic, 220; 550 Hz is exactly the fifth, 5 × 110; 390 lies between the third and fourth, 330 and 440:

```python {run continue echo=false}
from euterpe.view import spectrum

spectrum(bare.take(1.0), boxed.take(1.0), labels=["bare string", "guitar body"], f0=110, upto=2000,
         caption="A2 on a bare string and through a guitar's body: the body lifts the harmonics near its modes")
```

A bigger box has lower modes. `BassBody` puts its air mode at 70 Hz, and `ViolinBody` at 275 Hz, which is why a violin plucked sounds small. This is the model's limit too: a real body has hundreds of modes, spread and coupled, and four of them give its low resonance but not its whole colour.

## The exciter

Chapter 7 showed what the pluck point does: plucking at 1/n of the string's length removes every n-th harmonic. A finger is soft and plucks away from the bridge; a pick is hard and plucks near it. Here is one *strummed* A chord (a pick swept across the strings), with a pick near the bridge, at `position=0.06`, and the same chord at the middle of the string, `position=0.5`. `Shape(None, 0, 2, 2, 2, 0)` says which *fret* each string is pressed at, from the thickest string to the thinnest, and `strum` sweeps them; the section on the guitar explains both; `variation=0.0` keeps every pluck exactly at its position (the section after this one explains variation):

```python {run}
from euterpe.instruments import Guitar, Plectrum, Shape

A = Shape(None, 0, 2, 2, 2, 0)
for position in (0.06, 0.5):
    guitar = Guitar(exciter=Plectrum(position=position, variation=0.0))
    display(guitar.play(guitar.strum(A, at=0.0, length=2.0)).take(2.5, f"An A chord strummed at position {position}"))
```

Near the bridge the chord is thin and bright; at the middle, where every even harmonic has a still point, it is hollow and soft. Players move their hand along the string for exactly this. The same instrument with one argument changed is another sound, and every instrument in this family can be changed the same way.

## No two notes the same

A real instrument is never perfect, and it never plays two notes the same. Euterpe models both, each in the part that causes it.

- **The instrument's character.** No string is perfectly in tune with the others, and each has its own level and its own losses: an old string rings shorter. A string's `tolerance` says how far each string may be from the ideal: `Tolerance(cents, level, decay)`. Every string part defaults to `Tolerance(3.0, 0.05, 0.1)`: up to 3 cents out of tune either way (chapter 2), up to 5 % louder or softer, and losses up to 10 % larger or smaller, which means the share of the vibration lost on each trip, 1 − damping, moves by up to a tenth of itself. `Tolerance()` with no values is a perfect string. Each string draws its own flaws once, from the instrument's `seed` and the string's number, so the same string has the same flaws on every note, and another seed is another guitar of the same make.
- **The contact.** A finger or a pick never touches the string twice in the same place with the same force. An exciter's `variation`, by default 0.08, moves each pluck's position, brightness and force by up to 8 %, drawn anew for every note from the seed of `play`.

The flaws of the six strings of a guitar with `seed=7`:

```python {run output=code}
from euterpe.instruments import Guitar

guitar = Guitar(seed=7)
for string in range(1, 7):
    cents, level, decay = guitar.traits(string)
    print(f"string {string}: {cents:+.1f} cents, level {level:+.1%}, losses {decay:+.1%}")
```

To hear them, the same phrase plays twice below: the opening of *Romance*, a Spanish guitar piece of the 19th century whose author is unknown, on a classical guitar (nylon strings, played with the fingers), then a strum of a G major chord on the same strings. First with no flaws and no variation, then with the defaults. The melody repeats B4 four times; each beat is split in three, a melody note and then two notes of the chord (B3 and G3) a third of a beat apart, and the bass, E2, sounds on the first and the fourth beat:

```python {run}
from euterpe.instruments import Finger, Guitar, Note, Nylon, Shape, Tolerance
from euterpe.pitch import B3, B4, E2, G3

melody = [B4, B4, B4, B4]
G = Shape(3, 2, 0, 0, 0, 3)

def romance(guitar):
    beat, notes = 0.75, []
    for k, top in enumerate(melody):
        t = k * beat
        notes += [Note(t, top, beat), Note(t + beat / 3, B3, beat * 2 / 3, 0.5), Note(t + beat * 2 / 3, G3, beat / 3, 0.5)]
        if k % 3 == 0:
            notes.append(Note(t, E2, beat * 3, 0.7))
    end = len(melody) * beat + 0.3
    notes += guitar.strum(G, at=end, length=2.5, velocity=0.85)
    return guitar.play(notes, seed=1)

exact = Guitar(string=Nylon(tolerance=Tolerance()), exciter=Finger(variation=0.0), seed=7)
real = Guitar(string=Nylon(), exciter=Finger(), seed=7)
for guitar, name in ((exact, "no flaws, no variation"), (real, "the defaults")):
    display(romance(guitar).take(6.0, f"Four B4s and a G chord: {name}"))
```

Listen first to the repeated B4s. Without variation they are four copies of one sound, the mark of a machine; with it, each is slightly different, as from a hand. Then listen to the G chord, G2 B2 D3 G3 B3 G4. With flaws, the strings are a few cents out of tune with each other. Strings an octave apart, like the G's here, then beat slowly through their harmonics: the second harmonic of G3 is a few cents away from G4, and two close frequencies add up to a sound that swells and fades (chapters 5 and 8). Play it again and it beats the same way, because the strings are the same strings. The timing and loudness of each note stay exactly as written: playing them a little early or late, the way a musician does, is part of performance, which Part IV of the book, after the scores of Part III, will add.

## The guitar

`Guitar` is a `Plucked` with six steel strings tuned E2 A2 D3 G3 B3 E4, 19 frets and a pick. Strings are numbered from the highest-pitched: string 1 is E4 and string 6 is E2. The frets are metal strips across the neck; pressing a string just behind one shortens it, and each fret raises its note by a semitone. The *nut* is the ridge at the end of the neck where the open strings start. A hand position is a *shape*: one fret per string, from string 6 to string 1, `None` where a guitar book writes x. `Shape(None, 0, 2, 2, 2, 0)` is the A chord, x02220. A chord named by a letter alone, such as A, is major (chapter 3); a *minor* one, such as Em, takes 3 and 7 steps above its root instead of 4 and 7. Three methods turn a guitar's way of playing into notes:

- `strum(chord, at, length)` plays every string of a chord, 12 ms apart, from the lowest to the highest (a *down* strum), or from the highest down with `up=True`; `strings=3` plays only the three highest-pitched strings of the chord, as an up-strum often does;
- `pick(string, fret, at, length)` plays one string, as a *tab* (guitar notation by string and fret) writes it;
- `pitches(shape)` gives the pitches a shape plays, and `shape(pitches)` finds a shape for a list of pitches.

Each note a method makes carries its string as its resource (chapter 9), so a string struck again stops the note it was playing. A chord can be written as plain pitches too: the guitar finds a string and fret for each, nearest the nut, all within four frets, as a hand would.

```python {run output=code}
from euterpe.instruments import Guitar, Shape
from euterpe.pitch import A2, Cs4, E3, E4, A3

guitar = Guitar()
print(guitar.pitches(Shape(None, 0, 2, 2, 2, 0)))
print(guitar.shape([A2, E3, A3, Cs4, E4]))
print(Guitar(capo=2).pitches(Shape(None, 0, 2, 2, 2, 0)))
```

A *capo* is a clamp across all strings at one fret: `capo=2` raises every string by two semitones, so the A shape plays a B chord. Here is the guitar's phrase: an E major chord strummed, then a line picked from a tab.

```python {run}
from euterpe.instruments import Guitar, Shape

guitar = Guitar()
notes = guitar.strum(Shape(0, 2, 2, 1, 0, 0), at=0.0, length=1.8, velocity=0.9)
for k, (string, fret) in enumerate([(1, 0), (2, 0), (2, 1), (3, 2), (2, 0), (1, 0), (1, 3), (1, 0)]):
    notes += guitar.pick(string, fret, at=2.0 + 0.3 * k, length=0.3)
display(guitar.play(notes).take(caption="An E major chord strummed, then a picked line"))
```

A plucked string keeps ringing after its note's written length, until it dies, the same string is played again, or the guitar runs out of voices. That is what a guitar does: a player who wants a note short lays a finger on the string. `Staccato()` (chapter 9) does that, and so does `let_ring=False` for every note.

## The bass guitar

`BassGuitar` has four strings tuned E1 A1 D2 G2, an octave below the guitar's lowest four, and is played with the fingers. A low string makes few trips a second: at 41 Hz, its lowest E, a guitar's damping of 0.997 would let each note ring for over a minute, and every note would run into the next. So the bass's string loses 5 % a trip, the finger stops each note at its written end (`let_ring=False`), as bass players do, and the finger varies each pluck by 15 %, more than the default. It is still the least convincing of the four: a real bass string is thick and stiff, so its upper harmonics are slightly sharp, and the finger's thump at the attack carries much of what the ear recognises; `Pluck` has neither.

```python {run echo=false}
# Check the claim above: at damping 0.95 each note of a line stands well above the last one's tail.
import numpy as np

from euterpe.instruments import BassGuitar, Steel
from euterpe.pitch import A1, D2
from euterpe.sound.core import RATE

line = [(0.5 * k, (D2, A1)[k % 2], 0.45) for k in range(8)]
rms = lambda x: np.sqrt(np.mean(x ** 2))


def rise(damping):
    """How many dB the first 50 ms of each note stand above the 50 ms before it, on average."""
    x = np.asarray(BassGuitar(string=Steel(damping=damping)).play(line).take(4.0))
    starts = [round(0.5 * k * RATE) for k in range(1, 8)]
    return np.mean([20 * np.log10(rms(x[s : s + RATE // 20]) / rms(x[s - RATE // 20 : s])) for s in starts])


assert rise(0.95) > 12 and rise(0.998) < 6, (rise(0.95), rise(0.998))
```

Here is a line of *eighths*, notes half a beat long, at a quarter of a second each:

```python {run}
from euterpe.instruments import BassGuitar
from euterpe.pitch import B1, D2, E1, E2, G1, A1

line = [E1, E1, G1, A1, B1, A1, G1, E1, E1, E1, D2, E2]
display(BassGuitar().play([(0.25 * k, pitch, 0.25) for k, pitch in enumerate(line)]).take(caption="A line of eighths on the bass guitar"))
```

## The harp

A concert harp has 47 strings, from C1 to G7, one for each note it plays (its pedals, which retune strings by a semitone, are left out here). `Harp` gives every pitch its own string, so a note rings until it dies or the same note is played again, and it has 16 voices. It is plucked with the fingers near the middle of its gut strings, which makes it soft and round. Its phrase is an arpeggio, a chord played one note at a time, left ringing:

```python {run}
from euterpe.instruments import Harp
from euterpe.pitch import C3, C4, C5, E3, E4, G3, G4

notes = [(0.25 * k, pitch, 0.3) for k, pitch in enumerate([C3, E3, G3, C4, E4, G4, C5])]
display(Harp().play(notes).take(caption="A C major arpeggio on the harp, left ringing"))
```

Each note was written 0.3 s long, and each rings for seconds: a harp's strings are long and gut keeps the vibration. The chord builds up as it goes.

## Strings plucked with the fingers

Violinists and cellists can put down the bow and pluck the strings with a finger: *pizzicato*, Italian for "pinched". The string is short and stopped by a finger, so the note dies in about a second or less, sooner on high notes. `PizzicatoStrings` is a section of players doing it together: each note is played by `players=3` strings, each up to 6 cents sharp or flat, drawn per note, through a violin's body.

```python {run}
from euterpe.instruments import PizzicatoStrings
from euterpe.pitch import B4, D4, D5, G3, G4

figure = [G3, D4, G4, B4, D5, B4, G4, D4]
display(PizzicatoStrings().play([(0.2 * k, pitch, 0.15) for k, pitch in enumerate(figure)]).take(caption="A G major figure, pizzicato"))
```

Three players never pluck exactly in tune, so the section sounds wider than one string. All three pluck at the same instant, which real players never do, and the whole section sounds through one violin's body: those are this model's limits.

## A showcase: Bach on the harp

The harp, alone, plays the first eight bars of Bach's Prelude in C major (1722), BWV 846 in the catalogue of Bach's works. Each bar is one chord of five notes, played as sixteenth notes in the order 1 2 3 4 5 3 4 5, twice (0 1 2 3 4 2 3 4 in the code, which counts from 0). The tempo is 66 beats a minute, so a beat lasts 60 / 66 s and a sixteenth a quarter of that:

```python {run}
from euterpe.instruments import Harp
from euterpe.pitch import A4, A5, B3, C4, C5, D4, D5, E4, E5, F5, Fs4, G4, G5

chords = [[C4, E4, G4, C5, E5], [C4, D4, A4, D5, F5], [B3, D4, G4, D5, F5], [C4, E4, G4, C5, E5],
          [C4, E4, A4, E5, A5], [C4, D4, Fs4, A4, D5], [B3, D4, G4, D5, G5], [B3, C4, E4, G4, C5]]
sixteenth = 60 / 66 / 4
notes = [((16 * bar + 8 * half + k) * sixteenth, chord[i], 1.0, 0.8 if k == 0 else 0.7)
         for bar, chord in enumerate(chords) for half in range(2) for k, i in enumerate([0, 1, 2, 3, 4, 2, 3, 4])]
display(Harp().play(notes).take(caption="Bach, Prelude in C major BWV 846, bars 1 to 8, on the harp"))
```

## Putting it all together

Johann Pachelbel's Canon in D (about 1700) is built to be layered. Its bass, the *ground*, repeats eight notes for the whole piece, one chord per note: D, A, B minor, F♯ minor, G, D, G, A. Each pass adds a part over it. Here the bass guitar plays the ground four times, each note as two eighths; the harp joins on the second pass with an arpeggio of each chord; the plucked strings join on the third with the Canon's famous line, one note per chord; and the guitar strums the chords on the fourth. Everything sounds in one hall, chapter 8's `FDNReverb`. A chord per second, 32 seconds and the hall's tail:

```python {run name=finale}
from euterpe.instruments import BassGuitar, Guitar, Harp, PizzicatoStrings, Shape
from euterpe.pitch import A1, A3, A4, B1, B3, B4, Cs4, Cs5, D2, D4, D5, E4, E5, Fs1, Fs3, Fs4, Fs5, G1, G3
from euterpe.sound import FDNReverb

GROUND = [D2, A1, B1, Fs1, G1, D2, G1, A1]
CHORDS = [(D4, Fs4, A4), (A3, Cs4, E4), (B3, D4, Fs4), (Fs3, A3, Cs4), (G3, B3, D4), (D4, Fs4, A4), (G3, B3, D4), (A3, Cs4, E4)]
SHAPES = [Shape(None, None, 0, 2, 3, 2), Shape(None, 0, 2, 2, 2, 0), Shape(None, 2, 4, 4, 3, 2), Shape(2, 4, 4, 2, 2, 2),
          Shape(3, 2, 0, 0, 0, 3), Shape(None, None, 0, 2, 3, 2), Shape(3, 2, 0, 0, 0, 3), Shape(None, 0, 2, 2, 2, 0)]
LINE = [Fs5, E5, D5, Cs5, B4, A4, B4, Cs5]

bass = [(8 * p + i + 0.5 * h, pitch, 0.45) for p in range(4) for i, pitch in enumerate(GROUND) for h in (0, 1)]
arps = [(8 * p + i + 0.25 * k, pitch, 1.0, 0.6) for p in (1, 2, 3) for i, chord in enumerate(CHORDS)
        for k, pitch in enumerate(chord + (chord[0] + 12,))]
line = [(8 * p + i, pitch, 0.9) for p in (2, 3) for i, pitch in enumerate(LINE)]
guitar = Guitar()
strums = [n for i, shape in enumerate(SHAPES) for n in guitar.strum(shape, at=24 + i, length=1.0, velocity=0.6)]
band = BassGuitar().play(bass) + Harp().play(arps) + PizzicatoStrings().play(line) + guitar.play(strums)
song = FDNReverb(band, decay=2.2, size=0.9, mix=0.25)
song.take(35.0, "Pachelbel's Canon for plucked quartet: bass, harp, pizzicato and guitar")
```

`chord + (chord[0] + 12,)` adds the chord's root an octave up, so each arpeggio climbs four notes. Four plucked instruments, one model with three parts. Plug the same `Guitar` into chapter 8's `Saturator` and it starts to sound electric, but not quite like an electric guitar: that instrument has no wooden body, a pickup instead, and an amplifier that is part of its sound. Chapter 11 builds it.

## Summary

- `Plucked(exciter, string, body)` is a plucked string built from parts: `Finger` or `Plectrum` (position, brightness, variation), `Steel`, `Nylon` or `Gut` (damping, tolerance), and a body. A harder note starts brighter.
- `Body(src, freqs, decays, amps, dry)` is a wooden body as a few band-pass modes driven by the string; a bigger body has lower modes.
- Variation belongs to the instrument: a string's `Tolerance` gives each string fixed flaws drawn from the instrument's `seed`; an exciter's `variation` makes each pluck different.
- `Guitar` and `BassGuitar` play `Shape`s, tabs (`pick`) and plain pitches; each note carries its string. `Harp` has a string per pitch; `PizzicatoStrings` is a slightly detuned section.
- A plucked string rings past its written length until it dies, is struck again or is stolen; `Staccato` or `let_ring=False` mutes it.

## Exercises

1. In the finale, change the hall's `decay=2.2` to `decay=6.0` and `mix=0.25` to `mix=0.5`. What happens to the harp's arpeggios and the guitar's strums when the chord changes?
2. In the flaws block, change `Guitar(seed=7)` to `Guitar(seed=8)`. Do the flaws of string 1 change? Run the block twice with `seed=7`: do they?
3. In the bass line block, replace `BassGuitar()` with `BassGuitar(string=Steel(damping=0.998))` and add `Steel` to the import. What happens to the line, and why?

### Answers

1. The tail of each chord now rings for seconds into the next one, so when D changes to A, the D's notes still sound under the A's, and the arpeggios blur into a wash. Some notes clash for a moment (D against C♯, F♯ against E) before the old chord fades; that is why a player in a big church plays slower.
2. With `seed=8` every string draws new flaws, so string 1 changes: it is another guitar of the same make. Run twice with `seed=7`, the flaws are the same both times, because they are drawn from the seed and the string's number, not anew.
3. Each note now keeps 99.8 % of its vibration on each trip, so at these low frequencies it rings for over a minute and is still almost as loud as at its start when the next note comes. The finger still stops each note at its written end, but the notes run into each other and the line loses its edges.

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
