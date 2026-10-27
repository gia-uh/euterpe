# Anatomy of an instrument

Part I built sounds: a sine, a filter, a plucked string, each a unit that makes one sound when it is rendered. Music needs many sounds, one after another and on top of each other, each with its own pitch, start, length and loudness. An *instrument* is the object that turns that list into sound. It knows how one note sounds, how many notes it can play at once, what happens when a new note arrives while others still ring, and which notes it cannot play at all. This chapter builds one by hand from a sine and an envelope, then looks at each of those jobs in turn.

## Pitches and notes

Chapter 2 tuned the twelve notes of an octave in equal steps, each 2^(1/12) times the one below, with A4 at 440 Hz. `euterpe.pitch` has one constant per note, from `A0` to `C8`. A sharp is written with an `s` (`Cs4` is C♯4) and a flat with a `b` (`Db4` is D♭4); in equal steps they are the same note, so `Cs4` and `Db4` are the same object. Adding a number moves a pitch by that many semitones, and subtracting two pitches gives the distance between them:

```python {run output=code}
from euterpe.pitch import A4, C4, Cs4, Db4, E5

print(A4.freq, (A4 + 12).freq, round(C4.freq, 2))
print(A4 + 7, E5 - A4, Cs4 == Db4)
```

A4 is 440 Hz and the A an octave up, 12 semitones higher, is 880. Seven semitones up from A4 is E5, the fifth of chapter 2. The numbers behind the names are the MIDI numbers that synthesizers use, 60 for C4 and 69 for A4, so a pitch is a whole number of semitones and its frequency is 440 × 2^((number − 69) / 12).

A *note* is a pitch with a time: when it starts, in seconds; how long it is held, in seconds; and how hard it is played, its *velocity*, from 0 to 1. The short way to write one is a tuple, `(time, pitch, duration)` or `(time, pitch, duration, velocity)`; velocity defaults to 0.8. A pitch can also be a frequency in Hz, for a note between the twelve steps. Rhythm, in bars and beats, comes in Part III; until then a melody is a list of times in seconds.

## An instrument by hand

An instrument is a class with one method, `voice(note)`, which returns the unit that sounds one note. A *theremin* is an electronic instrument from 1920, played without touching it: one hand moves the pitch, the other the volume, and its tone is close to a pure sine with a slight wobble. The class below gives it three things. `polyphony = 1`, because it plays one note at a time. `playable = (C4, C7)`, the range it can reach, and `comfortable = (C4, C6)`, the part of it where it plays well (the end of the chapter uses both). And a voice: a sine whose frequency moves 1 % up and down five times a second (the *vibrato*, chapter 6's slow modulation), shaped by an `ADSR` (chapter 4) that rises in 0.15 s, holds while the note is held, and fades over 0.4 s after it.

```python {run}
from euterpe.instruments import Instrument
from euterpe.pitch import A4, C4, C6, C7
from euterpe.sound import ADSR, Sine


class Theremin(Instrument):
    polyphony = 1
    playable = (C4, C7)
    comfortable = (C4, C6)

    def __init__(self, vibrato: float = 5.0):
        self.vibrato = vibrato

    def voice(self, note):
        pitch = note.freq * (Sine(self.vibrato) * 0.01 + 1.0)
        return Sine(pitch) * ADSR(attack=0.15, release=0.4, gate=note.duration) * note.velocity * 0.5


display(Theremin().note(A4, 2.0).take(caption="A theremin plays A4 for 2 s"))
```

`note.freq` is the note's frequency in Hz and `note.velocity` its velocity, and `voice` builds a fresh graph of units from them for every note. `note(A4, 2.0)` plays one note at time 0, held 2 s. It returns a unit, like any unit of Part I, so `take` renders it and draws it. Without a length, `take` renders until the sound ends: 2 s of note and 0.4 s of release.

`play` takes a whole list. These are the first four bars of the *Ode to Joy* from Beethoven's Ninth Symphony, a quarter note every half second, each held 0.45 s:

```python {run continue}
from euterpe.pitch import C4, D4, E4, F4, G4

ode = [E4, E4, F4, G4, G4, F4, E4, D4, C4, C4, D4, E4, E4, D4, D4]
lengths = [1] * 12 + [1.5, 0.5, 2]
notes, t = [], 0.0
for pitch, beats in zip(ode, lengths):
    notes.append((t, pitch, 0.45 * beats))
    t += 0.5 * beats

melody = Theremin().play(notes)
display(melody.take(caption="The Ode to Joy on the theremin, every note started again"))
```

The result of `play` is a `Phrase`: one unit that starts each note's voice at its time and adds them up. It is a unit like a `Sine`, so the effects of chapter 8 take it as their source.

## Voices

Each note that sounds needs its own copy of the voice: its own sine, its own envelope, its own place in time. A copy that is sounding is a *voice*, and `polyphony` is how many voices the instrument has. A piano can sound all 88 strings at once; a flute, a trumpet or a voice sings one note at a time. When a note arrives and all the voices are busy, one has to stop. The `Phrase` stops the oldest, and it does not cut it: a cut drops the wave from wherever it is to 0 between two samples, and chapter 4 showed that such a step is heard as a click. The stopped voice fades out over 5 ms, 240 samples, instead.

The instrument below is the theremin with three voices. `starts` and `stops` say, in samples, when each voice of a phrase starts and stops. A C major chord, C4, E4 and G4, each held 2 s, starts one note every 0.1 s, and a fourth note, C5, arrives at 0.3 s:

```python {run continue output=code}
from euterpe.pitch import C5, E4, G4
from euterpe.sound.core import RATE


class Trio(Theremin):
    polyphony = 3


phrase = Trio().play([(0.0, C4, 2.0), (0.1, E4, 2.0), (0.2, G4, 2.0), (0.3, C5, 2.0)])
for note, start, stop in zip(phrase.notes, phrase.starts, phrase.stops):
    print(f"{note.pitch!r:4} sounds from {start / RATE:.3f} s to {stop / RATE:.3f} s")
```

C4, the oldest, stops at 0.305 s: the 0.3 s at which C5 arrives, plus the 5 ms fade. The others ring their full 2 s plus the 0.4 s release. A note that is stolen too early is a sign that the music asks more voices of the instrument than it has; the range rules at the end of the chapter warn about it before anything is rendered.

### Resources

A guitar has six strings, so it plays at most six notes, but that is not the whole rule. Each note sounds on one string, and a string plays one note at a time: a new note on a string that is ringing stops the old one, even when five strings are free. The note's *resource* is the part of the instrument that sounds it, a string, a key or a drum head, and `Note(time, pitch, duration, velocity, resource=...)` names it. The `Phrase` stops a voice when a new note takes its resource, before it counts voices.

`PluckedString` is chapter 7's `Pluck` as an instrument, with six voices. Below, two notes are played on string 1 and one on string 2:

```python {run continue output=code}
from euterpe.instruments import Note, PluckedString
from euterpe.pitch import E4, G4, B3
from euterpe.sound.core import RATE

guitar = PluckedString()
phrase = guitar.play([Note(0.0, E4, 1.0, resource=1), Note(0.0, B3, 1.0, resource=2), Note(0.5, G4, 1.0, resource=1)])
for note, stop in zip(phrase.notes, phrase.stops):
    print(f"{note.pitch!r:3} on string {note.resource}: stops at {stop / RATE:.3f} s")
```

E4 stops at 0.505 s, when G4 takes string 1, although the instrument had four voices free. B3 rings its whole second on its own string, and then `PluckedString`'s finger mutes it in 0.08 s, at 1.080 s. Chapter 10's guitar fills in the strings itself, from chord shapes or from plain pitches.

### Slurs

On an instrument with one voice there is a third case. A singer or a violinist can move from one note to the next without starting again: the sound goes on and only the pitch changes. Musicians call it a *slur*. On an instrument with `polyphony = 1`, a note that starts before the previous one has ended is slurred: the `Phrase` builds one voice for the whole run, and `note.freq` is no longer a number but a unit that steps from pitch to pitch with a glide of 20 ms. The theremin's voice multiplies `note.freq` by its vibrato either way, so it slurs without a change. The same *Ode to Joy*, with each note held 0.05 s longer than the gap to the next:

```python {run continue}
legato = [(time, pitch, 0.5 * beats + 0.05) for (time, pitch, _), beats in zip(notes, lengths)]
display(Theremin().play(legato).take(caption="The same melody slurred: one voice, gliding from note to note"))
```

The whole melody is one voice now, with one attack at the start. The spectrogram shows the difference: above, every note starts again from silence; below, the line of the melody is unbroken.

```python {run continue echo=false}
from euterpe.view import spectrogram

spectrogram(melody.take(), Theremin().play(legato).take(), labels=["started again", "slurred"], lo=200, hi=1000,
            caption="Each note started again, and the same notes slurred into one voice")
```

### Articulations

How a note is played, beyond its pitch and length, is its *articulation*. `Note` takes one as its fifth argument. Three are generic, and act on the note before the voice sees it: `Staccato()` holds the note for half its length, detached from the next; `Accent()` plays it 1.3 times as hard, up to 1; `Legato()` slurs it into the note before, even with no overlap. Any articulation applies to any instrument. A family of instruments adds its own, which act on its parts: a plucked string muted by the finger, a bowed string plucked instead.

```python {run continue}
from euterpe.instruments import Accent, Note, Staccato

marked = [Note(t, p, d, 0.6, Staccato() if i % 2 else Accent()) for i, (t, p, d) in enumerate(notes)]
display(Theremin().play(marked).take(caption="The melody with every other note staccato and the rest accented"))
```

## Ranges and lint

A real instrument cannot play every note. A theremin reaches from about C4 to C7; a flute starts at C4; a guitar's lowest note is its lowest open string. `playable` is the range the instrument can reach at all, and `comfortable` the part of it where it plays well. Outside `playable`, `play` warns. `lint_notes`, from `euterpe.lint`, checks a phrase's notes against its instrument before anything is rendered, with three rules:

- **R-PLAYABLE**, an error, for each note outside `playable`, named by its number and time.
- **R-COMFORT**, the share of note time outside `comfortable`, and a warning above a quarter.
- **R-POLYPHONY**, a warning when more notes are written to sound at once than the instrument has voices.

The theremin's comfortable range ends at C6. The block plays three notes on it; the last is B7, above the top of its range, and the block catches the warning to print it:

```python {run continue output=code}
import warnings

from euterpe.lint import lint_notes
from euterpe.pitch import B7, D6

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    phrase = Theremin().play([(0.0, A4, 1.0), (1.0, D6, 1.0), (2.0, B7, 0.5)])
print("play warns:", caught[0].message)
print(lint_notes(phrase).to_text())
```

D6 is playable but above C6, so of the 2.5 s of notes, 1.5 s lie outside the comfortable range: 60 %, more than a quarter. `euterpe lint piece.py:fn` runs the same rules first when `fn` returns a phrase, then the audio rules of Part I on what it renders, and exits with 1 on an error. An agent writing music hears about the impossible note before anyone listens to it.

## Summary

- `euterpe.pitch` has the notes from `A0` to `C8`, `Cs4` for C♯4 and `Db4` for D♭4; `+` and `-` count semitones, and `.freq` is the frequency in equal steps with A4 at 440 Hz.
- A note is `(time, pitch, duration, velocity)` in seconds, or a `Note`, which can also carry an articulation and a resource.
- An instrument is a class with `voice(note)`, which returns the unit for one note, and `polyphony`, `playable` and `comfortable`. `play(notes)` returns a `Phrase`, a unit; `note(pitch, duration)` plays one note.
- A new note on a busy resource stops the old note there; past the polyphony the oldest voice stops; a stopped voice fades over 5 ms. With one voice, overlapping notes slur.
- `lint_notes` checks a phrase against its instrument's ranges and voices before it renders.

## Exercises

1. Make the theremin's vibrato wider: change `0.01` to `0.03` in its voice. How many cents up and down does the pitch now move?
2. In the chord block, change `polyphony = 3` to `polyphony = 2`. Which notes stop, and when?
3. In the slurred *Ode to Joy*, change `+ 0.05` to `- 0.05`. Why does the melody start every note again?

### Answers

1. The frequency moves between 0.97 and 1.03 times the note's. In cents (chapter 2), 1200 × log₂(1.03) = 51 cents up and 1200 × log₂(0.97) = −53 cents down: about a quarter of a tone each way, where 0.01 gave 17 cents. It sounds like a wide, nervous vibrato.
2. With two voices, the third note, G4 at 0.2 s, stops the oldest, C4, at 0.205 s. Then C5 at 0.3 s stops the oldest left, E4, at 0.305 s. G4 and C5 ring to the end.
3. Each note now ends 0.05 s before the next starts, so no two notes overlap, and a note that starts after the previous one has ended is a new note. The theremin starts each one again with its 0.15 s attack.

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
