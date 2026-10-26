when: writing or revising a chapter of the book in book/chapters/

# Writing a chapter

The book teaches music to a programmer who knows none, and it is also where a reader first meets Euterpe's API. Both jobs decide what a chapter shows.

## Code that is knowledge stays visible

A visible block is code the reader learns from and can retype and change. Two kinds qualify, when they are short and simple:

- Euterpe code that makes or changes sound: units, parameters, `render`, `listen`.
- Short numpy or scipy code that computes the physics or maths the chapter teaches. Chapter 1 shows the comparison of the 44 000 Hz and 4 000 Hz samples and the measurement of folded energy, because a reader who doubts the claim wants to run and change exactly that code.

Utility code runs hidden, in `{run echo=false}` blocks: plotting and drawing (matplotlib), formatting of tables and text, bookkeeping, level checks. A hidden block that needs a variable from the block above it uses `{run continue echo=false}`.

- Never present a number as if the reader could reproduce it with code they cannot see. If the prose quotes a measured value, the code that measures it is on the page, or the number comes from a formula in the text.
- If a visible block needs a workaround (a loop, a helper class, raw numpy) to say something simple in Euterpe, the API is missing something. Propose the change to the API (a parameter, a method, a unit) in the pull request instead of hiding or keeping the workaround. Example: chapter 1 needed a saw without polyBLEP, so `Saw` gained `antialias=False` instead of the chapter defining a `NaiveSaw` class.
- Keep visible blocks short: a few lines, with every name in them explained in the prose around them.

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
