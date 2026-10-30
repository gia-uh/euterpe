# Notes, octaves and spelling

Chapter 15 typed every note as a time in seconds and a pitch name. A musician writes bars in a key, and from here on so does this book. This is where the chapter ends up, in that language:

```python {run echo=false}
# The teaser: the first bars of the finale, built by the code of this chapter's two named finale
# blocks, which it reads from this file so the two never differ. The block's own player is skipped.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import render

text = Path("chapters/16-notes-octaves-and-spelling.md").read_text()
scope = {}
for name in ("tune", "strings"):
    code = re.search(rf"```python \{{[^}}\n]*name={name}\b[^}}\n]*\}}\n(.*?)\n```", text, re.S).group(1)
    exec("\n".join(line for line in code.split("\n") if "listen(" not in line), scope)
display(Clip(render(scope["song"], 8.0), caption="The opening of Eine kleine Nachtmusik, in three octaves"))
```

Mozart's *Eine kleine Nachtmusik*, K. 525, written in 1787: a violin, a string section an octave under it and plucked strings two octaves under it, all on one line. Three instruments, and you hear one tune. By the end of this chapter you will know why, and you will have written it down in six lines of text.

## Seven letters

Western music names its notes with seven letters, A to G, and then starts over. `Pitch` is one of those names with an *octave number* after it, the system called *scientific pitch notation*. A4 is the A of chapter 2, the 440 Hz that orchestras tune to. Each pitch also has a number, the count of keys from a very low C that MIDI, the standard file format for notes, calls note 0:

```python {run output=code}
from euterpe import Pitch, Scale

print(Pitch("A4"), Pitch("A4").number, Pitch("A4").freq)
for p in Scale("C", "major").pitches():
    print(p, p.number, round(p.freq, 2))
```

The octave number changes at C, not at A: B3 is followed by C4, and A4 sits above C4. C4 is number 60, the middle of a piano. The numbers do not climb evenly: from E to F and from B to C they rise by 1, and between every other pair of neighbours by 2. A step of 1 is a *semitone*, the smallest step on a keyboard, the factor 2^(1/12) of chapter 2. The white keys are the seven letters, and the gaps of 2 are where a black key sits:

```python {run echo=false}
import matplotlib.pyplot as plt

from euterpe.view import figure


def draw():
    fig, ax = plt.subplots(figsize=(7, 2.4))
    for i, name in enumerate("C D E F G A B C".split()):
        ax.add_patch(plt.Rectangle((i, 0), 1, 3, facecolor="white", edgecolor="#1b1f23", linewidth=0.8))
        ax.text(i + 0.5, 0.3, f"{name}{5 if i == 7 else 4}", ha="center", fontsize=10)
        ax.text(i + 0.5, 0.75, "60 62 64 65 67 69 71 72".split()[i], ha="center", fontsize=8, color="#555555")
    for x, sharp, flat, number in ((1, "C♯", "D♭", 61), (2, "D♯", "E♭", 63), (4, "F♯", "G♭", 66), (5, "G♯", "A♭", 68), (6, "A♯", "B♭", 70)):
        ax.add_patch(plt.Rectangle((x - 0.32, 1.2), 0.64, 1.8, facecolor="#1b1f23", edgecolor="#1b1f23"))
        for y, label in ((2.45, sharp), (2.05, flat), (1.5, str(number))):
            ax.text(x, y, label, ha="center", fontsize=8, color="white")
    ax.set_xlim(-0.05, 8.05)
    ax.set_ylim(-0.05, 3.05)
    ax.axis("off")
    return fig


figure(draw, caption="One octave of a keyboard, from C4 to C5: each key's name and number")
```

The eight white keys from C4 to C5 are the C major scale, which chapter 18 explains. Here `Scale` only hands us the notes, and `degree(n)` counts them from 1, with 8 back on C. `Harp`, from chapter 10, plays them, and its phrase draws itself as a *piano roll*: a keyboard on its side, with each note a bar from where it starts to where it ends:

```python {run}
from euterpe import Scale
from euterpe.instruments import Harp

c_major = Scale("C", "major")
run = [(0.4 * (n - 1), c_major.degree(n), 0.4) for n in range(1, 9)]
Harp().play(run).take(4.0, "C major from C4 to C5, on the harp")
```

Listen to the 7th note, B4, and how much it wants to go on to C5. Stop the player there and the run feels unfinished. Chapter 18 says why.

## The octave

The run ended on a C, and the C at its end sounded like the C at its start, only higher. That distance is an *octave*: eight letters counted from the first to the last, 12 semitones, and a doubling of the frequency. A5 is 880 Hz, A3 is 220 Hz. It is the reason the letters start over at all. Two notes an octave apart get one name because the ear treats them as one note in two heights. A4, then A5, then both at once:

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
spectrum(low, high, f0=A4.freq, harmonics=16, labels=["A4", "A5"], caption="A saw on A4 and on A5, in harmonics of 440 Hz")
```

A5 has stems only at 2, 4, 6, 8: every partial of A5 is a partial of A4. So adding A5 to A4 adds no new frequency, and nothing beats: it only makes the even partials of the same stack louder. That is what brighter meant above. Only octaves do this. Chapter 17 hears the other distances.

## Sharps and flats

Five black keys have no letter of their own. Each takes its name from a neighbour: a *sharp* (♯) raises a letter by a semitone and a *flat* (♭) lowers it by one. The key between C and D is C♯ and it is also D♭. In code, `#` and `b` follow the letter:

```python {run output=code}
from euterpe import Pitch

cs, db = Pitch("C#4"), Pitch("Db4")
print(cs, db, cs == db, cs.sounds_as(db))
print(cs.number, db.number, cs.freq, db.freq)
print(Pitch("B#3").number, Pitch("Cb4").number, Pitch("E#4").number)
```

Same key, same number, same frequency, and yet `==` says no: a `Pitch` is a name, so `C#4` and `Db4` are two objects, and `sounds_as` is how you ask about the sound. The last line shows that a white key can take a sign too. B♯3 is C4's key, number 60; C♭4 is B3's, 59; E♯4 is F4's. In code the ready-made names spell a sharp with `s`, since Python does not allow `#` in a name: `Cs4` and `Db4` come from `euterpe.pitch`.

Add a whole number to a pitch and you move that many semitones. All twelve keys of an octave, one semitone at a time, is called the *chromatic scale*:

```python {run}
from euterpe.instruments import Harp
from euterpe.pitch import C4

chromatic = [C4 + i for i in range(13)]
Harp().play([(0.25 * i, p, 0.25) for i, p in enumerate(chromatic)]).take(3.5, "The twelve semitones from C4 to C5")
```

It climbs with no landmark, every step the same, so nothing marks where it is going. Against it the white keys' pattern of 2s and 1s, which you heard above, has a shape. Read the names on the roll: `C4 + 1` is `C#4`, never `Db4`. A number has no opinion about which letter it belongs to, so Euterpe needs a rule and takes the sharp. A person writing music has a reason to choose, and the end of the chapter comes to it.

## A first score

The tune now. `melody` reads a line of text. A note is a letter, its sign and its octave, a colon and a duration: `g5:q` is G5 for a *quarter*, a quarter of a whole note. `e` is an eighth, `h` a half, `s` a sixteenth, and `r` is a rest, a silence. Each token can leave out what it shares with the one before: without a duration it repeats the last one, and without an octave it takes the nearest one, so `g5:e d g b` is G5, D5, G5, B5. A `|` closes a bar. Chapter 19 does rhythm properly; for now, a *bar* here holds four quarters, and the tempo counts quarters per minute.

`Score` holds a key and a tempo, and `part` gives a line an instrument, which `play` then performs. These are the first four bars of K. 525, as printed in the Breitkopf & Härtel edition of 1883, in the key of G major:

```python {run}
from euterpe import Key, Score, melody
from euterpe.instruments import Violin

text = "g5:q r:e d5 g5:q r:e d5 | g5:e d g b d6:q r | c6:q r:e a5 c6:q r:e a5 | c6:e a f# a d5:q r"
opening = melody(text)
s = Score(key=Key("G major"), tempo=132)
s.part("violin", Violin()).add(opening)
s.play().parts["violin"].take(caption="The opening of K. 525 on one violin")
```

At 132 quarters a minute a bar takes 4 × 60 / 132 = 1.82 s, and `take` with no seconds plays to the end of the last note. There are no seconds in the text and no times to add up: the rests and the durations say where each note falls. The third note of bar 4 is an F♯, the only black key in the four bars. On the roll it is the one note on a shaded row.

An octave lower is a move you can already name. `transpose` moves a line by an *interval*, a distance between notes, written as text: `-P8` is an octave down, and chapter 17 explains the letters. It is a second line on the same score, so the same four bars now sound in two octaves:

```python {run continue}
from euterpe import Interval
from euterpe.instruments import StringSection
from euterpe.view import listen

s.part("section", StringSection(players=2)).add(opening.transpose(Interval("-P8")))
listen(s.play(), caption="The violin, with a string section an octave under it")
```

The section thickens the violin without adding a second tune, the effect you measured on the harp and the saw. Chapter 13's section makes each note out of two detuned bows, so it also adds its slow beating.

## Spelling is a bug

G major is the seven letters from G, one of each: G, A, B, C, D, E, and one more. The last one sits a semitone under G, on the black key that has two names, so which? The rule of a key is *one note per letter*, so it has to be F♯: as G♭ there would be two Gs and no F. Here is the opening with that note typed as G♭, against the key:

```python {run continue output=code}
import numpy as np
from euterpe.pitch import Fs5, Gb5
from euterpe.sound import render


def written(tune):
    score = Score(key=Key("G major"), tempo=132)
    score.part("violin", Violin()).add(tune)
    return score


right, wrong = written(opening), written(melody(text.replace("f#", "gb")))
print("same samples:", np.array_equal(render(right.play(), 7.0), render(wrong.play(), 7.0)))
print("same MIDI file:", right.to_midi("build/right.mid").read_bytes() == wrong.to_midi("build/wrong.mid").read_bytes())
print("same MusicXML file:", right.to_musicxml("build/right.xml").read_text() == wrong.to_musicxml("build/wrong.xml").read_text())
key = Key("G major")
print(key.scale.pitches())
for p in (Fs5, Gb5):
    print(p, p in key.scale, key.spell(p.number))
```

The samples are equal to the bit, so no ear could tell. The MIDI files are equal too, since MIDI stores key numbers and has no idea what a note is called. The MusicXML files differ. That is the format notation programs read, and it stores `<step>F</step><alter>1</alter>` for one and `<step>G</step><alter>-1</alter>` for the other. `key.scale` knows that G♭ is not in the key, and `key.spell` turns a number into the name this key gives it, F♯5.

So why call it a bug, if nothing audible breaks? Because a score is read as well as heard. A player sight-reading G major already expects F♯; the wrong line prints a flat sign in front of a G, where the eye expects the plain F that the key has already sharpened. The music of the next chapters also runs on letters. A to F♯ is a third, three letters; A to G♭ is a kind of second, two letters. Those are different things to chapter 17, and move the note up by the same interval and one spelling gives you G and the other A with two flats. A wrong spelling sounds right today and breaks later, which is what bugs do. Euterpe keeps your spelling exactly as you wrote it, so that it can be checked. A later chapter's linter reports this very note.

## Putting it all together

The closing piece is K. 525 from bar 1 to the long G that starts bar 18, 18 bars of the first violin's part, from the same 1883 edition. It stays in G major. `p` is a soft mark from the next note on, and `f!` a loud one; a bare `f` would be the note F. The first ten bars are loud and the next seven soft. The notation has no sign for the violin's trills and grace notes, so they are left out, and one `Violin` plays one string at a time, so the three-note chords of bars 1 and 5 keep only their top note. Bar 18 is held to the end of the bar, so that the excerpt stops on the home note:

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

Then the three octaves, on one line. The violin plays what is written, the section an octave under it, and `PizzicatoStrings`, from chapter 10, two octaves under it, `-P15` being two octaves counted in letters. The three start from one text, so they cannot disagree. The plucked notes fade fast and mark each note's start under the sustained bows. `gain` scales a part's level, and these bring the softer section and pizzicato up against the violin:

```python {run continue name=strings}
from euterpe import Interval, Key, Score
from euterpe.instruments import PizzicatoStrings, StringSection, Violin
from euterpe.view import listen

s = Score(key=Key("G major"), tempo=132, title="Eine kleine Nachtmusik")
s.part("violin", Violin(), gain=0.8).add(k525)
s.part("section", StringSection(players=2), gain=1.2).add(k525.transpose(Interval("-P8")))
s.part("pizzicato", PizzicatoStrings(), gain=1.2).add(k525.transpose(Interval("-P15")))
song = s.play()
listen(song, song.duration, "Eine kleine Nachtmusik, K. 525, bars 1 to 18, in three octaves")
```

Listen for the first second, where three instruments are one rising figure, then for bar 11, where `p` halves the velocity and the bows go softer and darker, as chapter 13 built them. The three lines never leave each other, so all you can hear change is register and timbre, and that is the octave at work.

It is also the arrangement's limit. In Mozart's score the strings stay in octaves for only four bars: from bar 5 the violins, violas and basses split, each on notes of its own, and the music opens up. The lines here sit an octave apart, the one distance this chapter named. Chapter 17 names all the others.

## Summary

- Notes have seven letter names and an octave number that changes at C: C4 is number 60, A4 is number 69 and 440 Hz. `Pitch("A4")` has `.number` and `.freq`.
- An octave is 12 semitones and a doubling of frequency. Every partial of the upper note is a partial of the lower one, so the two fuse and share a name.
- A sharp raises a letter a semitone and a flat lowers it. C♯ and D♭ are one key and two names: `==` compares names, and `sounds_as` compares sounds.
- `melody` reads notes as text, `Score` holds a key and a tempo, `part(...).add(...)` gives a line an instrument, and `play` performs it. A line's `transpose` moves it by an interval.
- A key uses each letter once, so the key decides the spelling: `key.scale` holds its notes and `key.spell(number)` names any number in it. A wrong spelling changes no sample and still changes the music as written.

## Exercises

1. In the octave block, import `Gs5` and change the last `A5` to it, a semitone under the octave. Do the two notes of the third sound still fuse?
2. In the first score block, change `tempo=132` to `tempo=66`. How long is a bar now, and how long are the four bars?
3. In the spelling block, change `key = Key("G major")` to `key = Key("Db major")`. What do the last two lines print, and why?

### Answers

1. No. G♯5 is 830.6 Hz, and its partials miss A4's: its first partial falls 49 Hz from A4's second at 880 Hz, so the pair rubs and beats, and you hear two notes.
2. A bar takes 4 × 60 / 66 = 3.64 s, and the four bars 14.5 s, against 1.82 s and 7.3 s. The text of the tune does not change.
3. `F#5 False Gb5` and `Gb5 True Gb5`. D♭ major has G♭ as its 4th note and no F♯, so the same key on the piano, number 78, now takes the other name. The spelling comes from the key, not from the key on the keyboard.

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
