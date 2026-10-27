# Plucked strings

Chapter 7 built a plucked string, `Pluck`: a burst of noise circulating in a delay line, losing its high harmonics first. On its own it sounds like a bare wire. A guitar, a harp or a bass is more than its string: something plucks it, a finger or a pick, and the string sounds through a wooden body that colours it. This chapter builds the plucked family from those three parts, then plays four instruments made from them: the guitar, the bass guitar, the harp and a section of strings plucked with the fingers.

## Words for strings and rhythm

A few words of the guitarist and of rhythm come up all through the chapter. A guitar's strings are numbered from the highest-pitched: string 1 is the thinnest, string 6 the thickest. A string played without pressing it is *open*. The neck carries *frets*, metal strips across it; pressing a string just behind a fret shortens it, and each fret raises its note by a semitone. The *nut* is the ridge at the end of the neck where the open strings start. A hand position is written with one fret per string, from string 6 to string 1, x for a string not played: x02220 is the A chord. A *strum* sweeps a pick across the strings: *down* goes from the lowest-pitched string to the highest, *up* the other way. A chord named by a letter alone, such as G or E, is *major*: its root, then the notes 4 and 7 semitones up (chapter 6). A *minor* chord, written Em, takes 3 and 7 instead. In rhythm, a *bar* groups a fixed number of beats (chapter 9); an *eighth* note lasts half a beat and a *sixteenth* a quarter of one.

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

The note is A2, 110 Hz, the note of the guitar's fifth string played open. The bare string is thin and buzzing; through the body it sounds fuller and rounder, and that is the difference between a wire and an instrument.

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

Chapter 7 showed what the pluck point does: plucking at 1/n of the string's length removes every n-th harmonic. A finger is soft and plucks away from the bridge; a pick is hard and plucks near it. Here is one strummed A chord, x02220, with a pick near the bridge, at `position=0.06`, and the same chord at the middle of the string, `position=0.5`. `Shape` and `strum` are the guitar's, and the section on the guitar explains them; `variation=0.0` keeps every pluck exactly at its position (the section after this one explains variation):

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

- **The instrument's character.** No string is perfectly in tune with the others, and each has its own level and its own losses: an old string rings shorter. A string's `tolerance` says how far each string may be from the ideal: `Tolerance(cents, level, decay)`. Every string part defaults to `Tolerance(3.0, 0.05, 0.1)`: up to 3 cents out of tune either way (chapter 2: a cent is a hundredth of a semitone), up to 5 % louder or softer, and losses up to 10 % larger or smaller, which means the share of the vibration lost on each trip, 1 − damping, moves by up to a tenth of itself. `Tolerance()` with no values is a perfect string. Each string draws its own flaws once, from the instrument's `seed` and the string's number, so the same string has the same flaws on every note, and another seed is another guitar of the same make.
- **The contact.** A finger or a pick never touches the string twice in the same place with the same force. An exciter's `variation`, by default 0.08, moves each pluck's position, brightness and force by up to 8 %, drawn anew for every note from the seed of `play`.

The flaws of the six strings of a guitar with `seed=7`:

```python {run output=code}
from euterpe.instruments import Guitar

guitar = Guitar(seed=7)
for string in range(1, 7):
    cents, level, decay = guitar.traits(string)
    print(f"string {string}: {cents:+.1f} cents, level {level:+.1%}, losses {decay:+.1%}")
```

To hear them, the same phrase plays three times below: the first four bars of *Romance*, a Spanish guitar piece of the 19th century whose author is unknown, on a classical guitar (nylon strings, played with the fingers), then two strums of a G chord on the same strings. First with no flaws and no variation, then with the defaults, then with both about four times larger. The piece is in bars of three beats; each beat is split in three, a melody note and then two notes of the chord (B3 and G3) a third of a beat apart, and the bass, E2, sounds on the first beat of each bar:

```python {run}
from euterpe.instruments import Finger, Guitar, Note, Nylon, Shape, Tolerance
from euterpe.pitch import A4, B3, B4, E2, E4, Fs4, G3, G4

melody = [B4, B4, B4, B4, A4, G4, G4, Fs4, E4, E4, G4, B4]
G = Shape(3, 2, 0, 0, 0, 3)

def romance(guitar):
    beat, notes = 0.75, []
    for k, top in enumerate(melody):
        t = k * beat
        notes += [Note(t, top, beat), Note(t + beat / 3, B3, beat * 2 / 3, 0.5), Note(t + beat * 2 / 3, G3, beat / 3, 0.5)]
        if k % 3 == 0:
            notes.append(Note(t, E2, beat * 3, 0.7))
    end = len(melody) * beat + 0.3
    notes += guitar.strum(G, at=end, length=2.5, velocity=0.85) + guitar.strum(G, at=end + 3.0, length=3.0, velocity=0.85)
    return guitar.play(notes, seed=1)

exact = Guitar(string=Nylon(tolerance=Tolerance()), exciter=Finger(variation=0.0), seed=7)
real = Guitar(string=Nylon(), exciter=Finger(), seed=7)
loose = Guitar(string=Nylon(tolerance=Tolerance(12.0, 0.2, 0.4)), exciter=Finger(variation=0.3), seed=7)
for guitar, name in ((exact, "no flaws, no variation"), (real, "the defaults"), (loose, "four times the defaults")):
    display(romance(guitar).take(18.0, f"Romance, then two G chords: {name}"))
```

Listen first to the repeated B4s at the start. Without variation they are four copies of one sound, the mark of a machine; with it, each is slightly different, as from a hand. Then listen to the G chords, G2 B2 D3 G3 B3 G4. With flaws, the strings are a few cents out of tune with each other. Strings an octave apart, like the G's here, then beat slowly through their harmonics: the second harmonic of G3 is a few cents away from G4, and two close frequencies add up to a sound that swells and fades (chapter 3). The second strum beats the same way as the first, because the strings are the same strings. At four times the defaults the guitar is out of tune and the player clumsy. The timing and loudness of each note stay exactly as written: playing them a little early or late, the way a musician does, is part of performance, which Part IV of the book, after the scores of Part III, will add.

## The guitar

`Guitar` is a `Plucked` with six steel strings tuned E2 A2 D3 G3 B3 E4, 19 frets and a pick. String 1 is E4 and string 6 is E2. A hand position is a *shape*: one fret per string, from string 6 to string 1, `None` where a guitar book writes x. `Shape(None, 0, 2, 2, 2, 0)` is the A chord, x02220. Three methods turn a guitar's way of playing into notes:

- `strum(chord, at, length)` plays every string of a chord, 12 ms apart, from the lowest to the highest, or from the highest down with `up=True`; `strings=3` plays only the three highest-pitched strings of the chord, as an up-strum often does;
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

`BassGuitar` has four strings tuned E1 A1 D2 G2, an octave below the guitar's lowest four, and is played with the fingers. It was the hardest instrument of this chapter to make, and its first version shows why. Its string kept 99.8 % of its vibration on each trip, close to a guitar's 99.7 %. But a low string makes few trips a second: at 41 Hz, the bass's lowest E, 0.998 to the power 41 a second takes about 80 s to fall 60 dB, counting the trip losses alone. Each note was still almost as loud as at its start when the next one came, so one note ran into the next and the ear could hardly tell them apart. The block measures it on a line of two notes a beat apart: how many dB the first 50 ms of each note stand above the 50 ms before it.

```python {run output=code}
import numpy as np

from euterpe.instruments import BassGuitar, Steel
from euterpe.pitch import A1, D2
from euterpe.sound.core import RATE

line = [(0.5 * k, (D2, A1)[k % 2], 0.45) for k in range(8)]
for damping in (0.998, 0.95):
    x = np.asarray(BassGuitar(string=Steel(damping=damping)).play(line).take(4.0))
    rise = []
    for k in range(1, 8):
        s = round(0.5 * k * RATE)
        after, before = (np.sqrt(np.mean(x[a:b] ** 2)) for a, b in ((s, s + RATE // 20), (s - RATE // 20, s)))
        rise.append(20 * np.log10(after / before))
    print(f"damping {damping}: each note starts {np.mean(rise):.1f} dB above the one before")
```

At 0.998 a new note rises only 4.6 dB above the end of the last one, and that is with the finger stopping each note at its end. At 0.95 each note falls quickly after its attack, as a plucked bass string does, and rises 16.9 dB above the last. The bass also lets the finger stop each note at its written end (`let_ring=False`), as bass players do, and its finger varies each pluck by 15 %, more than the default. It is still the least convincing of the four. The model's limits are clearest here: a real bass string is thick and stiff, so its upper harmonics are slightly sharp, and the finger's thump at the attack carries much of what the ear recognises; `Pluck` has neither. On small speakers, which cannot play 41 Hz, the fundamental is lost too, and the ear has only the harmonics to find the note.

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

## Showcases

Each instrument plays a short piece that most listeners know, all of them old enough to be free to use.

The harp plays the first eight bars of Bach's Prelude in C major (1722), BWV 846 in the catalogue of Bach's works. Each bar is one chord of five notes, played as sixteenth notes in the order 1 2 3 4 5 3 4 5, twice (0 1 2 3 4 2 3 4 in the code, which counts from 0). The tempo is 66 beats a minute, so a beat lasts 60 / 66 s and a sixteenth a quarter of that:

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

The guitar plays eight bars of the *Romance* of the variation section, then strums the chords G, D, E minor and C, the four chords of countless songs. Each bar of the strumming is eight eighths of 0.3 s, struck down on eighths 0 and 2, up on 3 and 5, down on 6 and up on 7:

```python {run}
from euterpe.instruments import Finger, Guitar, Note, Nylon, Shape
from euterpe.pitch import A2, A3, A4, B3, B4, C4, C5, D5, E2, E4, E5, Fs4, G3, G4

melody = [B4, B4, B4, B4, A4, G4, G4, Fs4, E4, E4, G4, B4, E5, E5, E5, E5, D5, C5, C5, B4, A4, A4, B4, C5]
beat, notes = 0.75, []
for k, top in enumerate(melody):
    t, inner, bass = k * beat, (B3, G3) if k < 18 else (C4, A3), E2 if k < 18 else A2
    notes += [Note(t, top, beat), Note(t + beat / 3, inner[0], beat * 2 / 3, 0.5), Note(t + beat * 2 / 3, inner[1], beat / 3, 0.5)]
    if k % 3 == 0:
        notes.append(Note(t, bass, beat * 3, 0.7))
romance = Guitar(string=Nylon(), exciter=Finger()).play(notes)

guitar, start, eighth = Guitar(), len(melody) * beat + 0.8, 0.3
pattern = [(0, False), (2, False), (3, True), (5, True), (6, False), (7, True)]
strums = []
for bar, shape in enumerate([Shape(3, 2, 0, 0, 0, 3), Shape(None, None, 0, 2, 3, 2), Shape(0, 2, 2, 0, 0, 0), Shape(None, 3, 2, 0, 1, 0)]):
    for j, (slot, up) in enumerate(pattern):
        length = ((pattern[j + 1][0] if j + 1 < len(pattern) else 8) - slot) * eighth
        strums += guitar.strum(shape, at=start + (8 * bar + slot) * eighth, length=length, up=up,
                               strings=3 if up else None, velocity=0.55 if up else 0.85)
strums += guitar.strum(Shape(3, 2, 0, 0, 0, 3), at=start + 32 * eighth, length=2.5, velocity=0.9)
display((romance + guitar.play(strums)).take(31.0, "Romance fingerpicked, then G, D, Em and C strummed"))
```

The bass guitar plays the bass line of Pachelbel's Canon in D (about 1700), eight notes that repeat under the whole piece, each as two eighths:

```python {run}
from euterpe.instruments import BassGuitar
from euterpe.pitch import A1, B1, D2, Fs1, G1

canon = [D2, A1, B1, Fs1, G1, D2, G1, A1]
notes = [((8 * rep + i) + 0.5 * half, pitch, 0.45, 0.85 if half == 0 else 0.7)
         for rep in range(3) for i, pitch in enumerate(canon) for half in range(2)]
display(BassGuitar().play(notes).take(caption="Pachelbel, Canon in D, the bass line three times"))
```

The pizzicato strings play the opening of Mozart's *Eine kleine Nachtmusik* (1787), three times, over a bass that alternates two notes:

```python {run}
from euterpe.instruments import PizzicatoStrings
from euterpe.pitch import A2, A4, B4, C5, D3, D4, D5, Fs3, Fs4, G2, G4

q, e = 0.42, 0.21  # a quarter note (one beat) and an eighth, in seconds
bars = [[(0, G4, q), (1.5 * q, D4, e), (2 * q, G4, q), (3.5 * q, D4, e)],
        [(0, G4, e), (e, D4, e), (2 * e, G4, e), (3 * e, B4, e), (4 * e, D5, 2 * q)],
        [(0, C5, q), (1.5 * q, A4, e), (2 * q, C5, q), (3.5 * q, A4, e)],
        [(0, C5, e), (e, A4, e), (2 * e, Fs4, e), (3 * e, A4, e), (4 * e, D4, 2 * q)]]
basses = [(G2, D3), (G2, D3), (D3, Fs3), (D3, A2)]
notes = []
for rep in range(3):
    for b, bar in enumerate(bars):
        t0 = (4 * rep + b) * 4 * q
        notes += [(t0 + t, pitch, length) for t, pitch, length in bar]
        notes += [(t0 + k * q, basses[b][k % 2], e) for k in range(4)]
notes += [(48 * q, G2, 0.5), (48 * q, G4, 0.5)]
display(PizzicatoStrings().play(notes).take(caption="Mozart, Eine kleine Nachtmusik, the opening, pizzicato"))
```

## Summary

- `Plucked(exciter, string, body)` is a plucked string built from parts: `Finger` or `Plectrum` (position, brightness, variation), `Steel`, `Nylon` or `Gut` (damping, tolerance), and a body. A harder note starts brighter.
- `Body(src, freqs, decays, amps, dry)` is a wooden body as a few band-pass modes driven by the string; a bigger body has lower modes.
- Variation belongs to the instrument: a string's `Tolerance` gives each string fixed flaws drawn from the instrument's `seed`; an exciter's `variation` makes each pluck different.
- `Guitar` and `BassGuitar` play `Shape`s, tabs (`pick`) and plain pitches; each note carries its string. `Harp` has a string per pitch; `PizzicatoStrings` is a slightly detuned section.
- A plucked string rings past its written length until it dies, is struck again or is stolen; `Staccato` or `let_ring=False` mutes it.

## Exercises

1. In the exciter block, change `position=0.5` to `position=0.25`. Which harmonics of the open A string (110 Hz) does the pluck now remove, and at what frequencies are the first two?
2. In the flaws block, change `Guitar(seed=7)` to `Guitar(seed=8)`. Do the flaws of string 1 change? Run the block twice with `seed=7`: do they?
3. In the bass block, add a third damping to the loop, `0.9`. Does each note stand out more or less than at 0.95, and why?

### Answers

1. Plucking at a quarter of the string (the block sets `variation=0.0`, so it is exactly a quarter) removes every harmonic with a still point there: the 4th, 8th, 12th and so on. The first two are at 4 × 110 = 440 Hz and 8 × 110 = 880 Hz.
2. With `seed=8` every string draws new flaws, so string 1 changes: it is another guitar of the same make. Run twice with `seed=7`, the flaws are the same both times, because they are drawn from the seed and the string's number, not anew.
3. More: at 0.9 each trip keeps 90 % of the vibration, so the note dies faster after its attack, and the level just before the next note is lower. The bass sounds shorter and drier, closer to a muted string.

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
