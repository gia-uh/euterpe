# Drums and percussion

A string or a column of air has harmonics in neat ratios, so it has a clear pitch. A drum head, a cymbal or a metal bar vibrates in modes at ratios no one chose, and most of the sound is in the first fraction of a second. That makes percussion the easiest family to synthesize with the units of Part I: a sine whose pitch falls, a burst of filtered noise, a few decaying modes. This chapter builds a drum kit from those, then timpani, then four instruments of tuned bars, and plays something known on each one.

## Words for drums and rhythm

A *drum kit* is the set of drums one drummer plays sitting down. The *kick*, or bass drum, is the large drum on the floor, struck by a beater on a pedal. The *snare* drum has *wires* (the snares) stretched under its lower head, which buzz against it. The *toms* are drums without wires, from high to low; the lowest stands on the floor. The *hi-hat* is a pair of cymbals on a stand, which a pedal closes against each other. A *crash* is a cymbal struck for an accent, and a *ride* is one struck in a steady pattern. A *mallet* is a stick with a round head, of felt, yarn, rubber or metal.

Music is counted in *beats*, and a *bar* groups a fixed number of them, four unless a piece says otherwise (chapter 9); the beats of a bar are numbered from 1, and beat 1 is the *downbeat*. An *eighth* lasts half a beat and a *sixteenth* a quarter of one; a *triplet* splits a beat in three. A *fill* is a short break from the pattern, often on the toms, that leads into the next section. Between two notes, a *third* is 3 or 4 semitones, a *fourth* 5, and a *fifth* 7 (chapter 2).

A *roll* is a stream of strokes so fast they blur into a sustained sound. A *flam* is a stroke with a soft *grace* stroke just before it, which makes it sound thicker. A *ghost note* is a very soft stroke between the loud ones. Tempo is counted in beats per minute (bpm): at 120 bpm a beat lasts 0.5 s. *Swing* plays pairs of eighths long-short, as the first and third notes of a triplet. An *ostinato* is a short pattern repeated all through a piece.

## Struck

Every instrument of this chapter is a `Struck`, a subclass of the `Instrument` of chapter 9. A struck instrument never sustains: each hit dies on its own and rings past its written duration, unless a new hit on the same drum stops it, as a stick does to a drum head still moving. A drum's tuning is `tune`, in Hz: a note made without a pitch plays at that tuning, and a pitch given to one hit retunes that hit alone. Three techniques make notes:

- `hit(at, velocity)`: one stroke at time `at`;
- `roll(at, length, velocity, end, rate)`: strokes `rate` times a second for `length` seconds, the velocity moving in a straight line from `velocity` to `end`;
- `flam(at, velocity, grace)`: a stroke at half the velocity `grace` seconds early (0.025 s by default), then the stroke.

```python {run output=code}
from euterpe.instruments import Snare

snare = Snare()
for note in snare.roll(0.0, 0.5, velocity=0.2, end=0.8, rate=10.0) + snare.flam(1.0):
    print(f"{note.time:.3f} s  velocity {note.velocity:.2f}")
```

The roll's five strokes are 0.1 s apart and grow from 0.2 to 0.8; the flam is a grace stroke at 0.975 s and the stroke at 1 s.

## The kick

When the beater hits the kick's head, it pushes the head in and stretches it, and a stretched membrane vibrates faster. As the head settles, its pitch falls to its resting tuning. `Kick` models exactly that: a sine whose frequency starts at `tune * sweep` and falls to `tune`, with time constant `drop`, under a decay, plus 4 ms of high-passed noise for the beater's click (chapter 5's `HighPass` on chapter 6's `WhiteNoise`).

```python {run}
from euterpe.instruments import Kick

kick = Kick(tune=50.0, sweep=3.0, drop=0.04)
display(kick.play(kick.hit(0.0, velocity=1.0)).take(0.6, "One kick, falling from 150 Hz to 50 Hz"))
```

The spectrum's brightest line starts high and bends down to 50 Hz in the first tenth of a second. The ear does not hear the fall as a glide: it is too fast, and it hears a punch instead. Measured, the strongest frequency in the first 20 ms and between 0.1 and 0.3 s:

```python {run output=code}
import numpy as np
from euterpe.instruments import Kick
from euterpe.sound.core import RATE, render

def strongest(x):
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return np.fft.rfftfreq(len(x), 1 / RATE)[np.argmax(spectrum)]

kick = Kick(tune=50.0, variation=0.0)
x = render(kick.play(kick.hit(0.0, velocity=1.0)), 0.4)
print(f"first 20 ms: {strongest(x[: RATE // 50]):.0f} Hz")
print(f"0.1 to 0.3 s: {strongest(x[RATE // 10 : 3 * RATE // 10]):.0f} Hz")
```

The first window is only 20 ms long. A window of T seconds holds whole cycles only of multiples of 1 / T Hz, so this one tells frequencies apart only every 1 / 0.02 = 50 Hz: 150 Hz is a rough reading, but it is far above the resting 50 Hz.

## The snare

The snare's head is a circular membrane. Its modes are not harmonics: over the lowest one, the next ones sit at 1.59, 2.14, 2.30 and 2.65 times its frequency, which is why a drum has no clear pitch. `Snare` gives the head its three lowest modes with chapter 7's `Modal`, and the wires a burst of white noise through a band-pass at 5 kHz with its own decay, at level `snappy`. Its `wires` argument is the wires' time to fall 60 dB, in seconds, and `snappy` their level. Two snares play the same bar below, one tight and bright (tuned high, wires loud and short), one loose and dark (tuned low, the wires soft and longer, the head ringing longer):

```python {run}
from euterpe.instruments import Kit, Snare

tight = Kit(snare=Snare(tune=240.0, snappy=1.0, wires=0.15, decay=0.12))
loose = Kit(snare=Snare(tune=150.0, snappy=0.3, wires=0.3, decay=0.35))
for kit, name in ((tight, "a tight snare"), (loose, "a loose snare")):
    grid = {kit.kick: "x.......x.x.....", kit.snare: "....x.......x..g", kit.hihat: "x.x.x.x.x.x.x.x."}
    display(kit.play(kit.pattern(grid, step=60 / 100 / 4, repeat=2)).take(5.0, f"A rock bar with {name}"))
```

The bar is written as a grid; the next sections explain it. Every instrument here is changed the same way, by the arguments of its class.

## Toms

A tom is the same membrane without wires. `Tom` gives it five modes and lets the fundamental drop a little in the first moments, as the kick's does, by less. Tuned to a pitch, it sounds near that pitch, but the inharmonic modes keep it vague, so three toms a fourth and then a fifth apart (196, 147 and 98 Hz in the kit) are heard as high, middle and low rather than as notes. The kit's lowest tom, the floor tom, plays the tom pattern of a 1930s swing standard, with a fill on the high tom every fourth bar:

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

A hand clap is a burst of noise that the hollow of the hands colours, around 1.2 kHz. One clap of several people is not one burst but several, a few milliseconds apart, since no two people clap at the same instant. `Clap(hands, spread)` makes that: `hands` bursts spread over `spread` seconds, through a band-pass. `Stomp` does the same for feet on wooden boards: several kicks with a short sweep, whose beater click is a knock of wood, 12 ms of noise band-passed around 900 Hz, in a hall with a smooth tail (chapter 8's `ConvolutionReverb`). A first version used the kick's own click, noise high-passed above 1.5 kHz, and a feedback-delay hall: it sounded metallic, a third of its spectrum above 2 kHz, and listeners did not hear feet. Together they play the stomp-stomp-clap of a stadium anthem, at 81 bpm:

```python {run}
from euterpe.instruments import Clap, Kit, Stomp

kit = Kit()
crowd = {Stomp(people=8): "xx..xx..", Clap(hands=12, spread=0.03, decay=0.25): "..x...x."}
display(kit.play(kit.pattern(crowd, step=60 / 81 / 2, repeat=4)).take(13.0, "Stomp, stomp, clap"))
```

Neither the stomp nor the clap is part of the kit, yet the kit plays them: a note sounds on the instrument that made it, whichever kit plays it.

## Metal

The hi-hat's two cymbals vibrate in hundreds of modes at no simple ratios. A drum machine of the early 1980s found a cheap stand-in: six square waves at unrelated frequencies, 205, 304, 370, 523, 540 and 800 Hz, high-passed so only their upper harmonics are left, which beat against each other as metal does. `HiHat` uses that cluster, with some noise. Closed, it decays in `closed` seconds, 0.05 by default; with the `Open()` articulation it rings for `open`, 0.45. One pedal holds both cymbals, so the hi-hat is one resource (chapter 9: the part of an instrument that sounds a note, which a new note on it takes over): a closed stroke on a ringing open one stops it, exactly as the foot does.

```python {run output=code}
from euterpe.instruments import HiHat, Open
from euterpe.sound.core import RATE

hat = HiHat()
phrase = hat.play(hat.hit(0.0, articulation=Open()) + hat.hit(0.2))
print(f"the open stroke would ring until {phrase.ends[0] / RATE:.2f} s; it stops at {phrase.stops[0] / RATE:.3f} s")
```

The open stroke stops 5 ms after the closed one starts, not at once: a voice that is stopped early fades out over 5 ms, as chapter 9's stolen voices do, so that it does not click.

A crash or a ride is the opposite: struck again, it keeps ringing under the new stroke, and the wash builds. `Cymbal` builds the metal from three pairs of chapter 6's `FM` at inharmonic ratios, adds high-passed noise for the wash and decays slowly; `Crash` and `Ride` are cymbals with other defaults, the ride with less wash and a bell. Its resource is `None`, so nothing stops it. The ride plays the swing pattern, "ding, ding-a ding", with the hi-hat closed by the foot on beats 2 and 4, and ghost notes on the kick on beats 1 and 3, which jazz drummers call *feathering*: felt more than heard:

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
- `.` or a space, a rest. A space takes a whole step, like a dot.

The grid lasts as long as its longest row, and `repeat` plays it that many times. A grid is notation, read like a guitar tab: the drums themselves stay objects. The kit's `level`, 0.35 by default, scales every drum, so that four drums struck at once at full velocity, a drummer's four limbs, stay under full scale.

Four on the floor, the disco beat: the kick on every beat, the snare on beats 2 and 4, the hi-hat opening between the beats, at 120 bpm:

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

A rock beat, three bars and a fill: the toms in sixteenths, a flam on the floor tom, and a crash with the kick on the next downbeat. The flam is a technique of the drum, so it joins the grid's notes with `+`:

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

A bar of wood or metal, free at both ends, vibrates in modes at 1, 2.76, 5.40 and 8.93 times the lowest: inharmonic again. Instrument makers carve the underside of each bar to move its modes. A marimba bar is carved until its second mode is two octaves above the first, a ratio of 4; a xylophone bar until it is an octave and a fifth above, a ratio of 3. A glockenspiel's steel bars are not carved, so they keep the free bar's ratios, which is why it sounds like a bell. A tube under each bar, the *resonator*, makes the fundamental louder and longer.

`Barred` is the family's instrument: a `Bar` (its mode ratios, decays and amplitudes), a `Mallet` and a decay, with a bar per pitch. As each string of chapter 10 has a tolerance, so has each bar: `Bar.tolerance` defaults to `Tolerance(2.0, 0.05, 0.1)`, so each bar is up to 2 cents out of tune, up to 5 % louder or softer and up to 10 % shorter or longer, fixed flaws of that instrument, as in chapter 10. The tuning does not move from stroke to stroke: a bar does not change pitch when struck again. The `Mallet` sets the sound's brightness: its contact with the bar is a short pulse, 4 ms at `hardness=0` and 0.3 ms at 1, and a shorter pulse holds higher frequencies. The same marimba phrase with a soft and a hard mallet:

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

The kit plays the stadium stomp, then four on the floor, then a breakbeat: the pattern of a short drum break from a 1969 soul record, the most sampled drum recording there is. Each section starts where the one before ends:

```python {run}
from euterpe.instruments import Clap, Kit, Stomp

kit = Kit()
e, s1, s2 = 60 / 81 / 2, 60 / 120 / 4, 60 / 136 / 4
notes = kit.pattern({Stomp(): "xx..xx..", Clap(hands=12, spread=0.03, decay=0.25): "..x...x."}, step=e, repeat=4)
t = 32 * e
notes += kit.pattern({kit.kick: "x...x...x...x...", kit.snare: "....x.......x...", kit.hihat: "x.o.x.o.x.o.x.o."},
                     step=s1, at=t, repeat=4)
t += 4 * 16 * s1
breakbeat = [
    {kit.ride: "x.x.x.x.x.x.x.x.", kit.snare: "....x..x.x..x..x", kit.kick: "x.x.......xx...."},
    {kit.ride: "x.x.x.x.x.x.x.x.", kit.snare: "....x..x.x..x..x", kit.kick: "x.x.......xx...."},
    {kit.ride: "x.x.x.x.x.x.x.x.", kit.snare: "....x..x.x....x.", kit.kick: "x.x.......x....."},
    {kit.ride: "x.x.x.x.x.x.....", kit.snare: ".x..x..x.x....x.", kit.kick: "..xx......x.....", kit.crash: "..........x....."},
]
for i, grid in enumerate(breakbeat * 2):
    notes += kit.pattern(grid, step=s2, at=t + i * 16 * s2)
notes += kit.pattern({kit.crash: "X", kit.kick: "X"}, step=1.0, at=t + 8 * 16 * s2)
display(kit.play(notes).take(36.5, "The kit: stadium, disco, breakbeat"))
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

The celesta plays the theme of Tchaikovsky's *Dance of the Sugar Plum Fairy* (1892), the piece that made the instrument famous, over a pizzicato bass from chapter 10 alternating E2 and B2, in bars of two beats. Two players are two phrases, and `+` mixes them:

```python {run}
from euterpe.instruments import Celesta, PizzicatoStrings
from euterpe.pitch import A4, B2, B4, C5, Cs5, D5, Ds5, E2, E5, Fs5, G5, Gs4

celesta, eighth = Celesta(), 60 / 72 / 2
theme = [(G5, 1), (E5, 1), (G5, 1), (Fs5, 1), (Ds5, 1), (E5, 1), (None, 2),
         (D5, 1), (D5, 1), (D5, 1), (Cs5, 1), (C5, 1), (C5, 1), (C5, 1), (B4, 1),
         (E5, 1), (C5, 1), (E5, 1), (B4, 1), (Gs4, 1), (A4, 1), (None, 2)]
notes, t = [], 8 * eighth * 2  # the bass alone first: eight eighths, four bars of two beats
for pitch, eighths in theme * 2:
    if pitch is not None:
        notes += celesta.hit(t, 0.7, pitch=pitch)
    t += eighths * eighth
bass = [(i * eighth, E2 if i % 2 == 0 else B2, eighth * 0.8, 0.6) for i in range(int(t / eighth) + 2)]
display((celesta.play(notes) + PizzicatoStrings().play(bass)).take(28.5, "Tchaikovsky, Dance of the Sugar Plum Fairy"))
```

## Summary

- `Struck` is every instrument hit by a stick, a hand or a mallet: it never sustains, its note's pitch is its tuning, and `hit`, `roll` and `flam` make its notes.
- A kick is a sine that falls in pitch; a snare is three membrane modes and band-passed noise for the wires; a tom is five membrane modes; a clap or a stomp is several bursts a few milliseconds apart.
- The hi-hat is six square waves and noise, one resource for its pedal, so a closed stroke chokes an open one; a cymbal is three FM pairs and noise, with no resource, so its hits overlap.
- `Kit` groups the drums and plays grids of `x X g o .`; a note sounds on the drum that made it.
- `Timpani` are pitched because the air in the kettle pulls their modes near harmonic; `Barred` instruments are bars whose modes the maker carves, struck by a `Mallet` whose hardness sets the brightness.

## Exercises

1. In the kick's measuring block, change `sweep` (pass `sweep=1.0` to `Kick`). What does the first window now measure, and how does the kick sound different?
2. In the disco block, change the hi-hat row to `"x.x.x.x.x.x.x.x."`. What is lost, and why does the open stroke matter to the beat?
3. A marimba bar is carved so its second mode is at 4 times the first. At C4 (261.6 Hz), where is it? Where would it be on an uncarved bar, with the free bar's ratio?
4. Write a cowbell as a `Struck` subclass: two square waves at 540 and 800 Hz (two of the hi-hat's six) through a band-pass at 2 kHz, under a decay of about 0.3 s. Play it on the beats of the disco grid.

### Answers

1. With `sweep=1.0` the pitch starts at the resting tune, so the first window measures about 50 Hz too, within its 50 Hz resolution. The kick loses its punch and sounds like a low sine bump: the fall in pitch is what makes the attack.
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
