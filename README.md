# Euterpe

Euterpe is a Python library in which an agent composes music by writing code: sound synthesized from scratch, instruments built from that sound, scores written with the concepts of European tonal theory, and a linter that measures what can be measured. Its documentation is a book that teaches a computer scientist music from the physics of a wave up to a full orchestral score, with every example rendered from Euterpe's own code. Euterpe settles the mechanics of music; a human judges whether a piece is good.

Status: milestone 1 (sound) is in progress. See the pinned vision issue.

## Install

```bash
uv add git+https://github.com/gia-uh/euterpe
```

## Example

A plucked A3, rendered to MP3.

```python
from euterpe.sound import Pluck, render

# Karplus-Strong: a burst of noise circulating in a delay line 1/220 s long
note = Pluck(220.0, damping=0.996, seed=1)

# two seconds at 48 kHz, written as MP3; render returns the path
path = render(note, 2.0, to="pluck-a3.mp3")
print(path)
```

## Development

```bash
uv sync --group dev
uv run pytest -q
```

The design is in `docs/superpowers/specs/`, the milestone plans in `docs/superpowers/plans/`.

## License

MIT.
