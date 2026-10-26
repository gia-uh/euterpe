when: writing or revising a chapter of the book in book/chapters/

# Writing a chapter

The book teaches music to a programmer who knows none, and it is also where a reader first meets Euterpe's API. Both jobs decide what a chapter shows.

## The code a reader sees is Euterpe code

A visible code block shows Euterpe making or changing sound: units, parameters, `render`, `listen`. Nothing else.

- Plots, tables, measurements and arithmetic that only serve the explanation run in hidden blocks, `{run echo=false}`. The reader sees the figure or the table they print, not the code. A hidden block that needs a variable from the visible block above it uses `{run continue echo=false}`.
- If a visible block needs numpy, a loop or a helper class to say something simple, the API is missing something. Propose the change to the API (a parameter, a method, a unit) in the pull request instead of hiding the workaround. Example: chapter 1 needed a saw without polyBLEP, so `Saw` gained `antialias=False` instead of the chapter defining a `NaiveSaw` class.
- Keep visible blocks short: a few lines that a reader can retype and change.

## Sounds and figures

- `listen(unit, seconds, "Caption")` renders, writes the MP3 and puts a player with that caption on the page. Pass `id="name"` only when the text refers to it as `@aud-name`.
- `show(fig, "Caption")` does the same for a matplotlib figure, from a hidden block.
- File names come from the caption and a hash of the content, so never name files by hand.
- Keep every example below full scale: `* 0.5` on a full-scale source.

## Prose

- Short sentences, real numbers, the mechanism instead of a metaphor.
- Each concept: prose that introduces it, a block that makes it audible or visible, then what to listen for.
- End with a summary list and three exercises the reader runs by changing one parameter.
- The chapter's last block is a hidden level check over every MP3 it wrote.

## Building and checking

```bash
cd book
rm -rf build site .scriptorium   # the freeze cache replays block output without rewriting files
uv run scriptorium render scriptorium.yaml --only site
```

Serve `book/site` over HTTP and open the chapter at 1440 px and 390 px wide: the players must play, and nothing may be wider than the phone.
