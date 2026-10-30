# Notes, octaves and spelling

Chapter 15 typed every note as a time in seconds and a pitch name. A musician writes bars in a key, and from here on so does this book. This is where the chapter ends up, in that language:

```python {run echo=false}
# The teaser: the first bars of the finale, built by the code of this chapter's two named finale
# blocks, which it reads from this file so the two never differ. The blocks' own views are skipped.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import render

text = Path("chapters/16-notes-octaves-and-spelling.md").read_text()
scope = {}
for name in ("tune", "strings"):
    code = re.search(rf"```python \{{[^}}\n]*name={name}\b[^}}\n]*\}}\n(.*?)\n```", text, re.S).group(1)
    exec("\n".join(line for line in code.split("\n") if "listen(" not in line and "display(" not in line), scope)
# Four bars of four beats at 132 bpm: the teaser stops in the rest that ends bar 4.
display(Clip(render(scope["song"], 4 * 4 * 60 / 132), caption="The opening of Eine kleine Nachtmusik, in three octaves"))
```

Mozart's *Eine kleine Nachtmusik*, K. 525, written in 1787: a violin, a string section an octave under it and plucked strings two octaves under it, all on one line. Three instruments, and you hear one tune. By the end of this chapter you will know why, and you will have written it down in six lines of text.

## Seven letters

Western music names its notes with seven letters, A to G, and then starts over. `Scale` lists the notes of a scale, and C major from C4 is the white keys of a piano; chapter 18 explains scales, and here `Scale` only hands us the notes. `degree(n)` counts them from 1, with 8 back on C. `Harp`, from chapter 10, plays them, and its phrase draws itself as a *piano roll*: a keyboard on its side, with each note a bar from where it starts to where it ends:

```python {run}
from euterpe import Scale
from euterpe.instruments import Harp

c_major = Scale("C", "major")
run = [(0.4 * (n - 1), c_major.degree(n), 0.4) for n in range(1, 9)]
Harp().play(run).take(4.0, "C major from C4 to C5, on the harp")
```

Listen to the 7th note, B4, and how much it wants to go on to C5. Stop the player there and the run feels unfinished. Chapter 18 says why.

Each note of that run is a `Pitch`: a letter with an *octave number* after it, the system called *scientific pitch notation*. A4 is the A of chapter 2, the 440 Hz that orchestras tune to. Each pitch also has a number, the count of keys from a very low C that MIDI, the standard file format for notes, calls note 0:

```python {run output=code}
from euterpe import Pitch, Scale

print(Pitch("A4"), Pitch("A4").number, Pitch("A4").freq)
for p in Scale("C", "major").pitches():
    print(p, p.number, round(p.freq, 2))
```

The octave number changes at C, not at A: B3 is followed by C4, and A4 sits above C4. C4 is number 60, the middle of a piano. The numbers do not climb evenly: from E to F they rise by 1, and from B up to the next C too, as the keyboard below shows; between every other pair of neighbours they rise by 2. A step of 1 is a *semitone*, the smallest step on a keyboard, the factor 2^(1/12) of chapter 2. The white keys are the seven letters, and the gaps of 2 are where a black key sits. The two names on each black key come below:

```python {run echo=false}
import matplotlib.pyplot as plt

from euterpe.view import figure


def draw():
    fig, ax = plt.subplots(figsize=(7, 2.4))
    for i, name in enumerate("C D E F G A B C".split()):
        ax.add_patch(plt.Rectangle((i, 0), 1, 3, facecolor="white", edgecolor="#1b1f23", linewidth=0.8))
        ax.text(i + 0.5, 0.3, f"{name}{5 if i == 7 else 4}", ha="center", fontsize=12)
        ax.text(i + 0.5, 0.75, "60 62 64 65 67 69 71 72".split()[i], ha="center", fontsize=10, color="#555555")
    for x, sharp, flat, number in ((1, "C♯", "D♭", 61), (2, "D♯", "E♭", 63), (4, "F♯", "G♭", 66), (5, "G♯", "A♭", 68), (6, "A♯", "B♭", 70)):
        ax.add_patch(plt.Rectangle((x - 0.32, 1.2), 0.64, 1.8, facecolor="#1b1f23", edgecolor="#1b1f23"))
        for y, label in ((2.45, sharp), (2.0, flat), (1.45, str(number))):
            ax.text(x, y, label, ha="center", fontsize=11, color="white")
    ax.set_xlim(-0.05, 8.05)
    ax.set_ylim(-0.05, 3.05)
    ax.axis("off")
    return fig


figure(draw, caption="One octave of a keyboard, from C4 to C5: each key's name and number")
```

## The octave

The run ended on a C, and the C at its end sounded like the C at its start, only higher. That distance is chapter 2's octave: eight letters counted from the first to the last, 12 semitones, and a doubling of the frequency. A5 is 880 Hz, A3 is 220 Hz. It is the reason the letters start over at all. Two notes an octave apart get one name because the ear treats them as one note in two heights. A4, then A5, then both at once:

```python {run}
from euterpe.instruments import Harp
from euterpe.pitch import A4, A5

Harp().play([(0.0, A4, 1.5), (1.5, A5, 1.5), (3.0, A4, 3.0), (3.0, A5, 3.0)]).take(6.5, "A4, then A5, then both together")
```

The third sound is hard to hear as two notes. It sounds like one A, brighter than the first. Chapter 3 gives the reason: a note is a stack of partials at whole multiples of its pitch. Chapter 1's saw has them all, so a saw on each A shows it, in steps of A4's 440 Hz:

```python {run}
from euterpe.pitch import A4, A5
from euterpe.sound import Saw
from euterpe.view import spectrum

low = (Saw(A4.freq) * 0.5).take(1.0)
high = (Saw(A5.freq) * 0.5).take(1.0)
spectrum(low, high, f0=A4.freq, labels=["A4", "A5"], caption="A saw on A4 and on A5, in harmonics of 440 Hz")
```

A5 has stems only on A4's even harmonics: every partial of A5 is a partial of A4. So adding A5 to A4 adds no new frequency, and nothing beats: it only makes the even partials of the same stack louder. That is what brighter meant above. The octave is the smallest distance that does this, but this arithmetic is not the whole reason for the shared name: three times A4, 1320 Hz, is on A4's stack too, and it is almost exactly E6, which has a name of its own. Chapter 17 hears the other distances.

## Sharps and flats

Five black keys have no letter of their own. Each takes its name from a neighbour: a *sharp* (♯) raises a letter by a semitone and a *flat* (♭) lowers it by one. The key between C and D is C♯ and it is also D♭. In code, `#` and `b` follow the letter:

```python {run output=code}
from euterpe import Pitch

cs, db = Pitch("C#4"), Pitch("Db4")
print(cs, db, cs == db, cs.sounds_as(db))
print(cs.number, db.number, cs.freq, db.freq)
print(Pitch("B#3").number, Pitch("Cb4").number, Pitch("E#4").number)
```

Same key, same number, same frequency, and yet `==` says no: a `Pitch` is a name, so `C#4` and `Db4` are two different values, and `sounds_as` is how you ask about the sound. The last line shows that a white key can take a sign too. B♯3 is C4's key, number 60; C♭4 is B3's, 59; E♯4 is F4's. In code the ready-made names spell a sharp with `s`, since Python does not allow `#` in a name: `Cs4` and `Db4` come from `euterpe.pitch`.

Add a whole number to a pitch and you move that many semitones. All twelve keys of an octave, one semitone at a time, are called the *chromatic scale*; the 13th note below is C5, which closes the octave:

```python {run}
from euterpe.instruments import Harp
from euterpe.pitch import C4

chromatic = [C4 + i for i in range(13)]
Harp().play([(0.25 * i, p, 0.25) for i, p in enumerate(chromatic)]).take(3.5, "The twelve semitones from C4 to C5")
```

It climbs with no landmark, every step the same, so nothing marks where it is going. Against it the white keys' pattern of 2s and 1s, which you heard above, has a shape. Read the names on the roll: `C4 + 1` is `C#4`, never `Db4`. A number has no opinion about which letter it belongs to, so Euterpe needs a rule and takes the sharp. A person writing music has a reason to choose, and "Spelling is a bug", below, comes to it.

## A first score

The tune now. `melody` reads a line of text. A note is a letter, its sign and its octave, a colon and a duration: `g5:q` is G5 for a *quarter*, a quarter of a whole note. `e` is an eighth, `h` a half, `s` a sixteenth, `w` a whole note, four quarters long, and `r` is a rest, a silence. A dot makes a note half as long again, so `q.` is 3/8. Each token can leave out what it shares with the one before: without a duration it repeats the last one, and without an octave it takes the nearest one, so `g5:e d g b` is G5, D5, G5, B5. A `|` closes a bar. Chapter 19 does rhythm properly; for now, a *bar* here holds four quarters, and the tempo counts quarters per minute.

`Score` holds a key and a tempo, and `part` gives a line an instrument. This *key* is a different word from a keyboard's key: it is the set of seven notes a piece is built on, the next section says which, and it changes no sound here. `display` engraves the score and puts a player under it. These are the first four bars of K. 525, as printed in the Breitkopf & Härtel edition of 1883, in the key of G major:

```python {run}
from euterpe import Key, Score, display, melody
from euterpe.instruments import Violin

text = "g5:q r:e d5 g5:q r:e d5 | g5:e d g b d6:q r | c6:q r:e a5 c6:q r:e a5 | c6:e a f# a d5:q r"
opening = melody(text)
s = Score(key=Key("G major"), tempo=132)
s.part("violin", Violin()).add(opening)
display(s, caption="The opening of K. 525 on one violin")
```

At 132 quarters a minute a bar takes 4 × 60 / 132 = 1.82 s. There are no seconds in the text and no times to add up: the rests and the durations say where each note falls.

The figure is a *staff*, the way this music has been written for centuries. It has five lines; each line and each space between them is one letter, and higher on the page is higher in pitch. A black head with a stem is a quarter, a flag on the stem makes it an eighth, and the small squiggles are rests. Three signs open the first staff. The curly one is the *treble clef*, which fixes which line is which letter. The ♯ on the top line is the key: it says that every F is F♯ without writing it each time. The 4/4 is the four quarters a bar of the text above. So the third note of bar 4, the one black key in these bars, carries no sign of its own, sitting on that top line. Only the staff leaves the sharp out: `melody` reads exactly what you type, so a plain `f` is F natural whatever the key, which is why the text says `f#`. You do not need to read a staff fluently for this book; you need to see which sign is where.

An octave lower is a move you can already name. `transpose` moves a line by an *interval*, a distance between notes, written as text: `-P8` is an octave down, and chapter 17 explains the letters. It is a second line on the same score, so the same four bars now sound in two octaves:

```python {run continue}
from euterpe import Interval
from euterpe.instruments import StringSection

s.part("section", StringSection(players=2)).add(opening.transpose(Interval("-P8")))
display(s, caption="The violin, with a string section an octave under it")
```

The section thickens the violin without adding a second tune, the effect you heard on the harp and saw in the saw's spectrum. Chapter 13's section makes each note out of two detuned bows, so it also adds its slow beating.

## Spelling is a bug

G major is the seven letters from G, one of each: G, A, B, C, D, E, and one more. The last one sits a semitone under G, not on plain F, because of the major pattern chapter 18 derives. That is the black key with two names, so which? The rule of a key is *one note per letter*, so it has to be F♯: as G♭ there would be two Gs and no F. Here is the opening with that note typed as G♭, against the key. `notation` engraves a score with no player, and `bars` picks the first and last bar to show:

```python {run continue}
from euterpe import Key, Score, display, melody
from euterpe.instruments import Violin

right = Score(key=Key("G major"), tempo=132)
right.part("violin", Violin()).add(opening)
wrong = Score(key=Key("G major"), tempo=132)
wrong.part("violin", Violin()).add(melody(text.replace("f#", "gb")))
display(right.notation(bars=(4, 4), caption="Bar 4 with F♯"), wrong.notation(bars=(4, 4), caption="Bar 4 with G♭"))
```

The first staff has no sign on that note. The second prints a flat in front of a G, where a player sight-reading G major expects the plain F that the key has already sharpened. So the two look different. Do they sound different? Play this one against the violin of the last section:

```python {run continue}
from euterpe.view import listen

listen(wrong.play(), caption="The same four bars with G♭")
```

Now the same question with the data. `play` performs a score into a sound, as an instrument's `play` does, so the samples can be compared. Then what each file format keeps: MIDI is the note format of the first section, and MusicXML is the format notation programs read:

```python {run continue output=code}
import numpy as np
from euterpe.lint import Report
from euterpe.score.midi import midi_bytes
from euterpe.score.musicxml import musicxml_bytes
from euterpe.sound import render

a, b = right.play(), wrong.play()
print("same samples:", np.array_equal(render(a, a.duration), render(b, b.duration)))
print("same MIDI:", midi_bytes(right) == midi_bytes(wrong))
print("same MusicXML:", musicxml_bytes(right) == musicxml_bytes(wrong))
kept = ("N-SPELLING", "R-COMFORT")
print(Report([f for f in wrong.lint().findings if f.rule in kept]).to_text())
```

The samples are equal to the bit, so no ear could tell. The MIDI data is equal too, since MIDI stores key numbers and has no idea what a note is called. MusicXML keeps the spelling. And `lint`, a linter for scores, reads each note against the key and reports this one by bar and beat: `N-SPELLING` is a warning, since nothing fails to play. The other line, `R-COMFORT`, is a measure, and says the whole line sits where a violin plays comfortably. `lint` measures much more than these two, and `kept` picks them out of its findings; later chapters read the rest.

The rule comes from the key itself. `key.scale` holds its notes, and `key.spell` turns a number into the name this key gives it. The last column moves each spelling up by `m2`, the interval of chapter 17 that goes one semitone up and one letter on:

```python {run continue output=code}
from euterpe import Interval, Key
from euterpe.pitch import Fs5, Gb5

key = Key("G major")
print(key.scale.pitches())
for p in (Fs5, Gb5):
    print(p, p in key.scale, key.spell(p.number), p + Interval("m2"))
```

So why call it a bug, if nothing audible breaks? Because a score is read as well as heard, and the music of the next chapters runs on letters. F♯ up to A is a third, three letters; G♭ up to A is a kind of second, two letters. Those are different things to chapter 17. And the same move, up by `m2`, lands the right spelling on G and the wrong one on A with two flats. A wrong spelling sounds right today and breaks later, which is what bugs do. Euterpe keeps your spelling exactly as you wrote it, so that it can be checked.

An interval keeps the letters too, which is what makes `transpose` safe. The score from the last section still holds the violin and the section, and the plucked strings of chapter 10, `PizzicatoStrings`, join them two octaves under the violin. `-P15` is two octaves counted in letters, 8 + 8 - 1, since the note where they meet is counted once:

```python {run continue}
from euterpe import Interval, display
from euterpe.instruments import PizzicatoStrings

s.part("pizzicato", PizzicatoStrings()).add(opening.transpose(Interval("-P15")))
display(s, caption="The opening in three octaves")
```

All three parts carry F♯, each with no sign of its own in bar 4. The lowest staff opens with the *bass clef* instead of the treble clef, which moves the letters so low notes fit on the lines, so the same shape there sounds lower. The plucked notes fade fast and mark each note's start under the sustained bows.

## Putting it all together

The closing piece is K. 525 from bar 1 to the long G that starts bar 18, 18 bars of the first violin's part, from the same 1883 edition. It stays in G major. `p` is a soft mark from the next note on, and `f!` a loud one; a bare `f` would be the note F. The first ten bars are loud and the next seven soft. The notation has no sign for the violin's trills and grace notes, so they are left out, and one `Violin` plays one string at a time, so the three-note chords of bars 1 and 5 keep only their top note. Bar 18 is held to the end of the bar, so that the excerpt stops on G, the note the key is named after:

```python {run name=tune}
from euterpe import melody

k525 = melody("""
    f! g5:q r:e d5 g5:q r:e d5 | g5:e d g b d6:q r | c6:q r:e a5 c6:q r:e a5 | c6:e a f# a d5:q r |
    g5:e r g:q. b:e a g | g f# f#:q. a:e c6 f#5 | a g g:q. b:e a g | g f# f#:q. a:e c6 f#5 |
    g:e g f# e:s f# g:e g a g:s a | b:e b c6 b5:s c6 d:q r |
    p d5:h e | c:q c b4 b | a a g:e f# e f# | g r a r b r r:q |
    d5:h e | d:e c c c c b4 b b | b a a a g f# e f# |
    f! g4:w""")
```

Then the three layers you have built, on the whole text: the violin, the section an octave under it and the pizzicato two octaves under it. The three start from one text, so they cannot disagree. `gain` scales a part's level, and these bring the softer section and pizzicato up against the violin:

```python {run continue name=strings}
from euterpe import Interval, Key, Score, display
from euterpe.instruments import PizzicatoStrings, StringSection, Violin
from euterpe.view import listen

s = Score(key=Key("G major"), tempo=132, title="Eine kleine Nachtmusik")
s.part("violin", Violin(), gain=0.8).add(k525)
s.part("section", StringSection(players=2), gain=1.2).add(k525.transpose(Interval("-P8")))
s.part("pizzicato", PizzicatoStrings(), gain=1.2).add(k525.transpose(Interval("-P15")))
song = s.play()
display(s.notation(bars=(9, 12), caption="Bars 9 to 12 of the three parts"))
listen(song, caption="Eine kleine Nachtmusik, K. 525, bars 1 to 18, in three octaves")
```

The staff shows bars 9 to 12, with the first sixteenths, two flags on a stem, and the `p` of bar 11. Listen for bar 2, from 1.82 s to 3.64 s, where three instruments are one rising figure, then for bar 11, at 18.2 s, where `p` lowers the velocity and the bows go softer and darker, as chapter 13 built them. The three lines never leave each other, so all you can hear change is register and timbre, and that is the octave at work.

It is also the arrangement's limit. In Mozart's score the strings stay in octaves for only four bars: from bar 5 the violins, violas and basses split, each on notes of its own, and the music opens up. The lines here sit an octave apart, the one distance this chapter named. Chapter 17 names all the others.

## Summary

- Notes have seven letter names and an octave number that changes at C: C4 is number 60, A4 is number 69 and 440 Hz. `Pitch("A4")` has `.number` and `.freq`.
- An octave is 12 semitones and a doubling of frequency. Every partial of the upper note is a partial of the lower one, so the two blend; it is the smallest distance that does, and the letters start over there.
- A sharp raises a letter a semitone and a flat lowers it. C♯ and D♭ are one key and two names: `==` compares names, and `sounds_as` compares sounds.
- `melody` reads notes as text, `Score` holds a key and a tempo, `part(...).add(...)` gives a line an instrument, `play` performs it, and `display` or `notation` engraves it on a staff. A line's `transpose` moves it by an interval.
- A key uses each letter once, so the key decides the spelling: `key.scale` holds its notes and `key.spell(number)` names any number in it. A wrong spelling changes no sample and still changes what is written, and where it goes when it moves. `s.lint()` reports it as `N-SPELLING`.

## Exercises

1. In the octave block, import `Gs5` and change the last `A5` to it, a semitone under the octave. Do the two notes of the third sound still fuse?
2. In the first score block, change `tempo=132` to `tempo=66`. How long is a bar now, and how long are the four bars?
3. In the block with `key.spell`, change `key = Key("G major")` to `key = Key("Db major")`. What do the last two lines print, and why?

### Answers

1. No. G♯5 is 830.6 Hz, and its partials miss A4's: its first partial falls 49 Hz from A4's second at 880 Hz, so the pair rubs and beats, and you hear two notes.
2. A bar takes 4 × 60 / 66 = 3.64 s, and the four bars 14.5 s, against 1.82 s and 7.3 s. The text of the tune does not change.
3. `F#5 False Gb5 G5` and `Gb5 True Gb5 Abb5`. D♭ major has G♭ as its 4th note and no F♯, so the same key on the piano, number 78, now takes the other name. The spelling comes from the key, not from the key on the keyboard.

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
