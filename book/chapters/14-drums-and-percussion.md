# Drums and percussion

A string or a column of air has harmonics in neat ratios, so it has a clear pitch. A drum head, a cymbal or a metal bar vibrates in modes at ratios no one chose, and most of the sound is in the first fraction of a second. That makes percussion the easiest family to synthesize with the units of Part I: a sine whose pitch falls, a burst of filtered noise, a few decaying modes. This chapter builds a drum kit from those, then timpani, then four instruments of tuned bars, and plays something known on each one. This is where it ends up:

```python {run echo=false}
# The teaser: the start of the finale, built by the code of this chapter's last section, which it
# reads from this file so the two never differ. The block's own player is skipped.
import re
from pathlib import Path

from euterpe.sound.clip import Clip
from euterpe.sound.core import RATE, render

text = Path("chapters/14-drums-and-percussion.md").read_text()
scope = {}
code = re.search(r"```python \{[^}\n]*name=finale\b[^}\n]*\}\n(.*?)\n```", text, re.S).group(1)
exec("\n".join(line for line in code.split("\n") if ".take(" not in line), scope)
display(Clip(render(scope["song"], 16.0)[6 * RATE:], caption="The celesta's entry in the chapter's finale"))
```

Tchaikovsky's *Dance of the Sugar Plum Fairy*, on the celesta, the instrument it made famous: a keyboard of struck steel plates, built in this chapter, over chapter 10's plucked strings.

## Struck

Every instrument of this chapter is a `Struck`, a subclass of the `Instrument` of chapter 9. A struck instrument never sustains: each hit dies on its own and rings past its written duration, unless a new hit on the same drum stops it, as a stick does to a drum head still moving. A drum's tuning is `tune`, in Hz: a note made without a pitch plays at that tuning, and a pitch given to one hit retunes that hit alone. Three techniques make notes, the three every drummer learns:

- `hit(at, velocity)`: one stroke at time `at`;
- `roll(at, length, velocity, end, rate)`: a *roll*, strokes so fast they blur into one sustained sound, `rate` times a second for `length` seconds, the velocity moving in a straight line from `velocity` to `end`;
- `flam(at, velocity, grace)`: a *flam*, a soft *grace* stroke at half the velocity `grace` seconds early (0.025 s by default), then the stroke, which sounds thicker than one.

The *snare* drum, the one a drummer keeps between the knees, plays a roll (`rate` is 20 strokes a second by default) and a flam:

```python {run}
from euterpe.instruments import Snare

snare = Snare()
snare.play(snare.roll(0.0, 1.0, velocity=0.2, end=0.8, rate=20.0) + snare.flam(1.5)).take(2.2, "A snare roll growing for 1 s, then a flam")
```

The roll's twenty strokes grow from 0.2 to 0.8; the flam's grace stroke comes 25 ms before its stroke.

## The kick

The *kick*, or bass drum, is the large drum on the floor, struck by a beater on a pedal. When the beater hits its head, it pushes the head in and stretches it, and a stretched membrane vibrates faster. As the head settles, its pitch falls to its resting tuning. `Kick` models exactly that: a sine whose frequency starts at `tune * sweep` and falls to `tune`, with time constant `drop`, under a decay, plus 4 ms of high-passed noise for the beater's click (chapter 5's `HighPass` on chapter 6's `WhiteNoise`).

```python {run}
from euterpe.instruments import Kick

kick = Kick(tune=50.0, sweep=3.0, drop=0.04)
display(kick.play(kick.hit(0.0, velocity=1.0)).take(0.6, "One kick, falling from 150 Hz to 50 Hz"))
```

The spectrum's brightest line starts high and bends down to 50 Hz in the first tenth of a second. The ear does not hear the fall as a glide: it is too fast, and it hears a punch instead. This is chapter 4's kick, with a beater's click added.

```python {run echo=false}
# Check the claim above: the strongest frequency starts near 150 Hz and settles at 50 Hz.
import numpy as np
from euterpe.instruments import Kick
from euterpe.sound.core import RATE, render

def strongest(x):
    return np.fft.rfftfreq(len(x), 1 / RATE)[np.argmax(np.abs(np.fft.rfft(x * np.hanning(len(x)))))]

kick = Kick(tune=50.0, variation=0.0)
x = render(kick.play(kick.hit(0.0, velocity=1.0)), 0.4)
assert strongest(x[: RATE // 50]) > 100 and abs(strongest(x[RATE // 10 : 3 * RATE // 10]) - 50) < 10
```

## The snare

The snare has *wires* stretched under its lower head, which buzz against it. Its head is a circular membrane. Its modes are not harmonics: over the lowest one, the next ones sit at 1.59, 2.14, 2.30 and 2.65 times its frequency, which is why a drum has no clear pitch. `Snare` gives the head its three lowest modes with chapter 7's `Modal`, and the wires a burst of white noise through a band-pass at 5 kHz with its own decay, at level `snappy`. Its `wires` argument is the wires' time to fall 60 dB, in seconds, and `snappy` their level. Two snares play the same bar below, one tight and bright (tuned high, wires loud and short), one loose and dark (tuned low, the wires soft and longer, the head ringing longer):

```python {run}
from euterpe.instruments import Kit, Snare

tight = Kit(snare=Snare(tune=240.0, snappy=1.0, wires=0.15, decay=0.12))
loose = Kit(snare=Snare(tune=150.0, snappy=0.3, wires=0.3, decay=0.35))
for kit, name in ((tight, "a tight snare"), (loose, "a loose snare")):
    grid = {kit.kick: "x.......x.x.....", kit.snare: "....x.......x..g", kit.hihat: "x.x.x.x.x.x.x.x."}
    display(kit.play(kit.pattern(grid, step=60 / 100 / 4, repeat=2)).take(5.0, f"A rock bar with {name}"))
```

The bar is written as a grid, one character per sixteenth of a bar; the section on the kit explains it. Every instrument here is changed the same way, by the arguments of its class.

## Toms

A *tom* is the same membrane without wires; a kit has several, from high to low, and the lowest stands on the floor. `Tom` gives it five modes and lets the fundamental drop a little in the first moments, as the kick's does, by less. Tuned to a pitch, it sounds near that pitch, but the inharmonic modes keep it vague, so three toms 5 and then 7 semitones apart (196, 147 and 98 Hz in the kit) are heard as high, middle and low rather than as notes. The kit's lowest tom, the floor tom, plays the tom pattern of a 1930s swing standard, with a *fill*, a short break from the pattern, on the high tom every fourth bar. *Swing* splits each beat in three, a *triplet*, and plays a pair of notes as its first and third parts, long-short. Tempo is counted in beats per minute (bpm):

```python {run}
from euterpe.instruments import Kit

kit = Kit()
step = 60 / 200 / 3  # 200 bpm, three steps a beat: swing
bar = {kit.toms[2]: "X.xX.xX.xX.x", kit.kick: "x..x..x..x.."}
fill = {kit.toms[2]: "X.xX.x......", kit.toms[0]: "......xxxxxx", kit.kick: "x..x..x..x.."}
notes = []
for i, grid in enumerate([bar, bar, bar, fill] * 3):
    notes += kit.pattern(grid, step=step, at=i * 12 * step)
display(kit.play(notes).take(15.5, "Toms: a swing standard's floor-tom beat"))
```

## Hands and feet

A hand clap is a burst of noise that the hollow of the hands colours, around 1.2 kHz. One clap of several people is not one burst but several, a few milliseconds apart, since no two people clap at the same instant. `Clap(hands, spread)` makes that: `hands` bursts spread over `spread` seconds, through a band-pass. `Stomp` does the same for feet on wooden boards: several kicks with a short sweep, whose beater click is a knock of wood, 12 ms of noise band-passed around 900 Hz, in a hall with a smooth tail (chapter 8's `ConvolutionReverb`). `people` sets how many feet stamp. Together they play the stomp-stomp-clap of a stadium anthem, at 81 bpm, repeated all through the song, an *ostinato*:

```python {run}
from euterpe.instruments import Clap, Kit, Stomp

kit = Kit()
crowd = {Stomp(people=8): "xx..xx..", Clap(hands=12, spread=0.03, decay=0.25): "..x...x."}
display(kit.play(kit.pattern(crowd, step=60 / 81 / 2, repeat=4)).take(13.0, "Stomp, stomp, clap"))
```

Neither the stomp nor the clap is part of the kit, yet the kit plays them: a note sounds on the instrument that made it, whichever kit plays it.

## Metal

The *hi-hat* is a pair of cymbals on a stand, which a pedal closes against each other. Chapter 4 built one from four inharmonic sines and chapter 6 from noise; its two cymbals vibrate in hundreds of modes at no simple ratios. A drum machine of the early 1980s found a cheap stand-in: six square waves at unrelated frequencies, 205, 304, 370, 523, 540 and 800 Hz, high-passed so only their upper harmonics are left, which beat against each other as metal does. `HiHat` uses that cluster, with some noise. Closed, it decays in `closed` seconds, 0.05 by default; with the `Open()` articulation it rings for `open`, 0.45. One pedal holds both cymbals, so the hi-hat is one resource (chapter 9: the part of an instrument that sounds a note, which a new note on it takes over): a closed stroke on a ringing open one stops it, exactly as the foot does.

```python {run}
from euterpe.instruments import HiHat, Open

hat = HiHat()
hat.play(hat.hit(0.0, articulation=Open()) + hat.hit(1.0, articulation=Open()) + hat.hit(1.2)).take(2.0, "Open, then open choked by a closed stroke")
```

The first open stroke rings its 0.45 s; the second is stopped by the closed stroke 0.2 s after it, with chapter 9's 5 ms fade.

A *crash* is a cymbal struck for an accent, and a *ride* one struck in a steady pattern. Unlike the hi-hat, a cymbal struck again keeps ringing under the new stroke, and the wash builds. `Cymbal` builds the metal from three pairs of chapter 6's `FM` at inharmonic ratios, adds high-passed noise for the wash and decays slowly; `Crash` and `Ride` are cymbals with other defaults, the ride with less wash and a bell. Its resource is `None`, so nothing stops it. The ride plays the swing pattern, "ding, ding-a ding", with the hi-hat closed by the foot on beats 2 and 4, and *ghost notes*, very soft strokes, on the kick on beats 1 and 3, which jazz drummers call *feathering*: felt more than heard:

```python {run}
from euterpe.instruments import Kit

kit = Kit()
swing = {kit.ride: "x..x.xx..x.x", kit.hihat: "...x.....x..", kit.kick: "g.....g....."}
display(kit.play(kit.pattern(swing, step=60 / 140 / 3, repeat=6)).take(11.0, "The ride's swing pattern"))
```

## The kit

`Kit()` groups a kick, a snare, a hi-hat, three toms, a crash and a ride, each an instrument of its own: `kit.kick`, `kit.toms[0]`. Its `pattern` method reads a grid, one row of characters per drum and one character per step of `step` seconds:

- `x` a hit at velocity 0.8, `X` an accent at 1.0, `g` a ghost note at 0.3;
- `o` an open stroke, the hi-hat's `Open()`;
- `.` a rest; a space or a `|` groups steps for the eye and takes no step, so `"x... x..."` is `"x...x..."`.

The grid lasts as long as its longest row, and `repeat` plays it that many times. A grid is notation, read like a guitar tab: the drums themselves stay objects. The kit's `level`, 0.35 by default, scales every drum, so that four drums struck at once at full velocity, a drummer's four limbs, stay under full scale.

Four on the floor (chapter 4), the disco beat: the kick on every beat, the snare on beats 2 and 4, the hi-hat opening between the beats, at 120 bpm:

```python {run}
from euterpe.instruments import Kit

kit = Kit()
disco = {kit.kick: "x...x...x...x...", kit.snare: "....x.......x...", kit.hihat: "x.o.x.o.x.o.x.o."}
display(kit.play(kit.pattern(disco, step=60 / 120 / 4, repeat=4)).take(8.5, "Four on the floor"))
```

Ravel's *Boléro* (1928) rests on one snare ostinato of two bars of three beats each, repeated from the first bar to the last while everything grows around it. Six steps a beat, at 72 bpm; the velocities grow over the three repeats:

```python {run}
import numpy as np
from euterpe.instruments import Kit

kit = Kit()
ostinato = "x..xxxx..xxxx..x..x..xxxx..xxxxxxxxx"
notes = kit.pattern({kit.snare: ostinato}, step=60 / 72 / 6, repeat=3)
for note, louder in zip(notes, np.linspace(0.35, 0.8, len(notes))):
    note.velocity *= louder
display(kit.play(notes).take(16.0, "Ravel, Boléro, the snare ostinato"))
```

A rock beat, three bars and a fill (the hi-hat drops out for the toms; a one-step grid is one hit at `at`): the toms in sixteenths, a flam on the floor tom, and a crash with the kick on the next downbeat. The flam is a technique of the drum, so it joins the grid's notes with `+`:

```python {run}
from euterpe.instruments import Kit

kit = Kit()
step = 60 / 110 / 4
beat = {kit.hihat: "x.x.x.x.x.x.x.x.", kit.snare: "....X.......X...", kit.kick: "x.....x.x......."}
fill = {kit.hihat: "x.x.x.x.", kit.snare: "....X...xx......", kit.toms[0]: "..........xx....",
        kit.toms[1]: "............xx..", kit.kick: "x.....x........."}
notes = []
for i, grid in enumerate([beat, beat, beat, fill]):
    notes += kit.pattern(grid, step=step, at=i * 16 * step)
notes += kit.toms[2].flam(3 * 16 * step + 14 * step, velocity=1.0)
notes += kit.pattern({kit.crash: "X", kit.kick: "X"}, step=1.0, at=64 * step)
display(kit.play(notes).take(10.5, "A rock beat, a tom fill ending on a flam, a crash"))
```

As the plucked strings of chapter 10 do, every hit varies: a drum's `variation`, 0.08 by default, moves each stroke's force and brightness by up to 8 % and its tuning by a tenth of that, so the hi-hat's eighths in the beat above are never two copies of one sound.

## Timpani

A timpano is a membrane too, yet it has a clear pitch, which an orchestra tunes to the music. The difference is the copper kettle under the head. The air inside pushes back on the head, and it pulls the modes that move the most air towards ratios near 1, 1.5, 2, 2.5 and 3 over the principal mode (1.50, 1.98, 2.44 and 2.90 in the model). Ratios of 2 : 3 : 4 : 5 : 6 are those of a harmonic series, so the ear groups the modes into one tone instead of a cluster, and hears it at the principal mode: a stroke with `pitch=G2` sounds G2. `Timpani` gives the head those five modes and a short thud below them, and strikes them with a felt `Mallet`, whose contact lasts a few milliseconds. Each pitch goes to its own kettle, four by default, from D2 to C4.

```python {run}
from euterpe.instruments import Timpani
from euterpe.pitch import C3, G2

timpani = Timpani()
strokes = timpani.hit(0.0, pitch=G2) + timpani.hit(1.5, pitch=C3) + timpani.roll(3.0, 3.0, velocity=0.2, end=1.0, pitch=G2)
display(timpani.play(strokes).take(8.0, "Timpani: G2, C3, then a roll on G2 growing"))
```

On the spectrum, the bright lines of each stroke stand at near-harmonic spacing, unlike the snare's. The roll is single strokes, 20 a second, growing from soft to loud: that is how a timpanist sustains a note, since a struck note cannot be held.

## Bars

A bar of wood or metal, free at both ends, vibrates in chapter 3's inharmonic modes, 1, 2.76, 5.40 and 8.93 times the lowest. Instrument makers carve the underside of each bar to move its modes. A marimba bar is carved until its second mode is two octaves above the first, a ratio of 4; a xylophone bar until it is an octave and a fifth above, a ratio of 3. A glockenspiel's steel bars are not carved, so they keep the free bar's ratios, which is why it sounds like a bell. A tube under each bar (makers call it a resonator; it is not chapter 7's filter) makes the fundamental louder and longer.

`Barred` is the family's instrument: a `Bar` (its mode ratios, decays and amplitudes), a `Mallet` and a decay, with a bar per pitch. As each string of chapter 10 has a tolerance, so has each bar: `Bar.tolerance` defaults to `Tolerance(2.0, 0.05, 0.1)`, fixed flaws of that instrument, as in chapter 10. The tuning does not move from stroke to stroke: a bar does not change pitch when struck again. The `Mallet`, a stick with a round head of felt, yarn, rubber or metal, sets the sound's brightness: its contact with the bar is a short pulse, 4 ms at `hardness=0` and 0.3 ms at 1, and a shorter pulse holds higher frequencies. The same marimba phrase with a soft and a hard mallet:

```python {run}
from euterpe.instruments import Mallet, Marimba
from euterpe.pitch import A4, C5, E4, E5, G4

phrase = [E4, G4, A4, C5, E5, C5, A4, G4]
for hardness in (0.1, 0.9):
    marimba = Marimba(mallet=Mallet(hardness))
    notes = [n for i, pitch in enumerate(phrase) for n in marimba.hit(0.25 * i, pitch=pitch)]
    display(marimba.play(notes).take(3.0, f"Marimba, mallet hardness {hardness}"))
```

Four presets come from it: `Marimba` (rosewood, ratio 4, yarn mallets, C2 to C7), `Xylophone` (rosewood, ratio 3, hard mallets, short, F4 to C8 as heard), `Glockenspiel` (steel, a free bar, brass mallets, G5 to C8 as heard) and `Celesta` (steel plates struck by felt hammers from a keyboard, over wooden resonators, C4 to C8 as heard). A marimba player rolls a held note, so in *Greensleeves* (a traditional English tune) the long notes are rolls:

```python {run}
from euterpe.instruments import Marimba
from euterpe.pitch import A4, B4, C5, D5, E4, E5, F5, Fs4, G4, Gs4

marimba, eighth = Marimba(), 60 / 100 / 2
tune = [(A4, 1), (C5, 2), (D5, 1), (E5, 1.5), (F5, 0.5), (E5, 1), (D5, 2), (B4, 1), (G4, 1.5), (A4, 0.5), (B4, 1),
        (C5, 2), (A4, 1), (A4, 1.5), (Gs4, 0.5), (A4, 1), (B4, 2), (Gs4, 1), (E4, 2), (A4, 1),
        (C5, 2), (D5, 1), (E5, 1.5), (F5, 0.5), (E5, 1), (D5, 2), (B4, 1), (G4, 1.5), (A4, 0.5), (B4, 1),
        (C5, 1.5), (B4, 0.5), (A4, 1), (Gs4, 1.5), (Fs4, 0.5), (Gs4, 1), (A4, 3)]
notes, t = [], 0.0
for pitch, eighths in tune:
    if eighths >= 2:
        notes += marimba.roll(t, eighths * eighth * 0.95, velocity=0.45, end=0.55, rate=14.0, pitch=pitch)
    else:
        notes += marimba.hit(t, 0.7, pitch=pitch)
    t += eighths * eighth
display(marimba.play(notes).take(20.0, "Greensleeves on the marimba, the long notes rolled"))
```

The xylophone plays the opening of Mozart's *Rondo alla Turca* (1783), in sixteenths at 116 bpm:

```python {run}
from euterpe.instruments import Xylophone
from euterpe.pitch import A4, A5, B4, B5, C5, C6, D5, Ds5, E5, F5, Gs4, Gs5

xylophone, sixteenth = Xylophone(), 60 / 116 / 4
rondo = [(B4, 1), (A4, 1), (Gs4, 1), (A4, 1), (C5, 2), (None, 2), (D5, 1), (C5, 1), (B4, 1), (C5, 1), (E5, 2), (None, 2),
         (F5, 1), (E5, 1), (Ds5, 1), (E5, 1), (B5, 1), (A5, 1), (Gs5, 1), (A5, 1), (B5, 1), (A5, 1), (Gs5, 1), (A5, 1), (C6, 4)]
notes, t = [], 0.0
for pitch, steps in rondo * 2:
    if pitch is not None:
        notes += xylophone.hit(t, 0.8, pitch=pitch)
    t += steps * sixteenth
notes += xylophone.hit(t, 1.0, pitch=A5) + xylophone.hit(t, 1.0, pitch=A4)
display(xylophone.play(notes).take(9.5, "Mozart, Rondo alla Turca, the opening, on the xylophone"))
```

The glockenspiel plays the four-note ostinato of Leontovych's *Shchedryk* (1916), known in English as the *Carol of the Bells*, then the same figure a third higher:

```python {run}
from euterpe.instruments import Glockenspiel
from euterpe.pitch import A6, As6, C7, D7, G6

glock, beat = Glockenspiel(), 0.5
figure = [(As6, 1), (A6, 0.5), (As6, 0.5), (G6, 1)]
higher = [(D7, 1), (C7, 0.5), (D7, 0.5), (As6, 1)]
notes, t = [], 0.0
for pitch, beats in figure * 4 + higher * 4 + figure * 2:
    notes += glock.hit(t, 0.7, pitch=pitch)
    t += beats * beat
display(glock.play(notes).take(16.5, "Leontovych, Shchedryk, the ostinato, on the glockenspiel"))
```

The glockenspiel's `decay` is 2 s at C4, and shorter up the range: up here a note rings for under a second, still longer than the half-beat between notes, so they overlap. Nothing damps a bar, so a fast passage blurs, as it does on a real one.

## Showcases

The kit plays a *breakbeat*: the pattern of a short drum break from a 1969 soul record, the most sampled drum recording there is, twice, and a crash:

```python {run}
from euterpe.instruments import Kit

kit, s2 = Kit(), 60 / 136 / 4
breakbeat = [
    {kit.ride: "x.x.x.x.x.x.x.x.", kit.snare: "....x..x.x..x..x", kit.kick: "x.x.......xx...."},
    {kit.ride: "x.x.x.x.x.x.x.x.", kit.snare: "....x..x.x..x..x", kit.kick: "x.x.......xx...."},
    {kit.ride: "x.x.x.x.x.x.x.x.", kit.snare: "....x..x.x....x.", kit.kick: "x.x.......x....."},
    {kit.ride: "x.x.x.x.x.x.....", kit.snare: ".x..x..x.x....x.", kit.kick: "..xx......x.....", kit.crash: "..........x....."},
]
notes = []
for i, grid in enumerate(breakbeat * 2):
    notes += kit.pattern(grid, step=s2, at=i * 16 * s2)
notes += kit.pattern({kit.crash: "X", kit.kick: "X"}, step=1.0, at=8 * 16 * s2)
kit.play(notes).take(16.5, "The kit: a breakbeat")
```

The timpani play the answers of Richard Strauss's *Also sprach Zarathustra* (1896): after each rising call of the brass, here left silent, the timpani strike C and G in turn, then a final roll grows on C:

```python {run}
from euterpe.instruments import Timpani
from euterpe.pitch import C3, G2

timpani, beat, notes, at = Timpani(), 1.0, [], 0.0
for answer in range(3):
    at += 3.0  # the brass call
    for i in range(4):
        notes += timpani.hit(at + i * beat / 2, 0.9 if answer < 2 else 1.0, pitch=C3)
        notes += timpani.hit(at + i * beat / 2 + beat / 4, 0.6, pitch=G2)
    notes += timpani.hit(at + 2 * beat, 1.0, pitch=C3)
    at += 2 * beat + 1.5
notes += timpani.roll(at, 4.0, velocity=0.25, end=1.0, rate=18.0, pitch=C3) + timpani.hit(at + 4.0, 1.0, pitch=C3)
display(timpani.play(notes).take(28.0, "R. Strauss, Also sprach Zarathustra, the timpani's answers"))
```

## Putting it all together

The celesta plays the theme of Tchaikovsky's *Dance of the Sugar Plum Fairy* (1892), the piece that made the instrument famous, over a pizzicato bass from chapter 10 alternating E2 and B2, in bars of two beats. Two players are two phrases, and `+` mixes them:

```python {run name=finale}
from euterpe.instruments import Celesta, PizzicatoStrings
from euterpe.pitch import A4, B2, B4, C5, Cs5, D5, Ds5, E2, E5, Fs5, G5, Gs4

celesta, eighth = Celesta(), 60 / 72 / 2
theme = [(G5, 1), (E5, 1), (G5, 1), (Fs5, 1), (Ds5, 1), (E5, 1), (None, 2),
         (D5, 1), (D5, 1), (D5, 1), (Cs5, 1), (C5, 1), (C5, 1), (C5, 1), (B4, 1),
         (E5, 1), (C5, 1), (E5, 1), (B4, 1), (Gs4, 1), (A4, 1), (None, 2)]
notes, t = [], 8 * eighth * 2  # the bass alone first: sixteen eighths, four bars of two beats
for pitch, eighths in theme * 2:
    if pitch is not None:
        notes += celesta.hit(t, 0.7, pitch=pitch)
    t += eighths * eighth
bass = [(i * eighth, E2 if i % 2 == 0 else B2, eighth * 0.8, 0.6) for i in range(int(t / eighth) + 2)]
song = celesta.play(notes) + PizzicatoStrings().play(bass)
song.take(28.5, "Tchaikovsky, Dance of the Sugar Plum Fairy")
```

The kit's drums are noise and sines, and the celesta and the strings are models of real objects. The 1980s had a cheaper way to make all of these sounds, from the few square waves and noise channels of a game console's sound chip: chapter 15. And the timpani, the celesta and the strings belong together in one orchestra, which chapter 16 assembles.

## Summary

- `Struck` is every instrument hit by a stick, a hand or a mallet: it never sustains, a note without a pitch plays at its tuning, and `hit`, `roll` and `flam` make its notes.
- The kit's drums are noise, sines and a few membrane modes. A kick is a sine that falls in pitch; a snare is three membrane modes and band-passed noise for the wires; a tom is five membrane modes; a clap or a stomp is several bursts a few milliseconds apart.
- The hi-hat is six square waves and noise, one resource for its pedal, so a closed stroke chokes an open one; a cymbal is three FM pairs and noise, with no resource, so its hits overlap.
- `Kit` groups the drums and plays grids of `x X g o .`; a note sounds on the drum that made it.
- `Timpani` are pitched because the air in the kettle pulls their modes near harmonic; `Barred` instruments are bars whose modes the maker carves, struck by a `Mallet` whose hardness sets the brightness.

## Exercises

1. In the block of two snares, change the tight snare's `snappy=1.0` to `snappy=0.0`. What is left of it?
2. In the disco block, change the hi-hat row to `"x.x.x.x.x.x.x.x."`. What is lost, and why does the open stroke matter to the beat?
3. A marimba bar is carved so its second mode is at 4 times the first. At C4 (261.6 Hz), where is it? Where would it be on an uncarved bar, with the free bar's ratio?
4. Write a cowbell as a `Struck` subclass: two square waves at 540 and 800 Hz (two of the hi-hat's six) through a band-pass at 2 kHz, under a decay of about 0.3 s. Play it on the beats of the disco grid.

### Answers

1. Only the head's three membrane modes: a short, dull knock with a vague pitch near 240 Hz, closer to a high tom than to a snare. The wires' burst of band-passed noise is what makes a snare a snare.
2. Every hi-hat stroke is now closed and short, so the long "tss" between the beats is gone. The open stroke rings until the next closed one chokes it, which fills the off-beat and gives disco its lift.
3. At 4 × 261.6 = 1046.5 Hz, which is C6, two octaves up, so it reinforces the note. An uncarved bar would put it at 2.76 × 261.6 ≈ 722 Hz, between F5 and F♯5, which clashes with the note and sounds like a bell.
4. One way, with the units of Part I; its `voice` is a few lines, the rest is the kit as before:

```python {run}
from euterpe.instruments import Kit, Struck
from euterpe.sound import ADSR, BandPass, Square


class Cowbell(Struck):
    tune = 540.0

    def voice(self, note):
        metal = Square(note.freq) + Square(note.freq * 800 / 540)
        decay = ADSR(attack=0.0, decay=0.3, sustain=0.0, release=0.0, gate=0.3, curve=4.0)
        return BandPass(metal, 2000.0, 1.0) * decay * (note.velocity * 0.4)


kit = Kit()
grid = {kit.kick: "x...x...x...x...", kit.snare: "....x.......x...", Cowbell(): "x...x...x...x..."}
display(kit.play(kit.pattern(grid, step=60 / 120 / 4, repeat=2)).take(4.5, "The disco beat with a cowbell"))
```

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
