when: writing or revising a chapter of the book in book/chapters/

# Writing a chapter

The book teaches music to a programmer who knows none, and it is also where a reader first meets Euterpe's API. Both jobs decide what a chapter shows.

## Code that is knowledge stays visible

A visible block is code the reader learns from and can retype and change. Two kinds qualify, when they are short and simple:

- Euterpe code that makes or changes sound: units, parameters, `take`, `listen`, the views.
- Short numpy or scipy code that computes the physics or maths the chapter teaches. Chapter 1 shows the comparison of the 44 000 Hz and 4 000 Hz samples and the `fold` rule, because a reader who doubts the claim wants to run and change exactly that code.

Utility code runs hidden, in `{run echo=false}` blocks: hand-made drawings, formatting of tables and text, bookkeeping, level checks. A hidden block that needs a variable from the block above it uses `{run continue echo=false}`.

- Never present a number as if the reader could reproduce it with code they cannot see. If the prose quotes a measured value, the code that measures it is on the page, or the number comes from a formula in the text.
- If a visible block needs a workaround (a loop, a helper class, raw numpy) to say something simple in Euterpe, the API is missing something. Propose the change to the API (a parameter, a method, a unit) in the pull request instead of hiding or keeping the workaround. Example: chapter 1 needed a saw without polyBLEP, so `Saw` gained `antialias=False` instead of the chapter defining a `NaiveSaw` class.
- Keep visible blocks short: a few lines, with every name in them explained in the prose around them.

## Sounds and figures

- `listen(unit, seconds, "Caption")` (from `euterpe.view`) puts a player with that caption on the page. Pass `id="name"` only when the text refers to it as `@aud-name`. As the last line of a block it shows itself; anywhere else write `display(listen(...))`.
- A figure is one view call with `caption=`: `clip.waveform()`, `spectrum(a, b, f0=220, labels=[...])`, `clip.spectrogram()`, `level(...)`, `filter.response()`, `shaper.curve()`, `row(left, right)`. Views draw in the house style of `docs/superpowers/specs/2026-10-26-display-api-design.html`, section 06.
- A drawing that plots a function rather than a sound goes through `figure(draw, caption=...)`, where `draw` returns the matplotlib figure; it is drawn in the house style too. If a sound needs hand-made matplotlib, the view API is missing something: propose the view instead.
- File names come from the caption and a hash of the content, so never name files by hand.
- Keep every example below full scale: `* 0.5` on a full-scale source.

## Pacing

A chapter loses the reader when it re-shows what they have already heard. Five rules, from the pacing review of issue #45:

1. **Sound first, destination first.** The first player comes by line 20, a 5 to 10 s teaser of the closing piece. No table or derivation comes before the sound it explains. A teaser that needs the closing code runs hidden and executes the closing blocks, found by their `name=`, from the chapter file (chapter 11 does this), so the two never differ.
2. **Two takes per knob.** Show both extremes of a parameter in one block; add a third only when the middle value is the lesson. A parameter taught in an earlier chapter gets a sentence and a back-reference, no block.
3. **One proof per fact.** A player, a figure or a table, not two or three of them. Checks that only confirm the author's numbers run hidden. Earlier terms are cited, never re-explained; no glossary walls.
4. **Music by the middle, built in layers.** A phrase of at least four notes, or a bar of rhythm, by the midpoint; each later section adds one layer to it, so the closing piece is assembled across the chapter. Budget: about 300 lines, at most 18 code blocks, at most 3 printed tables (the level check and the exercises' answers do not count).
5. **End on the closing piece, and open the door.** At least 20 s, with at least three of the chapter's tools sounding at once, a known piece or a recognisable genre. Its last paragraph names what it cannot do yet, which the next chapter adds. Solo showcases go before it, not instead of it.

Blocks that share variables chain with `{run continue}`: every block after the first of a chain must carry it, or the chain breaks and every later block fails with `NameError`. The site build does not fail on a block's error; it prints the traceback on the page, so search the built page for `Traceback`.

## Prose

- Short sentences, real numbers, the mechanism instead of a metaphor.
- Each concept: prose that introduces it, a block that makes it audible or visible, then what to listen for.
- End with a summary list and three exercises the reader runs by changing one parameter.
- The chapter's last block is a hidden level check over every MP3 it wrote.

## Building and checking

```bash
cd book
rm -rf build site .scriptorium   # only after a change to euterpe/: the cache cannot see the library
uv run scriptorium render scriptorium.yaml --only site
```

The freeze cache in `.scriptorium` keeps each chapter's block output, and the files in `build`, until the chapter's text changes; then every block of that chapter runs again. CI keeps both between builds (`.github/workflows/book.yml`) and starts empty when `euterpe/` or `uv.lock` changes.

Serve `book/site` over HTTP and open the chapter at 1440 px and 390 px wide: the players must play, and nothing may be wider than the phone.
