# Preface {.unnumbered}

This book is for a programmer who knows no music. It starts from what a sound is, a pressure that changes over time, and builds up to pieces of music. On the way it introduces Euterpe, a Python library in which every sound is made by code.

Each idea comes in three steps. A few sentences say what it is. A code block makes it: a sound you can play or a picture you can look at. Then the text says what to listen for and what the numbers mean. The players and pictures on these pages were made by the code blocks above them when the book was built, so what you hear is what the code does.

## Running the examples

Most examples are complete programs. A few build on the block just before them, and the text says so where they do; to run one of those, put it after the blocks it builds on, in the same file. To run the examples yourself, install Euterpe and the book's extras from a clone of the repository:

```bash
git clone https://github.com/gia-uh/euterpe
cd euterpe/book
uv sync --group book
uv run --with jupyterlab jupyter lab
```

and paste a code block from a chapter into a notebook cell. `display(sound.take(seconds, caption))` gives a drawing and a player, `listen` gives the player alone, and the views give other drawings: the notebook shows the last line of a cell, and `display(...)` shows any other line, as the book does.

Each chapter ends with three exercises. Each one changes a number in an example; run it again and listen to what changed.
