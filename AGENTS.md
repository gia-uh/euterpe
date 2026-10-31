# Euterpe: notes for agents

Euterpe is a Python library for composing music by writing code. It has four layers, each usable alone: sound (`euterpe/sound/`), instruments (`euterpe/instruments/`), theory and score (`euterpe/theory/`, `euterpe/score/`), performance and mix. Layers 1 to 3 exist so far. The design is `docs/superpowers/specs/2026-10-25-euterpe-design.html`; the current plan is in `docs/superpowers/plans/`.

## Layout

- `euterpe/sound/`: layer 1, sound units. A `Unit` answers `block(n)` with its next `n` samples and pulls from the units it was built on. `render` asks the top unit for blocks.
- `euterpe/instruments/`: layer 2, instruments that turn notes into sound: an `Instrument` gives each `Note` a voice, and `play(notes)` returns a `Phrase`, a unit.
- `euterpe/theory/`: layer 3, pure values with no audio: `Scale`, `Key`, `Chord`, `Roman`, `Meter`, the tunings. `euterpe/pitch.py` holds the spelled `Pitch` and `Interval`, below the instruments.
- `euterpe/score/`: layer 3, a `Score` of parts in written time as `Fraction`s, its notation (`melody`, `chords`, `drums`), the performance that turns it into layer 2 notes, the renderer, and the MusicXML and MIDI writers.
- `euterpe/io.py`: write and read audio files.
- `euterpe/cli.py`: the `euterpe` command, `render`, `lint` and `inspect`. A piece is a file whose `score()` returns a `Score`.
- `euterpe/inspect.py`: `inspect(score, out)` writes a piece's piano rolls, spectrogram, chroma, loudness and `summary.txt`; `estimate_key` and `chords_per_beat` read audio against the score. `cli.py` also imports the standard library's `inspect`, so this one is imported as `inspect_piece` there, and `euterpe` does not export it.
- `euterpe/lint/`: rules that measure audio and scores. `lint_audio`, `lint_score` and `lint_piece` (`euterpe/lint/score/`) return a `Report` of `Finding`s; a `Profile` reads a score in a style.
- `euterpe/view/`: views of sounds (`display(x)`, `x.spectrum()`, `listen(x)`) in the house style, through IPython's rich display; the book and notebooks show them.
- `euterpe/book.py`: `gain_db`, a measuring helper for the book's executed code blocks.
- `book/`: the book, in scriptorium Markdown (`book/scriptorium.yaml`). Each chapter's code blocks run when the book builds, from `book/`, and write their sounds and figures to `build` inside the book directory.
- `tests/`: one test file per module; `tests/helpers.py` holds spectrum helpers.

## Constraints

- Python 3.12 or later. Runtime dependencies: numpy, scipy, soundfile, pyloudnorm. Nothing else at runtime.
- Every file format Euterpe writes or reads (audio, MusicXML, MIDI, any later one) is written and read by Euterpe's own code on the standard library (`struct`, `xml.etree`, `zipfile`), with no third-party library, in the tests too: a test reads a file back with Euterpe's own reader, never with mido, music21 or the like. Drawing (matplotlib, the `view` extra) and staff engraving (verovio, the `notation` extra) are optional extras the book uses; the library imports them only inside the function that draws.
- Internal sample rate 48 000 Hz, float32. Mono is shape `(n,)`, stereo `(n, 2)`.
- Default block size 1024 frames. Rendering in any block size gives the same samples, to the bit.
- Every random source takes an explicit seed. The same unit graph and seed render the same samples.
- A unit's parameters are ordinary constructor arguments kept as attributes. Each may be a number or a `Unit` that moves it every sample; `_signal(x, n)` turns either into a block, and `inputs()` finds the attributes that are units. No unit validates a range for its own sake: each clips where its own numerics require it (a cutoff below Nyquist, q above 0) and raises `ValueError` only for a model it cannot build (a feedback loop that grows without end).
- Each model is its own class (`LowPass`, `Tanh`); no unit picks its model with a string. `Formant`'s vowel is data, a table of formants, not a model.
- Some parameters fix the unit's structure when it is built and take numbers only, raising `TypeError` for a `Unit`: `Comb` and `Allpass` (delay and gain), `Pluck` (all four: the loop length and its filters are set when the string is plucked), `Bow` (position, damping, brightness), `Bore` (mouth, damping, bell), `Phaser.stages`, `Limiter.ceiling`, `Cabinet.size`, `FDNReverb` (decay, size, damping) and `ConvolutionReverb.decay`. `Modal` takes lists (`freqs`, `decays`, `amps`) and validates them itself. `Delay` with a moving time needs `max_time`, which sizes its line and its tail.
- Each unit's docstring says what it does to the spectrum.
- `render(..., to=path)` writes the file and returns its `Path`.
- Algorithms (polyBLEP, LFSR noise, Karplus-Strong) are written from their published descriptions. Nothing is copied from other projects.
- English for code, docs, book and lint messages. This repo is public: nothing names a person, machine or account.

## Tests

```bash
uv sync --group dev
uv run pytest -q -n auto
```

No test takes more than 5 s in one process (`uv run pytest -q --durations=10` lists the slowest). Render the shortest stretch that shows the fact: a block-size check at block 1 covers a few hundredths of a second, and a peak check renders the hit, not its tail.

Work lands through an issue, a branch and a pull request; CI must be green before merge.

## Know-how

Print the menu with `grep -m1 -H '^when:' know-how/*.md` and read what matches.

- Writing a piece as a score, alone or without ears → `know-how/composing-a-piece.md`.
- Writing or revising a chapter → `know-how/writing-a-chapter.md`. Visible code is Euterpe code and short maths that is the lesson; plots, formatting and checks run hidden.
