when: writing a piece as a score, alone or as an agent without ears

# Composing a piece

A piece is one Python file whose `score()` returns a `Score`. If `score` takes `seed`, it receives `--seed`, and the same seed reaches the performance. Each command below reads that file.

```python
from euterpe import Key, Meter, Score, chords, melody
from euterpe.instruments import Harp, StringSection


def score():
    s = Score(key=Key("D major"), meter=Meter("3/4"), tempo=84)
    s.part("melody", Harp()).add(melody("f#4:q a4 d5 | c#5:h b4:q | a4:h."))
    s.part("chords", StringSection(players=2)).add(chords("I:h. | V:h. | I:h.", voicing="close"))
    return s
```

## The loop

1. Write or change one thing in the score.
2. Lint with a profile: `euterpe lint piece.py --profile chorale --no-audio`, which reads only the score and takes no render. Exit 1 means an error-level finding, 2 a usage error. Add `--json` to read the findings as data. A style's rule is not a law: a finding names its profile, so choose the profile that matches the piece (`chorale`, `pop`, `techno`).
3. Inspect: `euterpe inspect piece.py -o inspect/`. It renders the piece, writes `roll-<part>.png` per part, `spectrogram.png`, `chroma.png`, `loudness.png` and `summary.txt`, and prints each path, `summary.txt` last. It needs matplotlib (`euterpe[view]`).
4. Read `summary.txt`. Each line is one fact.
5. Fix one finding and go back to 2. One at a time, so that the next run shows what that change did.

Render when the summary holds up: `euterpe render piece.py -o piece.mp3 --seed 7`. `-o` also takes `.mid`, `.midi` and `.musicxml`, which write the notation with no render.

## Reading summary.txt

The piece above, trimmed:

```text
length: 6.78 s
loudness: -18.9 LUFS
true peak: -6.1 dBTP
key: D major (audio 0.85), written D major
chord 1.1: audio D, written D
chord 2.1: audio A, written A/C#
part melody: 6 notes, F#4 to D5
part chords: 9 notes, C#4 to A4
metric H-KEY: part melody: 0% of the note time is outside the key
metric A-PEAK: sample peak -6.2 dBFS
```

- `key`: the audio's estimate and its correlation, beside the written key. It can be wrong when your notes are right, so never change notes on this line alone. Over 61 progressions and lines on Organ, Harp, ElectricPiano, Violin, Flute and Clarinet it named the written key 57 times. All four misses were chords in a major key read as its dominant, at 0.66 to 0.89 (B major for E major). An estimate a fifth above the written key therefore says little. Any other disagreement is worth checking against `metric H-KEY`, which reads the written notes and says how much of their time is outside the key. On a piece of drums alone the estimate means nothing: it is reading noise.
- `chord <bar>.<beat>`: what the audio holds beside what the score says, one line per beat as played, so a repeat appears once per pass. `?` means nothing fits: the audio side names only major, minor and diminished triads and the dominant, major and minor sevenths, in root position, since chroma has no octave. `written A/C#` beside `audio A` is agreement. A difference where you expected agreement is a finding worth reading: a balance that buries a chord tone, or a wrong note.
- `part`: how many notes each part writes and its lowest and highest pitch, so you can check a part's range.
- `metric`: every lint metric, with no profile. The rules that a profile turns on or into warnings come from step 2.
- `loudness` says it cannot measure a clip under 0.4 s or one too quiet to gate.

A score can draw `s.chroma()`, the written pitch classes per beat with no render, and the audio's is `chroma.png`. Compare the two when `chord` lines disagree and the reason is not plain.
