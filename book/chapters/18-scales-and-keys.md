# Scales and keys

Chapter 17 stopped on a question: why does the Invention stay on seven of the twelve notes for three bars, and what does one new note change? Here is where this chapter ends up, on eight bars from the middle of its closing piece, and at the fifth of them the whole band steps up by one semitone:

```python {run echo=false}
# The teaser: bars 17 to 24 of the finale, four bars in D and four in E♭, built by the code of this
# chapter's two named finale blocks, which it reads from this file so the two never differ. The blocks'
# own views are skipped.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import render

text = Path("chapters/18-scales-and-keys.md").read_text()
scope = {}
for name in ("tune", "joy"):
    code = re.search(rf"```python \{{[^}}\n]*name={name}\b[^}}\n]*\}}\n(.*?)\n```", text, re.S).group(1)
    exec("\n".join(line for line in code.split("\n") if "listen(" not in line and "display(" not in line), scope)
# Two beats a bar at 116 bpm.
bar = 2 * 60 / 116
samples = render(scope["song"], 24 * bar)[int(16 * bar * 48000):]
display(Clip(samples, caption="Joy to the World: the end of the verse in D, then its start in E♭"))
```

Every note after the turn is a semitone higher than the note it replaces, and the tune is the same tune. Yet of the seven notes the verse was using, five are gone. What changed is the *key*, and this chapter says what a key is, which notes it holds, why it has a home, and how far apart two keys are.

## Steps

Chapter 16 found that the white keys climb by 2s and 1s, and left it there. `Scale` holds a *tonic*, the note a scale is named after, and a mode, and `steps` gives the semitones from each note to the next, ending back on the tonic. A step of 2 is a *whole step*, W, and a step of 1 a *half step*, H, the semitone of chapter 16:

```python {run output=code}
from euterpe import Scale

c_major = Scale("C", "major")
print(c_major.pitches())
print(c_major.steps, "".join("HW"[step - 1] for step in c_major.steps))
for tonic in ("G", "D"):
    print(Scale(tonic, "major").pitches(), Scale(tonic, "major").steps)
```

The pattern W W H W W W H is what *major* means. Start it on any of the twelve keys of a piano and you get a major scale, and it has to use whichever black keys the pattern lands on. This is the rule chapter 16 borrowed. From G the pattern needs a whole step from E, which F does not give, since E to F is a half step. So the sixth step lands on the black key above F, and because a scale uses one note per letter, its name is F♯.

```python {run}
from euterpe import Scale, display

display(Scale("C", "major").keyboard(caption="C major: the pattern fits the white keys from C"),
        Scale("D", "major").keyboard(caption="D major: the same pattern from D needs F♯ and C♯"))
```

A scale is not yet a tune, but this one nearly is. Lowell Mason printed a hymn tune called Antioch in Boston in 1839, and everyone knows it as Joy to the World. Its first line is D major, walked down from top to bottom. `Meter("2/4")` makes a bar of two quarters, which chapter 19 explains, and chapter 13's brass section plays it. The two ♯ at the start of the staff are D major's F♯ and C♯:

```python {run}
from euterpe import Key, Meter, Score, display, melody
from euterpe.instruments import BrassSection

opening = melody("d5:q c#:e. b4:s | a:q. g:e | f#:q e | d:h")
s = Score(key=Key("D major"), meter=Meter("2/4"), tempo=116)
s.part("brass", BrassSection(), gain=1.2).add(opening)
display(s, caption="The first line of Joy to the World: D major, from the top down")
```

## The tonic

That line ends with a thump of arrival on its last note. The same steps stopped one note short do not. `Key` holds a tonic and a mode, as a `Scale` does, and `degree(n)` counts its notes from 1. Two takes of D major on the harp, the first climbing to degree 7 and the second to degree 8:

```python {run continue}
from euterpe import Key, display
from euterpe.instruments import Harp

d_major = Key("D major")
for top in (7, 8):
    run = [(0.4 * (n - 1), d_major.degree(n), 0.4) for n in range(1, top + 1)]
    display(Harp().play(run).take(4.0, f"D major climbing to degree {top}, {d_major.degree(top)}"))
```

The first take leaves you hanging on C♯5, as chapter 16's run did on B4, and the second puts you down. The note that ends things, the first degree, is the tonic, and the piece's home. Degree 7 here is the *leading tone*, a half step under it. There is habit in this: music in this tradition has ended on the tonic for centuries, and your ear has learned that. Later sections add the mechanism.

The next most important note is degree 5, a fifth above the tonic, called the *dominant*, and music often stands on it before it goes home. For centuries those two were the only notes an orchestra's timpani were tuned to. Chapter 14's kettles join here on D, the tonic, and on A, the dominant, a fourth under it, so that bar 3 falls from A to D as the tune lands on D. A `decay` of 1.2 s, half the default, keeps repeated strokes from piling up:

```python {run continue}
from euterpe import display, melody
from euterpe.instruments import Timpani

s.part("timpani", Timpani(decay=1.2), gain=0.6).add(melody("d3:q r | d r | a2 a | d3:h"))
display(s, caption="The first line, with timpani on the tonic and the dominant")
```

## Why those seven

The answer to chapter 17's question starts with its smoothest interval. After the octave, the fifth is the distance whose partials meet lowest, 3 to 2. So stack seven notes a fifth apart, from F, then bring them all into one octave. `Pitch(letter, alter, octave)` rebuilds a name in another octave, and `alter` counts its sharps:

```python {run continue output=code}
from euterpe import Interval, Pitch, Scale
from euterpe.pitch import B4, F4

stack = [F4]
for _ in range(6):
    stack.append(stack[-1] + Interval("P5"))
print(stack)
print(sorted(Pitch(p.letter, p.alter, 4) for p in stack))
print(Interval.between(F4, B4))
print(stack[-1] + Interval("P5"))
```

Seven notes a fifth apart, from F, are the seven white keys. That is one account of why W W H W W W H has this uneven shape: it is what is left when a line of fifths is folded into one octave. Seven is also where the stack has to stop if each letter is to appear once, since the next fifth, in the last line, comes back to the letter F.

The stack holds six fifths, but its two ends, F and B, form something else, printed on the third line: the augmented fourth of chapter 17, the tritone, which no other pair of the seven forms. Each of its notes sits on one of the scale's two half steps: B is a semitone under C and F a semitone over E. So when the restless tritone moves, the shortest way out lands on C and E, and those seven notes point at C. That is the mechanism next to the habit, and it is why a leading tone leans.

The last line is the other half of the question. One more fifth above B gives F♯. Add it at the top of the stack, drop F from the bottom, and you have G major. So moving by one fifth changes exactly one note.

## Keys and signatures

Follow that one note up the line of fifths. Each new tonic a fifth up keeps six notes and sharpens one. Going the other way, a tonic a fifth down keeps six and flattens one. A key's *signature* is the count: `signature` gives sharps as a positive number and flats as a negative one, and those are the signs at the start of a staff. `dominant` is the key a fifth up:

```python {run continue output=code}
from euterpe import Key

for name in "C G D A E B F Bb Eb Ab".split():
    key = Key(f"{name} major")
    print(f"{name:3}{key.signature:3} ", " ".join(str(p)[:-1] for p in key.scale.pitches() if p.alter))
c_major, g_major = Key("C major"), Key("C major").dominant
print(g_major, [p for p in g_major.scale.pitches() if p not in c_major.scale])
```

Now the Invention can be read. For three bars it stays on the signature of C major, which has no sign at all. Bar 4 brings F♯, the one note that tells C major from G major, and by bar 7 the music stands on G and sounds as if it has arrived, because it has: one note moved the whole home by a fifth. Chapter 24 does this on purpose.

The line of fifths closes into a circle on the twelve keys of a piano, because twelve fifths come back to the note they started on: that is what equal temperament bought in chapter 17. `circle` draws it, with majors outside and their *relative* minors inside. Neighbours differ by one note, and keys on opposite sides share only two. Here is D major and, next to it, the key we are heading for:

```python {run continue}
from euterpe import Key, display

display(Key("D major").circle(caption="D major, with its neighbours A and G"),
        Key("Eb major").circle(caption="E♭ major, five places round from D"))
```

So D and E♭ are a semitone apart on the keyboard and five places apart on the circle. They share two notes, D and G, out of seven. That is why the turn at the start of this chapter is such a big change for so small a move.

A key also tells a chord what it is made of. `chords` writes chords by *Roman numeral*: I is the chord on the 1st note of the key, IV on the 4th, V on the 5th, and V7 adds one note on top. Chapter 21 builds them. For now what matters is that a numeral names a degree, not a note, so it follows whichever key is in force. Chapter 12's organ takes them, under the same two parts:

```python {run continue}
from euterpe import chords, display
from euterpe.instruments import Organ

s.part("organ", Organ(), gain=0.25).add(chords("I:h | I:q. IV:e | I:q V7 | I:h", octave=3))
display(s, caption="The first line, with the organ on Roman numerals")
```

## Minor

A *minor* scale starts from degree 6 of a major one and uses the same notes. `relative` finds it: `Key("C major").relative` is A minor, with no signs, and `parallel` gives the key of the other mode on one tonic, so `Key("A minor").parallel` is A major. The cost of the move is the leading tone. A minor's degree 7 is G, a whole step under the tonic, and so it does not lean. Musicians use three versions of the scale, here from one tonic, each with its steps in the caption:

```python {run continue}
from euterpe import Scale, display
from euterpe.instruments import Harp

for mode in ("natural minor", "harmonic minor", "melodic minor"):
    scale = Scale("A", mode)
    run = [(0.4 * (n - 1), scale.degree(n), 0.4) for n in range(1, 9)]
    display(Harp().play(run).take(4.0, f"A {mode}, steps {' '.join(map(str, scale.steps))}"))
```

The *natural minor* is that scale as it is. The *harmonic minor* raises degree 7 to G♯, which gives it a leading tone, but it opens a step of 3 from F to G♯, and you can hear the gap. The *melodic minor* also raises degree 6 to F♯, which closes it. Musicians traditionally play that going up and fall back to natural minor coming down, which `Scale` leaves to you, since it only lists the climb. The reason for the raised 7th is one note against the next. `leading_tone` gives the note a half step under the tonic whatever the mode's own 7th is:

```python {run continue}
from euterpe import Interval, Key, display
from euterpe.instruments import Harp

a_minor = Key("A minor")
top = a_minor.degree(8)
for seventh in (a_minor.degree(7), a_minor.leading_tone):
    step = Interval.between(seventh, top).pretty
    display(Harp().play([(0.0, seventh, 1.0), (1.0, top, 1.5)]).take(2.5, f"{seventh} up to {top}, a {step}"))
```

G up to A is a step on the way somewhere. G♯ up to A closes. Chapter 22 builds this into the cadence.

## Modes

The fifths gave seven notes and no first note, and the first note is a choice. The same white keys from D are a different scale, from E another, and so on. These are the seven *church modes*, named by medieval and Renaissance writers after Greek regions and peoples they have little to do with: from C ionian, from D dorian, then phrygian, lydian, mixolydian, aeolian and locrian. Each is the same cycle of steps entered at another place, so `Scale("D", "dorian").steps` is 2 1 2 2 2 1 2. `Scale` has all seven.

Ionian is major and aeolian is natural minor. Dorian is natural minor with one note changed: its degree 6 is a whole step higher. On a D tonic that note is B against B♭, and it is the whole sound of the sea shanty Drunken Sailor, which R. R. Terry printed in The Shanty Book in 1921. `Key("D", "dorian")` has no signature at all, since these are the white keys, and the staff stays clear of signs. The flute has the tune, and the harp plays fifths under it:

```python {run continue}
from euterpe import Key, Score, display, melody
from euterpe.instruments import Flute, Harp

sailor = melody("""
    a4:q a:e a a:q a:e a | a:q d4 f a | g:q g:e g g:q g:e g | g:q c4 e g |
    a:q a:e a a:q a:e a | a:q b c5 d | c a4 g e | d:h d""")
fifths = melody("""
    <d3 a3>:h <d3 a3> | <d3 a3> <d3 a3> | <c3 g3> <c3 g3> | <c3 g3> <c3 g3> |
    <d3 a3> <d3 a3> | <d3 a3> <d3 a3> | <c3 g3> <a2 e3> | <d3 a3>:w""")
shanty = Score(key=Key("D", "dorian"), tempo=120)
shanty.part("flute", Flute()).add(sailor)
shanty.part("harp", Harp()).add(fifths)
display(shanty, caption="Drunken Sailor in D dorian, flute over harp")
```

Listen for bar 6, from 10 s: the climb A, B, C, D. The B is the raised degree, the one that keeps this tune out of natural minor. Lydian and mixolydian are major with one note moved, and locrian has the tritone on its tonic, which is why it is rare. Most of the music in this book is major or minor, and you now know what those two leave out.

## Transposing a key

Chapter 17 ended by saying that equal temperament leaves every key usable. Now use that. `Score.transpose` moves a whole score by an interval, with its key, its notes and, through the key, its numerals. The first line of Joy to the World with all its parts, up a minor second:

```python {run continue}
from euterpe import Interval, display

eb = s.transpose(Interval("m2"))
display(eb, caption="The first line moved up a minor second, into E♭ major")
```

The tune is the same and only its height changes. Each D has become E♭ and each F♯ has become G, each spelled by the interval: `m2` is one letter up, so `eb.key.scale` holds E♭, F, G, A♭, B♭, C and D. Now try the other name for the same semitone. `A1`, an *augmented unison*, moves by a semitone too and stays on the same letter. The block compares the samples of the two scores and engraves them both:

```python {run continue}
import numpy as np
from euterpe import Interval, display
from euterpe.sound import render

sharp = s.transpose(Interval("A1"))
a, b = eb.play(), sharp.play()
same = np.array_equal(render(a, a.duration), render(b, b.duration))
display(eb.notation(bars=(1, 2), caption=f"E♭ major, signature {eb.key.signature}"),
        sharp.notation(bars=(1, 2), caption=f"D♯ major, signature {sharp.key.signature}, same samples: {same}"))
```

The samples are equal to the bit, so these two scores sound alike. Yet E♭ major has three flats, and D♯ major has nine sharps, more than the seven letters, so F and C each take two: `##` is a *double sharp*, which raises a letter by two semitones, and `sharp.key.scale` holds `F##` and `C##` among its seven.

This is chapter 16's lesson at the size of a key. No musician writes D♯ major, because E♭ says the same thing with six signs fewer. The choice of `m2` over `A1` changes nothing you can hear, and everything you can read.

## Putting it all together

The closing piece is the first verse of Antioch as Lowell Mason printed it in The Modern Psalmist, Boston, 1839, played in D and then up a semitone in E♭. The melody is the top voice of his four parts, with the long D that ties bars 7 and 8. Its opening walk down the scale comes back, and the leading tone, C♯, leads up to the top D in bars 6 and 7. The tune, the Roman numerals and the kettles, each written once in D:

```python {run name=tune}
from euterpe import chords, melody

tune = melody("""
    d5:q c#:e. b4:s | a:q. g:e | f#:q e | d:q. a:e |
    b:q. b:e | c#5:q. c#:e | d:h~ | d:q. d:e |
    d c# b4 a | a:e. g:s f#:e d5 | d c# b4 a | a:e. g:s f#:e f# |
    f# f# f# f#:s g | a:q. g:s f# | e:e e e e:s f# | g:q. f#:s e |
    f#:e d5:q b4:e | a:e. g:s f#:e g | f#:q e | d:h""")
harmony = chords("""
    I:h | I:q. IV:e | I:q V7 | I:h | IV:h | V | I | I |
    I | I | I | I | I | I | V | V7 | I:q. IV:e | I:h | I:q V7 | I:h""", octave=3)
kettles = melody("""
    d3:q r | d r | a2 a | d3 r | r:h | a2:q a | d3 r | d r |
    d r | d r | d r | d r | d d | d d | a2 a | a a | d3 r | a2 a | a a | d3:h""")
```

Then the score. The verse plays once as written, and the same lines follow it: `transpose` moves the tune and the kettles, and the numerals need no move, because `change` puts the key of E♭ in force from bar 21. `gain`, as in chapter 16, keeps the tune in front:

```python {run continue name=joy}
from euterpe import Interval, Key, Meter, Score, display
from euterpe.instruments import BrassSection, Organ, Timpani
from euterpe.view import listen

up = Interval("m2")
s = Score(key=Key("D major"), meter=Meter("2/4"), tempo=116, title="Joy to the World")
s.part("brass", BrassSection(), gain=1.2).add(tune + tune.transpose(up))
s.part("organ", Organ(), gain=0.25).add(harmony + harmony)
s.part("timpani", Timpani(decay=1.2), gain=0.6).add(kettles + kettles.transpose(up))
s.change(21, key=Key("Eb major"))
song = s.play()
display(s.notation(bars=(19, 22), caption="Bars 19 to 22: the verse ends in D and starts again in E♭"))
listen(song, caption="Joy to the World, Antioch, in D and then in E♭, on brass, organ and timpani")
```

At 116 quarters a minute a bar takes 1.03 s, so the turn comes at 20.7 s. Listen for the first line again, then the leading tone and its top D at about 6 s. Listen under it for the timpani moving between A and D. At the turn, the signature on the staff swaps two sharps for three flats and everything rises a semitone. It is a blunt and much-used way of changing key, with no preparation: a band just shifts up to lift the last verse. Chapter 24 prepares such moves.

There is one note here that this chapter has not explained, and it is in bar 17, at 16.6 s: the top D starts halfway through the first beat and holds across the start of the second. All the other notes of the tune begin on a beat or fill in between beats, and that one leans over one. This chapter has also typed `2/4` and dots without saying what a beat is. Chapter 19 says, and then builds rhythm from moving notes off it.

## Summary

- `Scale(tonic, mode)` lists a scale, and `steps` gives its semitones. Major is W W H W W W H, 2 2 1 2 2 2 1, from any of the twelve keys, with one note per letter.
- `Key` adds what a piece needs: `degree(n)`, `signature`, `dominant`, `relative`, `parallel`, `leading_tone` and `spell`. The tonic is home, the dominant is degree 5, and the leading tone is the half step under the tonic.
- Seven notes a fifth apart, folded into one octave, are the seven notes of a major scale. Their two ends form the scale's single tritone, which sits on its two half steps and points at the tonic.
- A tonic a fifth up keeps six notes and sharpens one. `key.circle()` draws the circle of fifths, on which neighbours share six notes and distant keys few.
- A minor scale shares its notes with its relative major. Harmonic minor raises degree 7 for a leading tone, and melodic minor also raises degree 6 to close the gap.
- The church modes are the same cycle of steps from another start. `Key("D", "dorian")` is natural minor with a raised 6th.
- `score.transpose(interval)` moves a whole score, and Roman numerals follow the key. `m2` and `A1` give the same samples and different spellings: E♭ major's three flats against D♯ major's nine sharps.

## Exercises

1. In the first block, change `("G", "D")` to `("F#", "Gb")`. What do the two new scales print, and do they sound different?
2. In the Drunken Sailor block, change the `b` in bar 6 to `bb`. What happens to the sound of bar 6, and what appears on the staff?
3. In the block with `eb = s.transpose(Interval("m2"))`, change `"m2"` to `"M2"`. What key do you get, how many notes does it share with D major, and did the numerals need any change?

### Answers

1. `F#4 G#4 A#4 B4 C#5 D#5 E#5` and `Gb4 Ab4 Bb4 Cb5 Db5 Eb5 F5`, both with steps 2 2 1 2 2 2 1. They are the same keys on a piano under different names, so they sound alike. They are the far side of the circle of fifths, with six sharps and six flats.
2. The climb to the top is darker, because it is now D natural minor's B♭, the note Dorian raises. The staff prints a flat in front of that note, since the key says D dorian, in which plain B belongs.
3. E major, with four sharps. It shares five notes with D major, E, F♯, A, B and C♯, because it is two places round the circle. The numerals need no change: `I` becomes E major's own tonic chord.

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
