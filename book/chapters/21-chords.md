# Chords

Chapter 20 put strings under the Largo and copied their notes from the score without a word about them. Those notes sound together, and three or more notes that sound together are a *chord*. Here is where this chapter ends up: one chord on each beat, nothing else, at a pace slow enough to name each one:

```python {run echo=false}
# The teaser: bars 1 and 2 of the finale, built by this chapter's two named blocks, read from this file.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import render

text = Path("chapters/21-chords.md").read_text()
scope = {}
for name in ("prelude", "largo"):
    code = re.search(rf"```python \{{[^}}\n]*name={name}\b[^}}\n]*\}}\n(.*?)\n```", text, re.S).group(1)
    exec("\n".join(line for line in code.split("\n") if "listen(" not in line and "display(" not in line), scope)
samples = render(scope["song"], 2 * 4 * 60 / 52)
display(Clip(samples, caption="Chopin, Prelude in C minor: its first two bars"))
```

Chopin's Prelude in C minor, Op. 28 No. 20, published in 1839. It has no tune that lives apart from its chords, so all you hear is what this chapter is about: how notes stack, how a stack gets a name, and what changes when the same notes are spaced another way.

## Stacking thirds

Chapter 17 measured the distance between two notes. Take a note, skip a letter, take the next, skip a letter and take the next: C, E, G. Each step is a third, so the stack is two thirds high, and three notes stacked this way make a *triad*. `Chord` holds one. Its bottom note in this stack is its *root*, here C, and the other two are named by their distance from it, the *third* and the *fifth*. `tones` gives the names with no octave, and `pitches` places them:

```python {run output=code}
from euterpe import Chord, Interval

c = Chord("C")
print(c.root, c.tones)
print(c.pitches())
print([Interval.between(c.pitches()[i], c.pitches()[i + 1]).pretty for i in range(2)])
```

A third comes in two sizes, major and minor, 4 and 3 semitones, and two of them can be stacked in four ways. Those are the four *qualities* of a triad. The text `Chord` reads is a *chord symbol*: a root, then a quality, with nothing for major, `m` for minor, `dim` for *diminished* and `aug` for *augmented*. The keyboards show the four on one root, and chapter 12's electric piano plays them in that order, through `chords`, which chapter 18 fed with numerals and which takes symbols too:

```python {run}
from euterpe import Chord, Meter, Score, chords, display
from euterpe.instruments import ElectricPiano

for name, stack in (("C", "major then minor third"), ("Cm", "minor then major"),
                    ("Cdim", "minor then minor"), ("Caug", "major then major")):
    display(Chord(name).keyboard(caption=f"{name}: {stack}"))
s = Score(meter=Meter("4/4"), tempo=60)
s.part("keys", ElectricPiano()).add(chords("C:h Cm | Cdim Caug", voicing="root"))
display(s, caption="C, Cm, Cdim and Caug, two beats each")
```

Major is the bright one, and minor differs from it by one semitone in one note, E♭ for E, the same semitone chapter 18 heard between its scales. Both have a perfect fifth from root to top. The other two do not: `Cdim` closes it by a semitone to the tritone of chapter 17, and `Caug` opens it by a semitone. Those two do not sound settled, and music rarely stops on them. `voicing="root"` keeps the root at the bottom of each, and the section called A progression explains it.

## What a chord does to the spectrum

Chapter 17 explained a smooth interval by its partials: two notes sound smooth when their low partials meet. A triad holds three intervals at once. So here are the saws of a C triad, one lane for each note, with E4 for major and E♭4 for minor. Partials that stand in line from one lane to another are partials that meet:

```python {run}
from euterpe.pitch import C4, E4, Eb4, G4
from euterpe.sound import Saw
from euterpe.view import spectrum

notes = (C4, E4, Eb4, G4)
spectrum(*((Saw(note.freq) * 0.5).take(1.0) for note in notes), f0=[note.freq for note in notes], harmonics=8,
         upto=2200.0, labels=["C4", "E4, in major", "E♭4, in minor", "G4"],
         caption="The partials of the notes of C major and C minor")
```

In both, the 3rd partial of C meets the 2nd of G near 785 Hz: that is the fifth, and they share it. The difference is the third. In the major triad the 5th partial of C, 5 × 261.6 = 1308 Hz, lies 10 Hz from the 4th of E, 4 × 329.6 = 1318 Hz. In the minor triad the third's first such meeting is higher up, the 5th of E♭, 5 × 311.1 = 1556 Hz, next to the 6th of C, 1570 Hz.

In just tuning those near misses close exactly. The major triad's three notes are then in the ratio 4 : 5 : 6, so they are partials 4, 5 and 6 of one note two octaves below C. The minor triad is 10 : 12 : 15, and its common note, 26 Hz, is too low to hear as a pitch. That is one account of why major sounds plainer and minor sounds darker. The other is habit, as chapter 18 said of the tonic.

## Sevenths

One more third on top gives a *seventh chord*, four notes, named after the distance from root to top. Five of them matter, and each suffix below names one. `maj7` is a major triad with a major seventh, and plain `7` is a major triad with a minor seventh. `m7` is a minor triad with a minor seventh. `m7b5` lowers that chord's fifth, and `dim7` stacks minor thirds all the way up. Here they are on chapter 12's organ, which holds its notes so that you can hear all four:

```python {run}
from euterpe import Chord, Meter, Score, chords, display
from euterpe.instruments import Organ

for name in ("Cmaj7", "C7", "Cm7", "Cm7b5", "Cdim7"):
    print(name, Chord(name).tones)
s = Score(meter=Meter("4/4"), tempo=60)
s.part("organ", Organ()).add(chords("Cmaj7:h C7 | Cm7 Cm7b5 | Cdim7:w", voicing="root"))
display(s, caption="The five seventh chords on C")
```

Listen to `C7` against `Cmaj7`. The first wants to go somewhere, and chapter 22 says where. The second just glows. The last line prints `Bbb`, a *double flat*, the same piano key as A. Chapter 16 said why it is spelled that way: a stack of thirds uses every other letter, and the fourth letter up from C by thirds is B.

## Inversions

The tones say what is in a chord and not which goes at the bottom. Put a chord's third at the bottom and you have its first *inversion*, its fifth and you have its second, and a seventh chord has a third with the seventh there. A slash in a symbol names the note at the bottom, the *bass*, and it must be a tone of the chord. `Chord(root, quality, inversion=1)` says the same thing by number:

```python {run output=code}
from euterpe import Chord

for c in (Chord("C"), Chord("C/E"), Chord("C/G"), Chord("C", "maj7", inversion=1)):
    print(c.name, c.tones, c.bass, c.pitches())
```

`tones` does not change, since these are all one chord, and `bass` and `pitches` do. Here is C over each of its three basses, two beats each:

```python {run}
from euterpe import Meter, Score, chords, display
from euterpe.instruments import ElectricPiano

s = Score(meter=Meter("4/4"), tempo=60)
s.part("keys", ElectricPiano()).add(chords("C:h C/E | C/G r", octave=3))
display(s, caption="C in root position, then on E, then on G")
```

The same three letters and yet three weights. On C it sits. On E it is lighter and could carry on. On G, with a fourth between the bass and the root above it, it hangs, and you wait for a chord that does not come. Most of what a bass line does is choose among these.

## A progression

A *progression* is one chord after another. Here is the first bar of Chopin's Prelude, in symbols. `chords` has to decide where to put each chord, and that is a *voicing*. `voicing="root"` stacks each from its root, and `voicing="close"`, the default, picks whichever inversion moves the fewest semitones from the chord before:

```python {run}
from euterpe import Key, Meter, Score, chords, display
from euterpe.instruments import ElectricPiano

for voicing in ("root", "close"):
    s = Score(key=Key("C minor"), meter=Meter("4/4"), tempo=52)
    s.part("keys", ElectricPiano()).add(chords("Cm:q Fm G7 Cm", voicing=voicing))
    display(s, caption=f"The Prelude's first bar in symbols, voicing={voicing!r}")
```

Those are the same four chords. The first take heaves all its notes up and down the staff, and the second moves little, keeps the common notes where they are and sounds like one thing changing. The notes it moves are what chapter 23 will call voices.

One bar is short. Here is the second bar, and two changes. The `open` voicing drops the second note from the top by an octave, so the hands spread apart, `octave=3` sets the register, and `bass=2` adds each chord's bass again in octave 2. A *major* chord can stand in a minor key too: A♭, D♭ and E♭7 all do here:

```python {run}
from euterpe import Key, Meter, Score, chords, display
from euterpe.instruments import ElectricPiano

sketch = "Cm:q Fm G7 Cm | Ab Db Eb7 Ab"
s = Score(key=Key("C minor"), meter=Meter("4/4"), tempo=52)
s.part("keys", ElectricPiano()).add(chords(sketch, voicing="open", octave=3, bass=2))
display(s, caption="The Prelude's first two bars in symbols, open with a bass")
```

That already sounds like the Prelude, heavy and slow. It is still not what Chopin wrote, which the closing piece gets to.

## Reading chords back

So far the name has made the notes. `Chord.from_pitches` goes the other way: it tries each note as a root against the table of qualities, by spelling, and gives a `Chord`, or `None` when nothing fits. Chapter 10's harp played eight bars of Bach's Prelude in C, each bar one chord of five notes spread out. There they were only a list. Here is the same list, read:

```python {run continue output=code}
from euterpe import Chord, Pitch

bars = ["C4 E4 G4 C5 E5", "C4 D4 A4 D5 F5", "B3 D4 G4 D5 F5", "C4 E4 G4 C5 E5",
        "C4 E4 A4 E5 A5", "C4 D4 F#4 A4 D5", "B3 D4 G4 D5 G5", "B3 C4 E4 G4 C5"]
print([Chord.from_pitches(Pitch(name) for name in bar.split()).name for bar in bars])
```

Doubled notes count once, and order counts only for the lowest note, which is the slash. So Bach's bass line, C C B C C C B B, is written right there in the names, and six of his eight chords are inverted to keep it near one note.

A recording can be read too. `chroma` folds a clip's spectrum into the twelve notes of the octave, one row for each, and draws how much energy each one holds over time, with octaves counted together. The organ joins the sketch on close chords, and this block plays the two parts and shows the result:

```python {run continue}
from euterpe import chords, display
from euterpe.instruments import Organ

s.part("organ", Organ(), gain=0.25).add(chords(sketch))
display(s.play().take(9.3).chroma(caption="The sketch's chromagram: each chord's tones as bright rows"))
```

Each chord is a column of three or four rows, and you can read the first off the picture: C, then D♯ and G. A sound has no spelling, so the view prints E♭ on the row of D♯. The darkest row is the chord's bass, which `bass=2` doubles. The palest rows are partials: the A♯ under Cm is the 3rd partial of E♭. So a chromagram shows what sounds, partials included, and `Chord.from_pitches` reads what is written.

## Putting it all together

Chopin's Prelude, its first eight bars. The score writes a stack for each beat, up to five notes in the right hand over a left hand in octaves, in the spacing he chose. The sketch said `G7`. Chopin's third beat has more going on than that: his left hand holds the G, the right holds G and B, and the top two notes come late, E♭ and G for three sixteenths, then D and F for one. Written as a stack, `~` holds the notes the next stack shares and lets the others change. `ff` and `p` are his, and they mean what they meant in chapter 16:

```python {run name=prelude}
from euterpe import melody

right = melody("""
    ff <g3 c4 eb4 g4>:q <ab3 c4 eb4 ab4> <g3 b3 eb4 g4>:e.~ <g3 b3 d4 f4>:s <eb3 g3 c4 eb4>:q |
    <eb3 ab3 c4 eb4> <f3 ab3 db4 f4> <db3 eb3 g3 c4 eb4>:e.~ <db3 eb3 g3 bb3 db4>:s <c3 eb3 ab3 c4>:q |
    <d3 f3 b3 d4> <e3 g3 bb3 c4 e4> <ab3 c4 g4>:e.~ <ab3 c4 f4>:s <g3 c4 eb4>:q |
    <f#3 c4 d4> <g3 b3 d4 g4> <c4 d4 f#4 b4>:e.~ <c4 d4 f#4 a4>:s <b3 d4 g4>:q |
    p <eb4 g4 eb5> <eb4 ab4 eb5> <d4 ab4 d5>:e.~ <d4 f#4 d5>:s <d4 g4 d5>:q |
    <c4 g4 c5> <c4 d4 f#4 d5> <d4 g4 b4>:e. <c4 a4>:s <b3 d4 g4>:q |
    <c4 g4 c5> <ab3 c4 ab4> <g3 d4 g4>:e.~ <g3 d4 f4>:s <g3 c4 eb4>:q |
    <eb3 ab3 c4 eb4> <f3 ab3 db4 f4> <f3 g3 b3 eb4>:e.~ <f3 g3 b3 d4>:s <eb3 g3 c4>:q""")
left = melody("""
    ff <c2 c3>:q <f1 f2> <g1 g2> <c2 g2 c3> | <ab1 ab2> db2 eb2 <ab1 ab2> |
    <g1 g2> c2 <f1 f2> <c2 c3> | <d2 a2 d3> <g1 g2> d2 <g1 g2> |
    p <c2 c3> <c3 c4> <b2 b3> <bb2 bb3> | <a2 a3> <ab2 ab3> <g2 g3> <f2 f3> |
    <eb2 eb3> <f2 f3> <b1 b2> <c2 c3> | <ab1 ab2> db2 <g1 g2> c2""")
```

Then the score. Each hand has its own part, and chapter 12's organ doubles the top note and the left hand's upper note, quietly, to hold what a struck note lets fade. There is no piano preset in this book yet, so the electric piano stands in for Chopin's. Its keys stop at E1, so the six low notes of his left hand under that, as the D♭1 of bar 2, are left out of their octaves. He wrote *Largo* and no number, so 52 quarters a minute is ours, and so is the ramp through bar 8, since we stop where his piece goes on:

```python {run continue name=largo}
from euterpe import Key, Meter, Score, display, melody
from euterpe.instruments import ElectricPiano, Organ
from euterpe.view import listen

top = melody("""
    ff g4:q ab g:e. f:s eb:q | eb f eb:e. db:s c:q | d e g:e. f:s eb:q | d g b:e. a:s g:q |
    p eb5 eb d d | c d b4:e. a:s g:q | c5 ab4 g:e. f:s eb:q | eb f eb:e. d:s c:q""")
bass = melody("""
    ff c3:q f2 g2 c3 | ab2 db2 eb2 ab2 | g2 c2 f2 c3 | d3 g2 d2 g2 |
    p c3 c4 b3 bb3 | a3 ab3 g3 f3 | eb3 f3 b2 c3 | ab2 db2 g2 c2""")
s = Score(key=Key("C minor"), meter=Meter("4/4"), tempo=52, title="Prelude in C minor")
s.part("right", ElectricPiano()).add(right)
s.part("left", ElectricPiano(), clef="bass").add(left)
s.part("top", Organ(), gain=0.2).add(top)
s.part("bass", Organ(), gain=0.2, clef="bass").add(bass)
s.ramp(8, 1, to=40)
song = s.play()
display(s.notation(bars=(1, 2), caption="Bars 1 and 2: stacks over octaves, with the top two notes late on beat 3"))
listen(song, caption="Chopin, Prelude in C minor, Op. 28 No. 20, bars 1 to 8, on electric piano and organ")
```

At 52 quarters a minute a bar takes 4 × 60 / 52 = 4.6 s. Listen to the first four bars loud, with a bass that jumps by fourths and fifths. At bar 5, at 18.5 s, the `p` falls away and so does the jumping: from there the bass walks down by semitones, C, B, B♭, A, A♭, G, while the top stays high and moves little. That walk is a line of inversions: each new note under the stack gives it a new name, as the slashes below show.

So read them. `s.harmony()` goes through the score a beat at a time and hands each beat's notes to `Chord.from_pitches`, longest first, and `?` marks a beat with no name:

```python {run continue output=code}
names = [h.chord.name if h.chord else "?" for h in s.harmony()]
for bar in range(8):
    print(bar + 1, names[4 * bar:4 * bar + 4])
```

Bar 1 reads Cm, Fm7, Ebaug/G and Cm. The sketch's plain `Fm` was short one note: Chopin's has an E♭ in it. The third name is simply wrong to the ear. You hear G7 with its top arriving late, and the reader counts a note that lasts three sixteenths as the chord and the one that lasts one as a passing thing. Bar 6's second beat is a `?` for a better reason: A♭, C, D and F♯ is a real chord that is not one of this chapter's qualities, and this book does not name it.

So names go a long way and not all the way, and they tell you nothing about order. Play bar 1 backwards, Cm, G7, Fm, Cm, and every chord keeps its name, and you hear another phrase. Why does G7 lead into C minor so firmly, and why does bar 3's C7 lead on to Fm? A name says what a chord is, and it cannot say what the chord is doing there. Chapter 22 gives chords a job in a key.

## Summary

- A triad is two thirds stacked on a root. Their two sizes give the four qualities: major, minor, diminished and augmented. `Chord("Cm").tones` lists the names, `pitches` places them, and `keyboard` draws them.
- A major triad's near-meetings of partials are lower than a minor triad's, and in just tuning its notes are partials 4, 5 and 6 of one note.
- A third third gives a seventh chord: `maj7`, `7`, `m7`, `m7b5` and `dim7`.
- A slash in a symbol sets the bass, as `Chord("C/E")`, and the bass changes a chord's weight and not its tones.
- `chords` takes symbols or numerals, and `voicing` chooses the spacing: `close` moves least, `root` keeps root position, and `open` spreads the hands. `bass=2` adds the bass an octave or more below.
- `Chord.from_pitches` names a stack from its spelling, `s.harmony()` names a score's beats, and `clip.chroma()` draws a sound's tones as rows.
- In a stack line, `~` holds what the next stack shares and lets the rest change.

## Exercises

1. In the first block of the Inversions section, change `Chord("C/G")` to `Chord("C/D")`. What happens, and why?
2. In the block with `for voicing in ("root", "close")`, change `"root"` to `"open"`. What is the bottom note of the first chord now?
3. In the block with `bass=2`, change `G7` to `Gm`. Which note changed, and what happens to the pull into the next `Cm`?

### Answers

1. It raises `ValueError`: D is not a tone of C, and the bass after a slash must be one.
2. E♭3. The close stack is C4, E♭4 and G4, and `open` drops the second note from the top, E♭, an octave.
3. B natural becomes B♭, and F goes, since `Gm` has no seventh. B natural is the leading tone of C minor, a half step under C, as chapter 18 said. Without it the step into C minor has much less pull, and chapter 22 says why.

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
