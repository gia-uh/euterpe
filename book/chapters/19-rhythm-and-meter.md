# Rhythm and meter

Chapter 18 stopped on one note of Joy to the World, a top D that starts between two beats and holds across the next one. This chapter is about notes like that. Here is where it ends up: a left hand as even as a march, and a right hand that keeps arriving just ahead of it:

```python {run echo=false}
# The teaser: bars 4 to 8 of the finale, built by this chapter's three named blocks, read from this file.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import render

text = Path("chapters/19-rhythm-and-meter.md").read_text()
scope = {}
for name in ("strain", "hands", "rag"):
    code = re.search(rf"```python \{{[^}}\n]*name={name}\b[^}}\n]*\}}\n(.*?)\n```", text, re.S).group(1)
    exec("\n".join(line for line in code.split("\n") if "listen(" not in line and "display(" not in line), scope)
bar = 2 * 60 / 76
samples = render(scope["song"], 8 * bar)[int(3.75 * bar * 48000):]
display(Clip(samples, caption="The Entertainer: the first phrase of its tune"))
```

Scott Joplin's The Entertainer, published in St. Louis in 1902. What makes it a rag is when its notes start, and this chapter gives you every tool it takes to write that down: lengths, beats, the strong and weak places in a bar, and the distance between a written time and a played one.

## Fractions of a whole

Chapter 16 said that `q` is a quarter of a whole note, and every other length works the same way: `w h q e s t` are 1, 1/2, 1/4, 1/8, 1/16 and 1/32. A length does not say how many seconds a note takes, since that depends on the tempo. It says what fraction of a whole note the note takes. A dot adds half again. A tie, `~`, joins a note to the next note of the same pitch, and so adds any two lengths. `Line.duration` gives the sum:

```python {run output=code}
from euterpe import melody

for text in ("c5:q", "c5:e", "c5:q.", "c5:e.", "c5:q~ c5:s"):
    print(f"{text:12}", melody(text).duration)
```

Those are exact fractions, Python's `Fraction`, and the last line is a length no dot can write. A dot is what gives the first line of Joy to the World its limp. Here it is with even notes, then as Mason wrote it. The notes are the same, and a `:e.` followed by a `:s` takes the time of two eighths and divides it 3 to 1:

```python {run}
from euterpe import Key, Meter, Score, display, melody
from euterpe.instruments import Harp

for how, tune in (("even", "d5:q c#:e b4 | a:q g | f#:q e | d:h"),
                  ("dotted", "d5:q c#:e. b4:s | a:q. g:e | f#:q e | d:h")):
    s = Score(key=Key("D major"), meter=Meter("2/4"), tempo=116)
    s.part("harp", Harp()).add(melody(tune))
    display(s, caption=f"The first line of Joy to the World, {how}")
```

A *bar* is the time between two of the `|` you have been typing, and its length is fixed by the *meter*, as the next sections say. Since each length is exact, a bar either adds up or it doesn't, and `lint` can check it. An `r` is a rest, which takes its time silently and counts in the sum. Here are five quarters in a bar that holds four:

```python {run output=code}
from euterpe import Meter, Score, melody
from euterpe.instruments import Harp

s = Score(meter=Meter("4/4"), tempo=90)
s.part("harp", Harp()).add(melody("c5:q d e f g | c5:h r"))
for finding in s.lint().errors:
    print(finding.rule, finding.place, finding.message)
```

`N-MEASURE` names the bar and the beat where it goes wrong. The score still plays: a mistake in bars is a mistake in writing, and an error from `lint` is how you hear of it.

## Tuplets

Halving gives every length so far, and halving alone never gives a third. `3[...]` plays three notes in the time of two, so three eighths in brackets last one quarter and each takes 1/12. A run of eight notes, then the same stretch of time cut into twelve:

```python {run}
from euterpe import Key, Meter, Score, display, melody
from euterpe.instruments import Harp

for how, run in (("eighths", "c5:e d e f g f e d"),
                 ("triplets", "3[c5:e d e] 3[f g a] 3[g f e] 3[d e d]")):
    s = Score(key=Key("C major"), meter=Meter("4/4"), tempo=84)
    s.part("harp", Harp()).add(melody(run))
    display(s, caption=f"One bar in {how}, {melody(run).duration} of a whole note")
```

The first take walks in twos and the second rolls in threes, and both land on the next bar at the same moment. That is the reason for `Fraction`. Two triplets of eighths must fill a half note exactly. Walk through them in floating point, one note at a time, as a player's position does, and they don't:

```python {run output=code}
from fractions import Fraction
from euterpe import melody

print(melody("3[c5:e d e] 3[f g a]").duration == Fraction(1, 2))
place = 0.0
for _ in range(6):
    place += 1 / 12
print(place, place == 1 / 2)
```

The difference is about 6 × 10^−17 of a whole note and no ear could find it, but a program asking whether a bar is full, or whether two notes start together, gets the wrong answer. A score keeps written time in fractions, and turns it into seconds only when it plays.

## Beat and meter

Tap your foot to a piece and you are tapping its *beat*. `Meter("3/4")` is a time signature, the two numbers at the start of a staff: each bar holds three quarters. In `Meter("6/8")` each bar holds six eighths, the same length of bar, and yet it is not the same thing. 3/4 is *simple*: three beats, each dividing in two. 6/8 is *compound*: two beats, each dividing in three.

Here are six eighths on chapter 14's kit in each meter. `drums` writes a kit's grid into a score, in the characters of `Kit.pattern`, and `X` is a harder stroke than `x`. A tempo counts the meter's beat, so 120 quarters and 80 dotted quarters are the same eighth, 0.25 s long. Same drums, same speed:

```python {run}
from euterpe import Meter, Score, display, drums
from euterpe.instruments import Kit

for meter, tempo, hats in (("3/4", 120, "Xx Xx Xx |"), ("6/8", 80, "Xxx Xxx |")):
    s = Score(meter=Meter(meter), tempo=tempo)
    s.part("kit", Kit()).add(drums({"kick": "x..... |" * 4, "hihat": hats * 4}, step="e"))
    display(s, caption=f"Six eighths in {meter}, at {tempo} beats a minute")
```

Count along and you count 1 2 3 on the first and 1 2 on the second, at the same speed of eighths. `Meter` holds what you counted. `bar` is the bar's length, `beats` how many beats it holds, `beat` the length of one, and `compound` is true when the top number is divisible by 3 and above 3. `strength` ranks a place in the bar, with 0 for the strongest. Each line prints those in that order, with the ranks of the six eighths last:

```python {run output=code}
from fractions import Fraction
from euterpe import Meter

for text in ("3/4", "6/8"):
    m = Meter(text)
    print(text, m.bar, m.beats, m.beat, m.compound, [m.strength(Fraction(i, 8)) for i in range(6)])
```

Same bar, 3/4 of a whole note, and other ranks. In 3/4 the strong eighths are the 1st, 3rd and 5th. In 6/8 they are the 1st and 4th. A strong place is where a listener expects something to happen, and that expectation is what the rest of this chapter plays against. When a score plays, it adds a little level on a downbeat and takes the same from the weakest places, so even a plain line leans towards its meter. The harder strokes in these grids are written by hand, on top of that.

## Syncopation

A note is *syncopated* when it starts in a weak place and holds across a stronger one. The ear expects a new note on the strong place and gets the old one still sounding. Two takes of one figure on nearly the same notes. The first is on the beat. The second cuts the bar's eight sixteenths into 3, 3 and 2, so two of its three high Cs miss the beat, and the last one ties across the bar line. `T-SYNCOPATION` measures this, by the index of Longuet-Higgins and Lee: for each note, how many ranks stronger is the strongest place it holds across than the place it starts on, added up over the part:

```python {run}
from euterpe import Key, Meter, Score, display, melody
from euterpe.instruments import ElectricPiano

for how, figure in (("on the beat", "e4:e c5 e4 c5 | c5:h"),
                    ("across the beat", "e4:s c5:e e4:s c5:e e4:s c5:s~ | c5:h")):
    s = Score(key=Key("C major"), meter=Meter("2/4"), tempo=76)
    s.part("right", ElectricPiano()).add(melody(figure))
    display(s, caption=f"{how}: syncopation index {s.lint().value('T-SYNCOPATION'):.0f}")
```

In 2/4 the sixteenths rank 0 3 2 3 1 3 2 3. The first high C starts on rank 3 and holds across rank 2, for 1. The tied one starts on rank 3 and holds across the bar line, rank 0, for 3.

The first take is a child's tune. The second is the start of The Entertainer. A rag comes in sections called *strains*, each 16 bars, and here is the right hand of its first strain on chapter 12's electric piano, spelled from Joplin's edition. `hook`, `fall` and `top` are the figures that come back, and `strain` strings them together with the bars that come once. Notes in angle brackets strike together, and most of these have the tune on top with an octave under it. Its first two notes come before the first full bar, and that is a *pickup*: `pickup=Fraction(1, 8)` tells the score that bar 1 holds only that eighth:

```python {run name=strain}
from fractions import Fraction
from euterpe import Key, Meter, Score, display, melody
from euterpe.instruments import ElectricPiano

hook = melody("e4:s c5:e e4:s c5:e e4:s c5:s~ | c5:q~ c5:s <c5 e5 c6> <d5 f5 d6> <d#5 f#5 d#6>")
fall = melody("<e5 g5 e6>:s <c5 e5 c6> <d5 f5 d6> <e5 g5 e6>~ <e5 g5 e6> <b4 d5 b5> <d5 f5 d6>:e")
lead = melody("d4:s d#")
close = melody("<c5 e5 c6>:h")
turn = melody("""e4:s c5:e e4:s c5:e e4:s c5:s~ | c5:q~ c5:e <a4 c5 a5>:s <g4 c5 g5> |
    <f#4 c5 f#5> <a4 a5> <c5 c6> <e5 e6>~ <e5 e6> <d5 d6> <c5 c6> <a4 a5> | <d5 f5 d6>:q. d4:s d#""")
top = melody("<e5 e6>:s <c5 c6> <d5 d6> <e5 e6>~ <e5 e6> <c5 c6> <d5 d6> <c5 c6>")
strain = (hook + fall + melody("<c5 e5 c6>:q. d4:s d#") + turn
          + hook + fall + melody("<c5 e5 c6>:q. <c5 c6>:s <d5 d6>") + top * 2 + fall)
s = Score(key=Key("C major"), meter=Meter("2/4"), tempo=76, pickup=Fraction(1, 8))
s.part("right", ElectricPiano()).add(lead + strain + close)
display(s, caption="The first strain, right hand alone")
```

Bar after bar has the same habit: a note arrives a sixteenth before the beat, usually the top of a figure, and holds over it. Bar 17 of Joy to the World was one syncopation. A piece that does it bar after bar is a *rag*, ragged time, and the habit needs a steady thing to lean against, which is the next layer.

The left hand plays what a march plays: a low note on each beat, and a chord between them. Joplin's edition has it in eighths under the whole strain, and `coda` and `home` are its last four bars, kept apart for the block after this one; `home` is the bar that ends on the low C. The clef on a part sets the staff it is written on:

```python {run continue name=hands}
from euterpe import display, melody
from euterpe.instruments import ElectricPiano
from euterpe.view import listen

march = melody("""c3:e <e3 g3 c4> <g2 g3> <g3 bb3 c4> | <f2 f3> <a3 c4> <e2 e3> <g3 c4> |
    g2 <e3 g3 c4> g2 <f3 g3 b3>""")
home = melody("<c3 g3 c4>:e <g2 g3> <c2 c3> r")
coda = melody("""<c3 c4>:e <g3 c4 e4> <bb2 bb3> <g3 c4 e4> | <a2 a3> <a3 c4 f4> <ab2 ab3> <ab3 c4 f4> |
    <g2 g3> <g3 c4 e4> g2 <g3 b3>""")
under = (march + melody("""c3:e <e3 g3 c4> <e3 g3 c4> <g3 b3> |
    c3 <e3 g3 c4> <g2 g3> <g3 bb3 c4> | <f2 f3> <a3 c4> <e2 e3> <eb2 eb3> |
    <d2 d3> <d3 f#3 a3 c4> d3 <f#3 a3 c4> | <g3 b3> <g2 g3> <a2 a3> <b2 b3>""")
         + march + melody("c3:e <e3 g3 c4> <g3 c4 e4> r") + coda)
s.part("left", ElectricPiano(), gain=0.5, clef="bass").add(melody("r:e") + under + home)
display(s.notation(bars=(1, 5), caption="The first phrase of the strain, both hands"))
listen(s.play(), 7.0, "The first phrase of the strain, both hands")
```

## Tempo

So far a tempo has been one number. A musician also slows down at the end of something. `s.ramp(bar, bars, to)` moves the tempo evenly from where it is to `to`, over that many bars: below the current tempo it is a *ritardando*, and above it an *accelerando*. The strain's last four bars with both hands, at 76 throughout and then slowing over bars 3 and 4 to 46:

```python {run continue}
from euterpe import Key, Meter, Score, display
from euterpe.instruments import ElectricPiano

for to, how in ((76, "in time"), (46, "with a ramp over its last two bars")):
    s = Score(key=Key("C major"), meter=Meter("2/4"), tempo=76)
    s.part("right", ElectricPiano()).add(top * 2 + fall + close)
    s.part("left", ElectricPiano(), gain=0.5, clef="bass").add(coda + home)
    s.ramp(3, 2, to=to)
    display(s, caption=f"The strain's last four bars, {how}")
```

Listen to the second take stretch into its last chord. How long do those two slowing bars last? A tempo that moves evenly from a to b beats a minute over n beats takes the integral of 60 / tempo over those beats, which comes out as 60 n ln(a / b) / (a − b) seconds. Here that is, with `to` still holding the loop's last value, against the tempo map the score plays from. Its `seconds` takes a place in whole notes, and bars 3 and 4 run from 1 to 2:

```python {run continue output=code}
import math

a, b, n = 76, to, 4
print(60 * n * math.log(a / b) / (a - b))
tempo = s.tempo_map()
print(tempo.seconds(2) - tempo.seconds(1))
print(60 * n / a)
```

The two agree, and the last line is the same bars with no ramp: the slowing adds 0.86 s.

## Swing

A written time goes through three steps on its way to seconds, in this order: swing, tempo, humanization. *Swing* comes first because it changes where a beat's inside falls. `Swing(ratio, unit)` takes pairs of units and gives the first one `ratio` of the pair. At the default, 2/3 on eighths, the second eighth of each beat moves late, to 2/3 of the way through the beat, and beats themselves stay where they are. `Performance` holds how a score is played, as against how it is written: `Score(performance=...)` sets it, and `s.play(performance=...)` overrides it for one take. So here is a groove of the book's own, a ride cymbal over a walking bass, chapter 10's bass guitar in quarters. The ride's pattern is the jazz drummer's, with its third and last strokes on the off-beat eighths:

```python {run continue}
from fractions import Fraction
from euterpe import Meter, Performance, Score, Swing, display, drums, melody
from euterpe.instruments import BassGuitar, Kit

m = Meter("4/4")
ride = drums({"ride": "x.xx x.xx |" * 4, "hihat": "..x. ..x. |" * 4}, step="e")
walk = melody("c2:q e g a | bb a g e | f a c3 a2 | g b d3 b2")
for how, swing in (("straight", None), ("swung", Swing())):
    s = Score(meter=m, tempo=132, performance=Performance(swing=swing))
    s.part("kit", Kit()).add(ride)
    s.part("bass", BassGuitar()).add(walk)
    display(s, caption=f"The groove {how}")
print(Swing().moved(Fraction(1, 8), m))
```

The staffs are the same and the two sound like two styles: the first is a march and the second is jazz. `moved` says where a written place goes, here the second eighth, from 1/8 of a whole note to the 1/6 it prints. Nothing but those few ride strokes moved, and only by 1/6 − 1/8 = 1/24 of a whole note. Each bass note is on a beat, so swing leaves it where it was. Joplin's rag stays straight here: his edition's only word on how to play it is the heading, Not fast.

## Humanize

Everything so far starts on its exact time, and no player does. `Humanize(timing, velocity)` adds a seeded Gaussian draw to each note's start and velocity. The defaults have standard deviations of 8 ms and 0.04, each clipped at 3 of them. The same bars with it off and on. Then the block reads what was played: `play` returns the audio, its `parts` hold each part's sound by name, their `notes` are in time order, and a note's `time` is its start in seconds. It prints the starts of the right hand's second to fifth notes, exact and then under two seeds:

```python {run continue}
from euterpe import Humanize, Key, Meter, Performance, Score, display, melody
from euterpe.instruments import ElectricPiano
from euterpe.view import listen

s = Score(key=Key("C major"), meter=Meter("2/4"), tempo=76)
s.part("right", ElectricPiano()).add(hook + fall)
s.part("left", ElectricPiano(), gain=0.5, clef="bass").add(march)
off, on = Performance(), Performance(humanize=Humanize())
display(listen(s.play(performance=off), caption="The same bars with Humanize off"))
display(listen(s.play(seed=1, performance=on), caption="The same bars with Humanize on"))
for performance, seed in ((off, 0), (on, 1), (on, 2)):
    take = s.play(seed=seed, performance=performance)
    print([round(note.time, 3) for note in take.parts["right"].notes[1:5]])
```

The first line is on an exact grid, and with `humanize` left at None no random draw is made at all. The other two give each note its own small error, which is different under each seed and the same every time under one, so a piece renders to the same samples every time. Listen for the difference in the attacks of the chords, where notes that started as one now spread by a few milliseconds.

## Putting it all together

The closing piece is the introduction and first strain of The Entertainer as John Stark & Son printed it in St. Louis in 1902: this chapter's two hands, with four bars added in front and one difference at the end. Joplin's strain is played twice, and the second time its last bar runs on into the next strain, so here the last bar closes on a held chord, and the ritardando is ours. The score doubles his low notes on chapter 10's pizzicato strings, where `at=5` starts the part at bar 5, with light humanizing over all of it. There is no `pickup` here: the introduction's fourth bar has room for those two sixteenths, so they are simply the end of it. Its first three bars are one falling figure, played in octaves by both hands, each time an octave down:

```python {run continue name=rag}
from euterpe import Humanize, Interval, Key, Meter, Performance, Score, display, melody
from euterpe.instruments import ElectricPiano, PizzicatoStrings
from euterpe.view import listen

fanfare = melody("d6:s e c a5~ a b g:e | d5:s e c a4~ a b g:e | d4:s e c a3~ a b a ab")
right = fanfare + melody("g3:e r <g4 b4 d5 g5> d4:s d#") + strain + close
left = fanfare.transpose(Interval("-P8")) + melody("g2:e r <g1 g2> <g3 b3>") + under + home
low = melody("""c3:e r g2 r | f r e r | g r g r | c3 r r r | c3 r g2 r | f r e eb | d r d3 r | r g2 a b |
    c3 r g2 r | f r e r | g r g r | c3 r r r | c3 r bb2 r | a r ab r | g r g r | c3 g2 c2 r""")
s = Score(key=Key("C major"), meter=Meter("2/4"), tempo=76, title="The Entertainer",
          performance=Performance(humanize=Humanize(timing=0.005, velocity=0.03)))
s.part("right", ElectricPiano()).add(right)
s.part("left", ElectricPiano(), gain=0.5, clef="bass").add(left)
s.part("low", PizzicatoStrings(), gain=0.8, clef="bass").add(low, at=5)
s.ramp(19, 2, to=46)
song = s.play(seed=7)
display(s.notation(bars=(1, 8), caption="The introduction and the first phrase of the strain"))
listen(song, caption="Joplin, The Entertainer, introduction and first strain, electric piano over pizzicato strings")
```

At 76 quarters a minute a bar takes 2 × 60 / 76 = 1.58 s, so the strain's first note comes at 6.3 s. Listen to the introduction first: both hands play one line, with no chord to mark a beat, and the A in each figure holds across the middle of the bar. Then listen to the two hands from 6.3 s. The left keeps its low note on every beat, and the right keeps slipping in a sixteenth ahead of one. Listen in bars 17 and 18, from 25 s, where a top E comes early twice, and for the pizzicato strings under the low notes. From bar 19, at 28 s, the ramp stretches the last two bars into the chord.

The rhythm is now written down: every length in that score is a fraction, each note has its strong or weak place, and a performance turns it all into seconds. What this chapter cannot say is why these notes. It has told you when the top C of the hook starts and nothing about why a climb to it, and that long fall back from it, stay in your head after one hearing. Rhythm and pitch are both written, and a list of them is not yet a tune. What makes one a melody? Chapter 20.

## Summary

- A length is a fraction of a whole note, kept as an exact `Fraction`. A dot adds half again, a tie, `~`, joins two notes of one pitch and adds their lengths, and a rest takes time silently. `N-MEASURE` reports a bar that doesn't add up.
- `3[...]` is three in the time of two. Its sums are exact, where the same running total in floats is not.
- `Meter` says how a bar divides: `beats`, `beat`, `compound` and `strength`. 3/4 is three beats of two eighths, and 6/8 two beats of three, in the same length of bar. A tempo counts the beat.
- `drums` writes a kit's grid into a score.
- A note that starts in a weak place and holds across a stronger one is syncopated. `T-SYNCOPATION` adds up by how many ranks. `Score(pickup=...)` lets notes come before the first full bar.
- `s.ramp(bar, bars, to)` moves the tempo evenly, and n beats from a to b take 60 n ln(a / b) / (a − b) seconds. `s.tempo_map().seconds` reads the place of any written time.
- `Performance` holds how a score is played. `Performance(swing=Swing())` moves off-beats and leaves beats alone. `Performance(humanize=Humanize())` gives each note a small seeded error, and the same seed gives the same samples.

## Exercises

1. In the block with `s.ramp(3, 2, to=to)`, change `46` to `120`. How long do the two bars take now, and what is this ramp called?
2. In the swing block, change `Swing()` to `Swing(3 / 4)`. Where does the second eighth start now, and what does the groove sound like?
3. In the closing piece, add `swing=Swing(unit=Fraction(1, 16))` to the `Performance`, importing `Swing` from `euterpe` and `Fraction` from `fractions`. What happens to the rag's sixteenths, and which notes stay where they were?

### Answers

1. 60 × 4 × ln(76 / 120) / (76 − 120) = 2.49 s, against 3.16 s with no ramp. It is an accelerando, and it also pushes the last chord forward.
2. At 3/16 of a whole note, 3/4 of the way through the beat. The off-beat stroke is now a sixteenth before the next beat, as a dotted eighth and a sixteenth would be. It sounds choppier, nearer to a march's dotted rhythm.
3. In each pair of sixteenths the first gets 2/3 and the second 1/3, so the right hand limps and the sixteenth before the beat comes later and closer to it. Every eighth stays, so from bar 5 on the left hand doesn't move. It has become another style of piece, since the printed sixteenths are even.

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
