# Intervals

Chapter 16 kept three lines an octave apart, and an octave is one distance out of many. This is where this chapter ends up, with two lines that are almost never an octave apart:

```python {run echo=false}
# The teaser: the first three bars of the finale, built by the code of this chapter's two named finale
# blocks, which it reads from this file so the two never differ. The blocks' own views are skipped.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import render

text = Path("chapters/17-intervals.md").read_text()
scope = {}
for name in ("lines", "duo"):
    code = re.search(rf"```python \{{[^}}\n]*name={name}\b[^}}\n]*\}}\n(.*?)\n```", text, re.S).group(1)
    exec("\n".join(line for line in code.split("\n") if "listen(" not in line and "display(" not in line), scope)
# Three bars of four beats at 72 bpm.
display(Clip(render(scope["song"], 3 * 4 * 60 / 72), caption="The opening of Bach's Invention No. 1, flute over strings"))
```

Bach's Invention No. 1 in C, BWV 772, written in 1723 to teach a student to play two lines at once. There are two lines and nothing else, so everything you hear is one note against another. A distance between two notes is an *interval*, and this chapter names every one of them, says why some are smooth and others rub, and then uses them to write these two lines.

## Counting letters

An interval has a number and a quality. The number counts letters, with both ends included: C up to E is C, D, E, so a third. C up to C is a unison, a first, and C up to the next C is the octave of chapter 16, an eighth. The quality then says how many semitones that number holds, because the same three letters can hold several. `Interval("M3")` is a major third, and `C4 + Interval("M3")` is the pitch that far up, spelled by its letters.

Unisons, fourths, fifths and octaves take the word *perfect* (`P`), and the others take major (`M`) and minor (`m`), one semitone less. *Augmented* (`A`) is a semitone wider than perfect or major, and *diminished* (`d`) a semitone narrower than perfect or minor. A minus sign goes down, as `-P8` did in chapter 16. Mind the letter A: `Interval("A4")` is an augmented fourth and `Pitch("A4")` is the note at 440 Hz, and each class reads the text its own way. All four thirds of C:

```python {run output=code}
from euterpe import Interval, Pitch
from euterpe.pitch import C4

for name in ("d3", "m3", "M3", "A3"):
    third = Interval(name)
    print(name, third.semitones, C4 + third, third.pretty)
print(Interval.between(C4, Pitch("E#4")), Interval.between(C4, Pitch("F4")))
print(Pitch("E#4").sounds_as(Pitch("F4")))
```

Each quality moves the top note by one semitone and keeps its letter E. The last two lines are why the counting is by letters. C up to E♯ and C up to F are the same five semitones on one key of the piano, and they sound alike, and still the first is an *augmented third* and the second a *perfect fourth*, because E♯ is a kind of E and F is not. This is the point chapter 16 left open: F♯ up to A is a third and G♭ up to A is a second, on the same keys.

Two of those thirds, one note after the other and then together, on chapter 10's harp:

```python {run}
from euterpe import Interval
from euterpe.instruments import Harp
from euterpe.pitch import C4

for name in ("m3", "M3"):
    top = C4 + Interval(name)
    notes = [(0.0, C4, 1.0), (1.0, top, 1.0), (2.0, C4, 2.5), (2.0, top, 2.5)]
    display(Harp().play(notes).take(4.5, f"C4 and {top}, a {Interval(name).pretty}"))
```

One semitone is all that separates them, and the minor third sounds darker than the major one. Chapter 21 builds chords on that difference.

Intervals also add, turn over and stretch:

```python {run output=code}
from euterpe import Interval
from euterpe.pitch import C4, E5

print(Interval("m3") + Interval("M3"))
print(Interval("M3").inverted, Interval("P5").inverted, Interval("A4").inverted)
print(Interval.between(C4, E5), Interval.between(C4, E5).simple, Interval("M10").semitones)
```

A minor third on a major third is a perfect fifth: C to E♭ to G. *Inversion* moves the lower note up an octave, so the two intervals fill an octave between them: C up to E is `M3`, and E up to the next C is `m6`. Their numbers add up to 9 and their semitones to 12, major swaps with minor, augmented with diminished, and perfect stays perfect. A *compound* interval is wider than an octave, and `simple` takes the octaves out, keeping the quality: C4 to E5 is a major tenth, a major third with an octave added. The third bar of the Invention starts on exactly that pair.

## Hearing each one

Names are worth little until you can hear them. Here are the twelve distances within an octave, each one from C4: a violin holds C4 and a flute plays the note above it, two seconds each:

```python {run}
from euterpe import Interval
from euterpe.instruments import Flute, Violin
from euterpe.pitch import C4

names = "m2 M2 m3 M3 P4 A4 P5 m6 M6 m7 M7 P8".split()
flute = Flute().play([(2.0 * i, C4 + Interval(name), 1.8) for i, name in enumerate(names)])
violin = Violin().play([(2.0 * i, C4, 1.8) for i in range(12)])
(flute + violin * 0.8).take(24.5, "Each interval from C4: m2, M2, m3, M3, P4, A4, P5, m6, M6, m7, M7, P8")
```

Listen to how much each pair rubs. The m2 at the start grinds, and so does the M7 near the end, one semitone short of closing the octave. The thirds and sixths are sweet. The P5 and the P8 are so plain that they are almost one note. The A4, the middle of the octave and called the *tritone*, is restless and wants to move. `consonance` is the name for this, and `Interval` gives it three grades:

```python {run output=code}
from euterpe import Interval

for name in ("P5", "M3", "m2"):
    print(name, Interval(name).consonance)
```

The *perfect* consonances are the open ones, the *imperfect* ones the sweet ones, and the rest *dissonant*: they want to go somewhere. The fourth depends on context. `consonance` calls P4 perfect, as its partials do, but when four lines are written together a fourth above the lowest line counts as a dissonance, and chapter 23 follows that rule.

## Transposing

Every interval is also a move. A *subject*, the short tune a piece is built from, can be moved whole by `Line.transpose`, and it keeps its shape because every note moves by the same interval. The Invention's subject is seven notes after a sixteenth's rest, and bar 1 of its upper line finishes it with four eighths. `then` carries a line on inside the same bar, where `+` would start a new one. The figure, followed by itself up a step, and then by itself up a fifth, the distance Bach goes to next:

```python {run}
from euterpe import Interval, Key, Score, display, melody
from euterpe.instruments import Flute

subject = melody("r:s c4 d e f d e c")
figure = subject.then(melody("g4:e c5 b4 c5"))
for name in ("M2", "P5"):
    s = Score(key=Key("C major"), tempo=72)
    s.part("flute", Flute()).add(figure + figure.transpose(Interval(name)))
    display(s, caption=f"The figure, then the same a {Interval(name).pretty} higher")
```

Each is the same tune at a new height: the ear recognises it because the distances are the same. The staffs show what that cost. The major second brings in F♯ and C♯, and the perfect fifth F♯, since the semitone from B to C has to be a semitone from F♯ to G.

Bach's trick for two hands is the same move in time. The lower line waits two beats and enters with the same subject an octave down, which `transpose` writes in one line. This is *imitation*. The flute keeps the upper line and a low string section, chapter 13's, the lower:

```python {run continue}
from euterpe.instruments import StringSection

entry = melody("r:h").then(subject.transpose(Interval("-P8")))
s = Score(key=Key("C major"), tempo=72)
s.part("flute", Flute()).add(figure)
s.part("section", StringSection(players=2)).add(entry)
display(s, caption="Bar 1 of the Invention: the subject, and the subject an octave down, two beats later")
```

Now the catch. Moving by a fixed interval moves every step by the same semitones, and a piece that stays on seven notes often cannot do that. The second half of bar 3 is a run of eight notes, and Bach moves it down a third again and again. Move it down a minor third with `transpose`, then hear Bach's own next step, which opens bar 4:

```python {run continue}
run = melody("g5:s f e d c e d f")
moved = run.transpose(Interval("-m3"))
bach = melody("e5:s d c b4 a c5 b4 d5")
for answer, how in ((moved, "moved down a minor third"), (bach, "as Bach writes it")):
    s = Score(key=Key("C major"), tempo=72)
    s.part("flute", Flute()).add(run.then(answer))
    display(s, caption=f"The run, then the run {how}")
```

`transpose` keeps every step's exact size, so it has to bring in C♯, a note outside the seven the Invention has used so far. Bach's answer stays on the white keys. It keeps the third in letters, and lets the quality change note by note: G down to E is a minor third and E down to C a major one. Number and quality are two separate things, and that is why. Music on a fixed set of notes moves by number.

## Why some are smooth

A note is a stack of partials, as chapter 3 showed, and so two notes are two stacks. Chapter 16 heard the case of the octave, where every partial of the upper note lands on one of the lower. Other intervals line up less often. A saw has all its partials, so two saws on A3, 220 Hz, show which ones meet. First a perfect fifth, then a minor second, each as a sound and as stems, one panel per note, since `f0` can take one fundamental per clip:

```python {run}
from euterpe import Interval
from euterpe.pitch import A3
from euterpe.sound import Saw
from euterpe.view import spectrum

for name in ("P5", "m2"):
    high = (A3 + Interval(name)).freq
    display(((Saw(A3.freq) + Saw(high)) * 0.25).take(3.0, f"Two saws a {name} apart, from A3"))
    clips = (Saw(A3.freq) * 0.5).take(1.0), (Saw(high) * 0.5).take(1.0)
    display(spectrum(*clips, f0=[A3.freq, high], harmonics=12, upto=3000.0, labels=["A3", name],
                     caption=f"The partials of A3 and of the note a {name} above it"))
```

In the fifth, every 3rd partial of A3 meets every 2nd partial of E4, near 660, 1320 and 1980 Hz. That 3 to 2 is the ratio of chapter 2. It is also the note chapter 16 stopped on: A4's third partial is almost exactly E6, a fifth and an octave up. In the minor second no low partials meet. Low down, each stem of the upper note stands right next to one of the lower: 220 Hz against 233 Hz beat 13 times a second, and 440 Hz against 466 Hz 26 times. That roughness is the sound of dissonance.

So for each interval, ask which partials are the first to meet. The block takes the upper note's partials in turn, finds the nearest partial of the lower note, and stops at the first pair closer than 20 cents; `cents` says how far they still miss in equal temperament, the tuning of `Pitch.freq`, and the last column is the grade:

```python {run output=code}
import numpy as np
from euterpe import Interval

print("name lower upper cents grade")
for name in "P8 P5 P4 M6 M3 m3 m6 m7 M2 M7 m2 A4".split():
    interval = Interval(name)
    ratio = 2 ** (interval.semitones / 12)
    upper = np.arange(1, 21)
    lower = np.round(upper * ratio)
    cents = 1200 * np.log2(upper * ratio / lower)
    n = np.argmax(np.abs(cents) < 20)
    print(f"{name:4} {lower[n]:5.0f} {upper[n]:5} {cents[n]:5.1f} {interval.consonance}")
```

Low partials are the loud ones, so the smaller these two numbers, the more of the sound lines up: 2 and 1 for the octave, 3 and 2 for the fifth, 5 and 4 for the major third. The dissonances wait until the 9th or the 15th partial, where a saw has little level left. The order follows the grades, with one exception, and it shows what this measure leaves out. The tritone meets at 7 and 5, yet it sounds rough: well below that, its lower note's 3rd partial and its upper note's 2nd miss by 1200 log2(3 / (2 × 2^(6/12))) = 102 cents, about a semitone. Partials that meet make an interval smooth, and partials that nearly meet make it rough.

## Just and equal

The cents column has a sting: only the octave is at 0. The major third's two partials meet at 13.7 cents apart, and so they beat. Twelve equal semitones can't be whole-number ratios, because no power of 2^(1/12) other than the octaves is a ratio of whole numbers. Tuning that uses the ratios themselves is called *just*: `JustIntonation(C4)` keeps C4 and sets each note by a ratio from it, and `EqualTemperament()` is the default, every note `Pitch.freq` gives. A tuning's `freq` answers for a spelled pitch. Here is E4 in both, then the 5th partial of C4 and the 4th partial of E4, the pair that should meet, and the beats between them in Hz:

```python {run output=code}
from euterpe import EqualTemperament, JustIntonation
from euterpe.pitch import C4, E4

for tuning, name in ((EqualTemperament(), "equal"), (JustIntonation(C4), "just")):
    partial5, partial4 = 5 * tuning.freq(C4), 4 * tuning.freq(E4)
    beats = partial4 - partial5
    print(f"{name:6} {tuning.freq(E4):.2f} {partial5:.1f} {partial4:.1f} {beats:.1f}")
```

Moving E4 down by 2.6 Hz puts its 4th partial right onto C4's 5th. Now `Score` takes the tuning, and one sustained third plays in each, written `<c4 e4>:w`: angle brackets sound notes together. An organ is the instrument for this: chapter 12's organ builds a note from sines at exact multiples and holds them at one level, so nothing moves but the beat. `"008888800"` pulls out the first five. Under each player is the sound through chapter 5's `BandPass`, centred between the two partials so that nothing else gets through:

```python {run}
from euterpe import EqualTemperament, JustIntonation, Key, Score, melody
from euterpe.instruments import Organ
from euterpe.pitch import C4
from euterpe.sound import BandPass
from euterpe.view import listen

for tuning, name in ((EqualTemperament(), "equal"), (JustIntonation(C4), "just")):
    s = Score(key=Key("C major"), tempo=60, tuning=tuning)
    s.part("organ", Organ(drawbars="008888800")).add(melody("<c4 e4>:w"))
    display(listen(s.play(), 4.0, f"C4 and E4 on an organ, in {name} tuning"))
    near = BandPass(s.play(), 1313.0, q=40.0).take(1.0)
    display(near.waveform(caption=f"One second of the band near 1313 Hz, in {name} tuning"))
```

Listen high up: the equal third shimmers, and its band swells 10 times in that second. The just third is still, and its band is flat.

So why does every piano use the other one? Because just tuning fits one key. `JustIntonation(C4)` sets D at 9/8 and A at 5/3, so the fifth from D up to A is (5/3) / (9/8) = 40/27, which is 680 cents instead of a pure fifth's 702, and it howls. In this tuning G♯ and A♭ are even two frequencies, so a keyboard would need more keys. Equal temperament spreads the error evenly: each fifth is 2 cents narrow, each major third 13.7 cents wide, and every key is equally usable and equally a little out of tune. Chapter 18 needs that freedom. The rest of this book plays in equal temperament.

## Putting it all together

The closing piece is the first seven bars of Invention No. 1, from the Bach-Gesellschaft edition of the 19th century, and a held G to close, which is not in Bach: bar 8 goes on, and this excerpt stops on the note bar 7 has been working towards. The notation has no sign for the trills and mordents, so they are left out. The upper line starts with the figure. Its bar 7 enters with the subject a fifth up, and the bars between are spelled out, because they are the kind of move `transpose` cannot make: even bar 2, the figure a fifth up, replaces the sixteenth's rest with a D and keeps F where `transpose` gave F♯:

```python {run name=lines}
from euterpe import Interval, melody

subject = melody("r:s c4 d e f d e c")
figure = subject.then(melody("g4:e c5 b4 c5"))
right = figure + melody("""
    d5:s g4 a b c5 a4 b g d5:e g f g |
    e5:s a g f e g f a g f e d c e d f |
    e d c b4 a c5 b4 d5 c b4 a g f# a g b |
    a:e d4 c5:e. d:s b4 a g f# e g f# a |
    g:s b a c5 b4 d5 c e d b4:t c5 d:s g b4:e a:s g""")
right += melody("g4:e r r:q").then(subject.transpose(Interval("P5")))
right += melody("g4:w")
```

A `t` is a thirty-second, half a sixteenth. The lower line is built the same way. It enters after a two-beat rest with the subject an octave down, and again a fourth down in bar 2. Bar 7 takes the whole figure down a perfect eleventh, an octave and a fourth, and that one transposition, F♯3 included, is exactly what Bach wrote:

```python {run continue name=duo}
from euterpe import Key, Score, display
from euterpe.instruments import Flute, StringSection
from euterpe.view import listen

left = melody("r:h").then(subject.transpose(Interval("-P8")))
left += melody("g3:e g2 r:q").then(subject.transpose(Interval("-P4")))
left += melody("""
    c4:e b3 c4 d e g3 a b |
    c4 e3 f# g a b c4:q~ |
    c4:s d3 e f# g e f# d g:e b2 c3 d |
    e:e f# g e b2:e. c3:s d:e d2""")
left += figure.transpose(Interval("-P11")) + melody("g3:w")
s = Score(key=Key("C major"), tempo=72, title="Invention No. 1")
s.part("flute", Flute()).add(right)
s.part("section", StringSection(players=2)).add(left)
song = s.play()
display(s.notation(bars=(1, 4), caption="Bars 1 to 4 of the two lines"))
listen(song, caption="Bach, Invention No. 1, BWV 772, bars 1 to 7, flute over strings")
```

The `~` is a *tie*: it joins a note to the next one of the same pitch, so the C4 at the end of bar 4 holds into bar 5. At 72 quarters a minute a bar takes 3.33 s. Listen in bar 1, from 1.67 s, for the strings entering with the tune the flute just played, the octave you already know, and in bar 2 for the fifth above that tune and the fourth below it. Listen for the long downward runs of bars 3 and 4, each one a third under the last, while the strings climb under them in eighths. Then try hearing it vertically: the third bar starts on the major tenth from the first section of this chapter, C4 under E5, and through the seven bars the two lines keep landing on thirds, sixths and tenths and passing through seconds on the way to them. Every pair of notes here is an interval you can now name.

There is something this chapter cannot explain. For three bars the Invention uses only seven of the twelve notes, the white keys. The first black key, F♯, comes in bar 4. From there on the music leans on it, and bar 7 sounds as if it has arrived somewhere new. Why those seven, and what does one new note change? Chapter 18.

## Summary

- An interval has a number, which counts letters with both ends included, and a quality, which says how many semitones it holds. `Interval("M3")`, `p + Interval("M3")` and `Interval.between(p, q)` name, apply and measure one.
- C to E♯ and C to F sound alike and are a third and a fourth, because the number counts letters and not semitones.
- `.inverted` fills the octave: the numbers add up to 9 and the semitones to 12. `.simple` takes the octaves out of a compound interval, and `.semitones` and `.pretty` read it.
- `.consonance` grades an interval as perfect, imperfect or dissonant. Consonance follows the partials: the lower the partials that meet, the smoother the sound, and partials that nearly meet are what rubs.
- `JustIntonation(C4)` sets notes by ratios from one tonic, so a third does not beat; `EqualTemperament()`, the default, makes every key usable and leaves a major third 13.7 cents wide, and it beats. `Score(tuning=...)` picks one.
- `line.transpose(interval)` moves a line by an interval and keeps its exact shape, and `line.then(other)` carries a line on inside its last bar. Moving by a third within seven notes keeps the number and changes the quality, so that kind of line is spelled out.

## Exercises

1. In the block with the four thirds, change `C4 + third` to `D4 + third`, importing `D4`. What are the four thirds of D now?
2. In the block that prints E4 in each tuning, change `(JustIntonation(C4), "just")` to `(Pythagorean(C4), "pure fifths")`, importing `Pythagorean` from `euterpe`, a third tuning that builds every note from pure fifths. How fast does the third beat now, and why?
3. In the closing piece, change `Score(key=Key("C major"), tempo=72, title="Invention No. 1")` by adding `tuning=JustIntonation(C4)`, importing `JustIntonation` from `euterpe` and `C4` from `euterpe.pitch`. What improves, and where does it go wrong?

### Answers

1. `Fb4`, `F4`, `F#4` and `F##4`: each keeps the letter F, two letters above D. The semitones are the same as from C, 2, 3, 4 and 5, since the interval decides them and the starting note does not.
2. E4 is now 331.1 Hz, 81/64 of C4, a stack of four pure fifths. Its 4th partial is 1324.4 Hz against C4's 5th at 1308.1 Hz, so it beats at 16.3 Hz, faster than equal temperament's 10.4. A tuning built on pure fifths gets its thirds worse.
3. The thirds and tenths sound stiller. But D is 9/8 and A is 5/3, so D to A is the 680-cent fifth from the section on tuning: D3 falls under A4 at the end of bar 5, and for that sixteenth it sounds sour. The one tuning cannot make every fifth pure as well as every third, which is why the piece, and the book, stays in equal temperament.

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
