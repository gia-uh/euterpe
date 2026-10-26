# Euterpe: notes for agents

Euterpe is a Python library for composing music by writing code. It has four layers, each usable alone: sound (`euterpe/sound/`), instruments, theory and score, performance and mix. Only layer 1 exists so far. The design is `docs/superpowers/specs/2026-10-25-euterpe-design.html`; the current plan is in `docs/superpowers/plans/`.

## Layout

- `euterpe/sound/`: layer 1, sound units. A `Unit` answers `block(n)` with its next `n` samples and pulls from the units it was built on. `render` asks the top unit for blocks.
- `euterpe/io.py`: write and read audio files.
- `euterpe/cli.py`: the `euterpe` command, `render` and `lint`.
- `euterpe/lint/`: rules that measure audio (and later scores). `lint_audio` returns a `Report` of `Finding`s.
- `euterpe/view/`: views of sounds (`display(x)`, `x.spectrum()`, `listen(x)`) in the house style, through IPython's rich display; the book and notebooks show them.
- `euterpe/book.py`: `gain_db`, a measuring helper for the book's executed code blocks.
- `book/`: the book, in scriptorium Markdown (`book/scriptorium.yaml`). Each chapter's code blocks run when the book builds, from `book/`, and write their sounds and figures to `build` inside the book directory.
- `tests/`: one test file per module; `tests/helpers.py` holds spectrum helpers.

## Constraints

- Python 3.12 or later. Runtime dependencies: numpy, scipy, soundfile, pyloudnorm. Nothing else at runtime.
- Internal sample rate 48 000 Hz, float32. Mono is shape `(n,)`, stereo `(n, 2)`.
- Default block size 1024 frames. Rendering in any block size gives the same samples, to the bit.
- Every random source takes an explicit seed. The same unit graph and seed render the same samples.
- Every unit declares its parameters as `Param(name, unit, lo, hi, scale, default)`. A constant outside `[lo, hi]` raises `ValueError` naming the unit, parameter and range. A parameter may be a number or a `Unit`; a modulating signal is clipped to the range.
- Exceptions, where a parameter fixes the unit's structure when it is built: `Comb` and `Allpass` (delay and gain), `Pluck` (all four: the loop length and its filters are set when the string is plucked), `Phaser.stages`, `Limiter.ceiling`, `FDNReverb` (decay, size, damping) and `ConvolutionReverb.decay` take numbers only and raise `TypeError` for a `Unit`. `Modal` takes lists (`freqs`, `decays`, `amps`), declares no `Param` and validates them itself.
- Each unit's docstring says what it does to the spectrum.
- `render(..., to=path)` writes the file and returns its `Path`.
- Algorithms (polyBLEP, LFSR noise, Karplus-Strong) are written from their published descriptions. Nothing is copied from other projects.
- English for code, docs, book and lint messages. This repo is public: nothing names a person, machine or account.

## Tests

```bash
uv sync --group dev
uv run pytest -q
```

Work lands through an issue, a branch and a pull request; CI must be green before merge.

## Know-how

Print the menu with `grep -m1 -H '^when:' know-how/*.md` and read what matches.

- Writing or revising a chapter → `know-how/writing-a-chapter.md`. Visible code is Euterpe code and short maths that is the lesson; plots, formatting and checks run hidden.
