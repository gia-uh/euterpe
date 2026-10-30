# Bowed strings, winds and brass

This is where the chapter ends up:

```python {run echo=false}
# The teaser: the last bar of the finale's last pass and its ending, built by the code of this
# chapter's last section, which it reads from this file so the two never differ. Its notes from
# the last bar on are moved to time 0 and mixed alone, so the rest of the piece is not rendered.
import re
from dataclasses import replace
from pathlib import Path

from euterpe.view import listen

text = Path("chapters/13-bowed-strings-winds-and-brass.md").read_text()
scope = {}
code = re.search(r"```python \{[^}\n]*name=finale\b[^}\n]*\}\n(.*?)\n```", text, re.S).group(1)
exec(code, scope)
t0 = scope["starts"][4] + 3 * scope["BAR"]
later = {inst: [replace(n, time=n.time - t0) for n in notes if n.time >= t0] for inst, notes in scope["score"].items()}
display(listen(scope["mix"](later), scope["length"] - t0, "Ravel, Boléro, the last bar and the ending"))
```

Ravel's *Boléro* (1928): one melody handed from a flute to a clarinet, to the violins and to the brass, over a snare drum that never stops. Chapter 12 ended on a pad, three saws that hold a chord because a key is down. Nothing plays them. A violinist pushes a bow across a string for as long as the note lasts, and a flautist blows for as long as the note lasts: the force never stops, and the note changes with it. This chapter builds those instruments, the strings, the winds and the brass, and each one plays a piece written for it before they all play the *Boléro*.

The pieces in this chapter are transcribed from their public-domain scores into `book/tunes.py`, next to the chapters. `notes("air", at, beat)` returns one of them as a list of `Note`s from time `at`, `beat` seconds a beat, so a tempo is one number.

## A force that does not stop

Chapter 7 plucked a string once and let it ring: `Pluck` puts a burst into a delay line and the note only dies after that. A bow is different. Its hair is coated with rosin, which grips. While the string moves with the bow, it *sticks* to the hair and is dragged along. When the string's own pull back grows stronger than the grip, it *slips* and snaps back, until the hair catches it again. Stick, slip, stick, slip, once per period, for as long as the bow moves. `Bow(freq, force, speed)` is a string in a delay line, as in `Pluck`, with that friction acting at the bow on every sample. The same G3, plucked and bowed:

```python {run}
from euterpe.pitch import G3
from euterpe.sound import Bow, Pluck
from euterpe.view import listen

display(listen(Pluck(G3.freq) * 0.5, 2.5, "G3, plucked"))
display(listen(Bow(G3.freq, force=0.5, speed=0.5) * 0.5, 2.5, "G3, bowed"))
```

The plucked note starts bright and fades. The bowed one holds its level and its tone, and would hold them forever. Its shape, seen at the bridge, is close to a sawtooth: a slow climb while the string sticks to the bow, and a fast fall when it slips.

```python {run}
from euterpe.pitch import G3
from euterpe.sound import Bow

Bow(G3.freq).take(1.0).waveform(span=(0.5, 0.52), caption="Bow(G3) at the bridge: stick (slow climb), slip (fast fall)")
```

A sawtooth has every harmonic, falling as 1/k (chapter 3), so a bowed string is rich and buzzing before any body colours it.

## Force and speed

How hard the bow presses is its `force`; how fast it moves is `speed`, both from 0 to 1. Only a window of forces gives a clean note for a given speed. Too little, and the hair cannot hold the string for a whole period: it slips several times a cycle, the fundamental fails, and a thin whistle of upper harmonics is left, the *surface sound* of a beginner. Too much, and the string sticks too long and tears free at random: a scratch. Here the middle value is the lesson, so the block plays three:

```python {run}
from euterpe.pitch import G3
from euterpe.sound import Bow
from euterpe.view import listen

for force, name in ((0.02, "too light"), (0.5, "right"), (1.0, "too heavy")):
    display(listen(Bow(G3.freq, force=force, speed=0.8, position=0.2) * 0.5, 2.0, f"Bow force {force}, {name}"))
```

`position` is where the bow crosses the string, as a fraction of its length from the bridge: 0.2 here, 0.12 by default. The harmonics whose node sits under the bow cannot be driven, so at 0.12 every eighth harmonic is missing, and nearer the bridge the note is brighter and the window of good forces narrower.

## The violin

`Violin` is chapter 9's anatomy of an instrument with a bow inside: each note is one `Bow`, drawn by a `Bowing` part, through a bridge resonance near 2.5 kHz and chapter 10's `ViolinBody`. Velocity is not a gain here. It sets the bow's force and speed together, so a harder note is louder and brighter at once, as on the real instrument. The attack ramps the force up in 0.08 s with a short bump, the hair catching the string.

A violinist also rocks the finger on the string, a few times a second: *vibrato*. The string's length swings, so the pitch swings by a few cents either side. `Vibrato(rate, cents, delay, rise)` is a part of the instrument: 5.5 Hz and 18 cents on the violin, held back for a quarter second and growing in over 0.3 s, as players start a note straight and let it sing. One long A4, without and with:

```python {run}
from euterpe.instruments import Note, Vibrato, Violin
from euterpe.pitch import A4
from euterpe.view import listen

display(listen(Violin(vibrato=Vibrato(cents=0)).play([Note(0.0, A4, 3.0)]), 3.5, "A4, no vibrato"))
display(listen(Violin().play([Note(0.0, A4, 3.0)]), 3.5, "A4, with vibrato"))
```

Without vibrato the note is a steady buzz. With it, the note sounds alive after a moment, because each harmonic k swings by k times the fundamental's swing and moves across the body's resonances.

Bach's *Air* from the Orchestral Suite No. 3 in D (BWV 1068, about 1730) opens on a single F♯ held for more than a bar, then turns down in a fast run. Only a driven string can play it: a plucked F♯ would be gone before the bar ends, and a bowed one grows. On the solo violin, at 50 beats a minute:

```python {run}
from euterpe.instruments import Violin
from euterpe.view import listen
from tunes import notes

AIR = 60 / 50
violin = Violin()
display(listen(violin.play(notes("air", 0.0, AIR)), 20.0, "Bach, Air (BWV 1068), the melody on Violin"))
```

## A section

An orchestra has no single violin: it has a dozen, playing the same line. No two are exactly in tune, no two start at the same instant, and each vibrato has its own rate. Their sum beats and shimmers, as chapter 12's supersaw did, but from players who differ by accident instead of by a fixed spread. `StringSection(players=4)` is that: one `Bow` per player, each detuned by up to 8 cents, starting up to 30 ms late, with its own vibrato rate and phase, and summed. One player against four, on the same note:

```python {run}
from euterpe.instruments import Note, StringSection, Violin
from euterpe.pitch import A4
from euterpe.view import listen, spectrogram

one, four = Violin().play([Note(0.0, A4, 3.0)]).take(3.5), StringSection().play([Note(0.0, A4, 3.0)]).take(3.5)
display(listen(one, caption="A4, one violin"), listen(four, caption="A4, a section of four"))
spectrogram(one, four, labels=["one player", "four players"], lo=400, hi=4000,
            caption="The upper harmonics: one line each for one player, a band of beating lines for four")
```

The single violin's harmonics are clean lines that wave together. The section's are blurred bands: four strings a few cents apart beat at a different rate in every harmonic. Below C3 the section sounds through a cello's body (`CelloBody`, an air mode near 100 Hz), so its lowest players can take a bass line.

The *Air* is written for strings in four parts: the melody, two inner voices that hold the harmony, and a bass that walks in octaves under it, one leap every eighth note. Each layer added to the solo violin: the section on the inner voices, then the section's low players on the bass:

```python {run}
from euterpe.instruments import StringSection, Violin
from euterpe.view import listen
from tunes import notes

AIR = 60 / 50
violin, section = Violin(), StringSection(players=3)
inner = section.play(notes("air inner", 0.0, AIR, velocity=0.4))
bass = section.play(notes("air bass", 0.0, AIR, velocity=0.5))
display(listen(violin.play(notes("air", 0.0, AIR)) + inner * 0.8 + bass * 0.9, 20.5, "Bach, Air, in four parts"))
```

Listen for the held F♯ swelling over the walking bass, and the inner voices changing chord under it every two beats.

## An air column

A clarinet is a tube with a reed at one end. Blown air pushes the reed against the mouthpiece and closes it; the pressure wave runs down the tube, reflects at the bell and comes back to open it again. The reed is a valve that the tube itself opens and closes, once per period. Chapter 7's bar rang once when struck; here the player's breath keeps the tube going, and the reed does for it what the bow does for a string.

`Bore(freq, pressure, mouth)` is a tube in a delay line, with a mouthpiece at one end and a bell at the other. The mouthpiece is a model of its own: `Reed()` for a clarinet, `Jet()` for a flute, `Lips()` for brass. A reed closes its end of the tube, a flute is open at both ends, and that one difference decides the harmonics. A tube closed at one end must have still air at the closed end and moving air at the open one, which only odd multiples of a quarter wavelength allow. So a clarinet sounds the odd harmonics, 1, 3, 5, and almost none of the even ones. A tube open at both ends allows every harmonic:

```python {run}
from euterpe.pitch import G3
from euterpe.sound import Bore, Jet, Reed
from euterpe.view import spectrum

spectrum(Bore(G3.freq, pressure=0.6, mouth=Reed()).take(1.5), Bore(G3.freq, pressure=0.6, mouth=Jet()).take(1.5),
         labels=["Reed: closed at one end", "Jet: open at both"], f0=G3.freq, harmonics=10,
         caption="The same G3 from a closed and an open tube")
```

The reed's second and fourth harmonics sit far below its first and third: that hollow, woody sound is the clarinet's low register. A driven tube also needs enough pressure to start at all. Below about 0.3 the reed does not move far enough to feed the tube, and only the breath is heard; above it, the note *speaks*, suddenly. Chapter 4's `Segments` raises the pressure from 0 to 0.7 over three seconds, one take across the threshold:

```python {run}
from euterpe.pitch import G3
from euterpe.sound import Bore, Reed, Segments
from euterpe.view import listen

breath = Segments([(0.0, 0.0), (3.0, 0.7)])
display(listen(Bore(G3.freq, pressure=breath, mouth=Reed(), noise=0.05) * 0.5, 4.0, "A reed, the pressure rising past the threshold"))
```

`Clarinet` is `Bore` with a `Reed` inside an instrument, its velocity setting the pressure through a `Breath` part, with no vibrato: classical clarinettists play without it. Mozart wrote his Clarinet Concerto (K. 622) in 1791, the year he died; its Adagio opens on a slow, singing line in the instrument's middle register. Over soft chords from the section:

```python {run}
from euterpe.instruments import Clarinet, StringSection
from euterpe.view import listen
from tunes import notes

ADAGIO = 60 / 50
theme = Clarinet().play(notes("adagio", 0.0, ADAGIO, velocity=0.6))
chords = StringSection(players=3).play(notes("adagio chords", 0.0, ADAGIO, velocity=0.3))
display(listen(theme + chords * 0.6, 19.5, "Mozart, Clarinet Concerto (K. 622), Adagio, the opening"))
```

## The flute's jet

A flute has no reed. The player blows a thin jet of air across the edge of a hole; the jet flips to one side of the edge or the other, and the tube's air, swinging back and forth, decides which. `Jet()` models it with a second delay, the time the jet takes to cross to the edge, and a soft curve that splits it there. The tone is close to a sine, and the breath noise around it is part of the sound, louder than on any other instrument (`Flute` sets the breath's noise to 0.06, three times the clarinet's). Blow too hard and the jet arrives too early for the fundamental: the note jumps to its octave. That is *overblowing*, and a flautist uses it on purpose to reach the second register.

Grieg's *Morning Mood* (from *Peer Gynt*, published in 1888) is a sunrise: the flute plays a phrase that rocks around a chord of E major, and it is answered an octave lower. The second time down here is the same flute, over a held chord from the section:

```python {run}
from euterpe.instruments import Flute, Note, StringSection
from euterpe.pitch import B3, E3
from euterpe.view import listen
from tunes import notes

MORNING = 60 / 200  # an eighth note
flute = Flute().play(notes("morning", 0.0, MORNING) + notes("morning", 36 * MORNING, MORNING, up=-12))
chord = StringSection(players=2).play([Note(0.0, p, 72 * MORNING, 0.3) for p in (E3, B3)])
display(listen(flute + chord * 0.5, 23.0, "Grieg, Morning Mood, the flute and its reply"))
```

Listen for the breath at the start of each note and the almost bare tone in between, rounder and darker in the low reply.

## Lips and a bell

A brass player's lips are the reed: they buzz in the cup of the mouthpiece, opening and closing once per period. Unlike a cane reed, lips are a mass on a spring with a pitch of their own, and the player tunes it to the note. `Lips()` is that resonator, and the tube under it, like the flute's, has every harmonic. What sets brass apart is how it grows. Played softly, the lips barely open and the sound is round; played hard, they slam shut on every cycle, and the sharp edges add high harmonics fast. A trumpet getting louder gets *brassy*. `BrassSection(players=3)` blows each note on three `Bore`s with `Lips`, a few cents apart. The same C major chord, four times, each harder than the last:

```python {run}
from euterpe.instruments import BrassSection, Note
from euterpe.pitch import C3, C4, E3, G3
from euterpe.view import listen

brass = BrassSection()
swell = [Note(1.5 * k, p, 1.3, v) for k, v in enumerate((0.1, 0.4, 0.7, 1.0)) for p in (C3, E3, G3, C4)]
display(listen(brass.play(swell), 6.5, "A C major chord on BrassSection, velocity 0.1 to 1.0"))
```

The first chord is soft and dark, almost a horn. By the last the same notes rasp. On a driven instrument, loudness and tone come from the same force, and no gain can fake it.

Rossini's *William Tell* Overture (1829) ends on a gallop, a trumpet call of repeated notes, three to a beat, the most famous fanfare ever written for brass:

```python {run}
from euterpe.instruments import BrassSection, Note
from euterpe.pitch import B2, E2
from euterpe.view import listen
from tunes import notes

brass = BrassSection()

GALLOP = 60 / 152
call = notes("tell", 0.0, GALLOP, velocity=0.8) + notes("tell", 8 * GALLOP, GALLOP, velocity=0.8)
call += notes("tell end", 16 * GALLOP, GALLOP, velocity=1.0)
low = [Note(b * GALLOP, (E2, B2)[b % 2], GALLOP * 0.6, 0.6) for b in range(22)]  # the low players on E and B
display(listen(brass.play(call + low) * 0.7, 10.0, "Rossini, William Tell Overture, the gallop on BrassSection"))
```

## Where synthesis stops

These instruments are recognisable and they respond to how they are played. They are also not yet real, and the ear knows why:

- A violin's body has hundreds of resonances and radiates differently in every direction; here it has three modes.
- A long note on a real violin changes bow direction, with a small break the ear expects. There is no bow change here, and no spiccato, col legno or double stops.
- A real player moves the bow's pressure, speed and position all through a note, by judgement. Here they follow an envelope.
- The tubes are cylinders whose length changes as a whole: no tone holes, no key noise, no break between the clarinet's low and high registers, and no cone, so no oboe, saxophone or bassoon. In the finale the clarinet an octave down stands in for the bassoon, which Ravel wrote there.
- A section's players start apart and drift in tune, but they do not listen to each other.
- Every instrument here is dry until an effect adds a room.

## Putting it all together

The *Boléro* is marked *Tempo di Bolero, moderato assai*: 72 beats a minute in 3/4, so a bar is 2.5 s. The snare drum plays the same two-bar figure from the first bar to the last, the ostinato of chapter 14's `Kit`, where the drum is built. A pizzicato bass (chapter 10) plucks C and G under it. The melody passes from instrument to instrument, four bars each, and every pass is louder: the velocity rises from 0.35 to 0.95 over the piece, which on these instruments raises the bow's force and the breath, so the swell brightens as it grows.

- **Pass 0**: one bar of the snare and the bass alone, very soft.
- **Pass 1**: the flute on the melody.
- **Pass 2**: the clarinet.
- **Pass 3**: the clarinet an octave down, in its dark low register.
- **Pass 4**: the string section in two octaves, with vibrato.
- **Pass 5**: everyone: the brass on the melody, the strings doubling it an octave up, the flute an octave up and the clarinet.
- **The ending**: a held chord over a snare roll, then a last C major chord with a crash and a kick, cut off.

```python {run name=finale}
from euterpe.instruments import BrassSection, Clarinet, Flute, Kit, Note, PizzicatoStrings, StringSection
from euterpe.pitch import B3, C2, C3, C4, C5, C6, D4, D5, E4, E5, F4, G2, G3, G4, G5
from euterpe.sound import FDNReverb
from tunes import notes

BAR = 60 / 72 * 3
starts = [BAR + 4 * BAR * k for k in range(5)]  # passes 1 to 5, four bars each, after one bar alone
end = starts[4] + 4 * BAR
length = end + 2 * BAR


def louder(at):
    """The velocity at time at: the whole piece is one crescendo, 0.35 to 0.95."""
    return min(0.95, 0.35 + 0.6 * at / end)


def theme(at, up=0):
    return notes("bolero", at, BAR / 3, up, louder(at))


kit, flute, clarinet = Kit(), Flute(), Clarinet()
strings, brass, pizz = StringSection(players=3), BrassSection(players=2), PizzicatoStrings()
snare = [n for n in kit.pattern({kit.snare: "x..xxxx..xxxx..x..x..xxxx..xxxxxxxxx"}, BAR / 18, repeat=11) if n.time < end]
for n in snare:
    n.velocity *= louder(n.time)
hold, last = [G2, B3, F4, G4], [C2, G3, E4, C5]
score = {
    kit: snare + kit.snare.roll(end, BAR, 0.5, 1.0) + kit.crash.hit(end + BAR, 1.0) + kit.kick.hit(end + BAR, 1.0),
    pizz: [Note(b * BAR + o, p, 0.3, louder(b * BAR)) for b in range(21) for o, p in ((0, C3), (2 * BAR / 3, G2))],
    flute: theme(starts[0]) + theme(starts[4], 12) + [Note(end, G5, BAR, 0.95), Note(end + BAR, C6, 0.5, 1.0)],
    clarinet: theme(starts[1]) + theme(starts[2], -12) + theme(starts[4]) + [Note(end, D5, BAR, 0.95), Note(end + BAR, E5, 0.5, 1.0)],
    strings: theme(starts[3]) + theme(starts[3], 12) + theme(starts[4], 12)
             + [Note(end, p, BAR, 0.95) for p in hold] + [Note(end + BAR, p, 0.5, 1.0) for p in last],
    brass: theme(starts[4], -12) + [Note(end, p, BAR, 0.95) for p in (G3, D4)] + [Note(end + BAR, p, 0.5, 1.0) for p in (C3, G3, C4)],
}
gains = {kit: 1.0, pizz: 1.2, flute: 1.0, clarinet: 0.8, strings: 0.9, brass: 0.8}


def mix(score):
    """Every instrument at its gain, through one hall."""
    return FDNReverb(sum(inst.play(ns) * gains[inst] for inst, ns in score.items()), decay=2.0, mix=0.25) * 0.4


song = mix(score)
```

```python {run continue}
from euterpe.view import listen

listen(song, length, "Ravel, Boléro (1928), from the flute to the brass")
```

Listen for the same four bars changing colour: the breathy flute, the hollow clarinet and its darker low octave, the shimmer of the section, and the brass turning the whole band bright as the last pass swells.

The snare under all of it has been the one sound in this chapter that nothing drives. It is a drum: a membrane stretched over a shell, with a set of wires under it, struck once and left to ring. Chapter 14 builds it, and the rest of the kit around it.

## Summary

- `Bow(freq, force, speed, position)` is a string kept moving by stick-slip friction: its waveform at the bridge is close to a sawtooth, and only a window of forces for each speed gives a clean note.
- `Bore(freq, pressure, mouth)` is an air column driven by a mouthpiece: `Reed()` closes one end and gives odd harmonics, `Jet()` and `Lips()` leave it open and give all of them. Below a threshold pressure no note starts.
- On a driven instrument velocity is force or breath, not gain: louder is brighter.
- `Vibrato(rate, cents, delay, rise)` swings the pitch of a held note, and is a part of `Violin`, `Flute` and the sections.
- `Violin`, `StringSection`, `Flute`, `Clarinet` and `BrassSection` build on these; a section is several independent players, each detuned and late by a little.

## Exercises

1. In the force block, change `speed=0.8` to `speed=0.3`. Which of the three takes changes most, and why?
2. In the threshold block, change `(3.0, 0.7)` to `(3.0, 0.2)`. Does the note ever speak?
3. In the brass block, change `BrassSection()` to `BrassSection(players=1)`. What is gone from the chords?

### Answers

1. Two of them swap. A slower bow needs less force to hold the string, so 0.02 now gives a clean note, and 0.5, the right force for a fast bow, is too much for a slow one and scratches like 1.0. The window of good forces moves with the speed.
2. No: the pressure now stops below the threshold, about 0.3, so the reed never feeds the tube and only the breath noise is heard, growing louder.
3. The beating: one player per note is a single clean tube, so the chords are steadier and thinner, and the brassy edge at velocity 1.0 sounds like one instrument instead of a section.

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
