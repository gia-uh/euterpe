# Preface {.unnumbered}

This book is for a programmer who knows no music. It starts from what a sound is, a pressure that changes over time, and builds up to pieces of music. On the way it introduces Euterpe, a Python library in which every sound is made by code.

Each idea comes in three steps. A few sentences say what it is. A code block makes it: a sound you can play or a picture you can look at. Then the text says what to listen for and what the numbers mean. The players and pictures on these pages were made by the code blocks above them when the book was built, so what you hear is what the code does.

## Running the examples

Most examples are complete programs. A few build on the block just before them, and the text says so where they do; to run one of those, put it after the blocks it builds on, in the same file. To run the examples yourself, install Euterpe and the book's extras from a clone of the repository:

```bash
git clone https://github.com/gia-uh/euterpe
cd euterpe/book
uv sync --group book
uv run python example.py
```

where `example.py` holds a code block from a chapter. An example that calls `listen` writes an MP3 under `build/audio/`; one that calls `show` writes an SVG under `build/img/`. Open them with any player or browser.

Each chapter ends with three exercises. Each one changes a number in an example; run it again and listen to what changed.
