# Euterpe: notes for agents

Euterpe is a Python library for composing music by writing code. It has four layers, each usable alone: sound (`euterpe/sound/`), instruments, theory and score, performance and mix. Only layer 1 exists so far. The design is `docs/superpowers/specs/2026-10-25-euterpe-design.html`; the current plan is in `docs/superpowers/plans/`.

## Layout

- `euterpe/sound/`: layer 1, sound units. A `Unit` answers `block(n)` with its next `n` samples and pulls from the units it was built on. `render` asks the top unit for blocks.
- `euterpe/io.py`: write and read audio files.
- `euterpe/lint/`: rules that measure audio (and later scores).
- `euterpe/book.py`: `listen` and `show`, used only by the book's executed code blocks.
- `book/`: the book, in scriptorium Markdown (`book/scriptorium.yaml`). Each chapter's code blocks run when the book builds, from `book/`, and write their sounds and figures under build/ inside book/
- `tests/`: one test file per module; `tests/helpers.py` holds spectrum helpers.

## Constraints

- Python 3.12 or later. Runtime dependencies: numpy, scipy, soundfile, pyloudnorm. Nothing else at runtime.
- Internal sample rate 48 000 Hz, float32. Mono is shape `(n,)`, stereo `(n, 2)`.
- Default block size 1024 frames. Rendering in any block size gives the same samples, to the bit.
- Every random source takes an explicit seed. The same unit graph and seed render the same samples.
- Every unit declares its parameters as `Param(name, unit, lo, hi, scale, default)`. A constant outside `[lo, hi]` raises `ValueError` naming the unit, parameter and range. A parameter may be a number or a `Unit`; a modulating signal is clipped to the range.
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

None yet.
