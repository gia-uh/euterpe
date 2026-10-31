"""The euterpe command: render, lint or inspect a piece, render a function's unit to a file, or lint a unit or an audio
file.

A piece is path.py, a file whose score() returns a Score. A target is path.py:function, where the function returns a
Unit.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from euterpe.inspect import inspect as inspect_piece
from euterpe.instruments import Phrase
from euterpe.io import read, write
from euterpe.lint import PROFILES, Report, lint_audio, lint_notes, lint_piece
from euterpe.score import Score
from euterpe.sound.core import RATE, Unit, render

_NOTATED = (".mid", ".midi", ".musicxml")


class _TargetError(Exception):
    pass


def _is_target(text: str) -> bool:
    return ":" in text and text.rpartition(":")[0].endswith(".py")


def _is_piece(text: str) -> bool:
    return text.endswith(".py")


def _call(target: str, seed: int | None):
    """Import path.py and call its function, with seed= when the function takes one."""
    path, _, name = target.rpartition(":")
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    if spec is None or not Path(path).is_file():
        raise _TargetError(f"cannot load {path}: no such file")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise _TargetError(f"cannot import {path}: {type(e).__name__}: {e}") from None
    fn = getattr(module, name, None)
    if not callable(fn):
        names = sorted(
            n for n, v in vars(module).items()
            if inspect.isfunction(v) and v.__module__ == module.__name__ and not n.startswith("_")
        )
        raise _TargetError(f"{path} has no function {name}; its functions are: {', '.join(names)}; "
                           "a piece is path.py with a score() function, and path.py:function names any other")
    param = inspect.signature(fn).parameters.get("seed")
    takes_seed = param is not None
    if takes_seed and seed is None and param.default is inspect.Parameter.empty:
        raise _TargetError(f"{target} takes a seed: pass --seed N")
    try:
        return fn(seed=seed) if takes_seed and seed is not None else fn()
    except Exception as e:
        raise _TargetError(f"{target} failed: {type(e).__name__}: {e}") from None


def _load(target: str, seed: int | None) -> Unit:
    unit = _call(target, seed)
    if not isinstance(unit, Unit):
        raise _TargetError(f"{target} returned {type(unit).__name__}, not a Unit")
    return unit


def _piece(path: str, seed: int | None) -> Score:
    score = _call(f"{path}:score", seed)
    if inspect.isgenerator(score):
        raise _TargetError(f"{path}: generator scores come with milestone 5")
    if not isinstance(score, Score):
        raise _TargetError(f"{path}:score returned {type(score).__name__}, not a Score")
    return score


def _play(score: Score, path: str, seed: int | None):
    """The piece's unit, from --seed; a usage error for a score that cannot play."""
    try:
        return score.play(seed or 0)
    except ValueError as e:
        raise _TargetError(f"cannot play {path}: {e}") from None


def _check_seconds(seconds: float) -> None:
    if seconds <= 0:
        raise _TargetError(f"--seconds must be above 0, got {seconds:g}")


def _export(score: Score, args) -> int:
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        if out.suffix.lower() == ".musicxml":
            score.to_musicxml(out)
        else:
            score.to_midi(out)
    except ValueError as e:
        raise _TargetError(f"cannot write {out}: {e}") from None
    print(f"{out}: bars 1 to {score.bars}")
    return 0


def _render(args) -> int:
    notated = Path(args.output).suffix.lower() in _NOTATED
    if _is_piece(args.target):
        score = _piece(args.target, args.seed)
        if notated:
            if args.seconds is not None or args.rate != RATE:
                raise _TargetError(f"{args.output} holds notation, not audio, so it takes no --seconds or --rate")
            return _export(score, args)
        unit = _play(score, args.target, args.seed)
        if args.seconds is None and unit.duration == 0:
            raise _TargetError(f"{args.target} has nothing written, so there is nothing to render")
        seconds = unit.duration if args.seconds is None else args.seconds
    else:
        if notated:
            raise _TargetError(f"{args.target} returns a Unit, which has no written notes for {args.output}: "
                               "write a piece, path.py with a score() function")
        if args.seconds is None:
            raise _TargetError(f"rendering {args.target} needs --seconds: how long to render it")
        unit, seconds = _load(args.target, args.seed), args.seconds
    _check_seconds(seconds)
    samples = render(unit, seconds)
    try:
        out = write(samples, args.output, rate=args.rate)
    except ValueError as e:
        raise _TargetError(str(e)) from None
    peak = float(np.abs(samples).max()) if samples.size else 0.0
    level = f"{20 * np.log10(peak):.1f} dBFS" if peak > 0 else "silent"
    print(f"{out}: {seconds:g} s, peak {level}")
    if peak >= 1.0:
        print(f"euterpe: warning: {out} is clipped: the samples peak at {level}, above full scale", file=sys.stderr)
    return 0


def _lint_piece(args) -> int:
    score = _piece(args.input, args.seed)
    if args.seconds is not None or args.loop:
        raise _TargetError(f"linting {args.input} takes no --seconds or --loop: "
                           "a piece renders whole and does not loop")
    report = lint_piece(score, args.profile, args.seed or 0, audio=not args.no_audio)
    print(report.to_json() if args.json else report.to_text())
    return 1 if report.errors else 0


def _lint(args) -> int:
    if _is_piece(args.input):
        return _lint_piece(args)
    if args.profile or args.no_audio:
        raise _TargetError(f"--profile and --no-audio read a score, and {args.input} is not a piece: "
                           "path.py with a score() function")
    notes = Report()
    if _is_target(args.input):
        if args.seconds is None:
            raise _TargetError(f"linting {args.input} needs --seconds: how long to render it")
        _check_seconds(args.seconds)
        unit = _load(args.input, args.seed)
        if isinstance(unit, Phrase):
            notes = lint_notes(unit)
        samples, rate = render(unit, args.seconds), RATE
    elif not Path(args.input).is_file():
        raise _TargetError(f"cannot lint {args.input}: no such file")
    else:
        try:
            samples, rate = read(args.input)
        except sf.LibsndfileError as e:
            raise _TargetError(f"cannot read {args.input} as audio: {e.error_string}") from None
    report = Report(notes.findings + lint_audio(samples, rate, loop=args.loop).findings)
    print(report.to_json() if args.json else report.to_text())
    return 1 if report.errors else 0


def _inspect(args) -> int:
    score = _piece(args.piece, args.seed)
    try:
        paths = inspect_piece(score, args.output, args.seed or 0)
    except (ImportError, OSError, ValueError) as e:
        raise _TargetError(f"cannot inspect {args.piece}: {e}") from None
    print("\n".join(map(str, paths)))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the euterpe command with argv (default sys.argv[1:]) and return its exit code."""
    parser = argparse.ArgumentParser(prog="euterpe", description="Compose music by writing code.")
    commands = parser.add_subparsers(dest="command", required=True)

    r = commands.add_parser("render", help="render a piece or path.py:function to a file")
    r.add_argument("target", help="path.py, a piece with a score() function, or path.py:function, a function that "
                                  "returns a Unit")
    r.add_argument("-o", "--output", required=True,
                   help="the file to write: .wav, .flac, .mp3 or .ogg; for a piece also .mid, .midi or .musicxml")
    r.add_argument("--seconds", type=float,
                   help="how long to render (required for path.py:function; a piece defaults to its duration)")
    r.add_argument("--seed", type=int,
                   help="passed to the function as seed=, when it takes one, and to a piece's performance")
    r.add_argument("--rate", type=int, default=RATE, help="the file's sample rate (default 48000)")
    r.set_defaults(run=_render)

    lint = commands.add_parser("lint", help="measure an audio file, a piece or path.py:function; exit 1 on an error")
    lint.add_argument("input", help="an audio file, path.py, a piece with a score() function, or path.py:function")
    lint.add_argument("--seconds", type=float, help="how long to render a function (required for one)")
    lint.add_argument("--seed", type=int,
                      help="passed to the function as seed=, when it takes one, and to a piece's performance")
    lint.add_argument("--profile", choices=sorted(PROFILES), help="the style a piece's rules read it in")
    lint.add_argument("--no-audio", action="store_true", help="read a piece's score only, with no render")
    lint.add_argument("--loop", action="store_true", help="also check that the end joins the start")
    lint.add_argument("--json", action="store_true", help="print the report as JSON")
    lint.set_defaults(run=_lint)

    look = commands.add_parser("inspect", help="write a piece's piano rolls, spectrogram, chroma, loudness and summary")
    look.add_argument("piece", help="path.py, a piece with a score() function")
    look.add_argument("-o", "--output", required=True, help="the directory to write into, made if missing")
    look.add_argument("--seed", type=int, help="passed to score() as seed=, when it takes one, and to its performance")
    look.set_defaults(run=_inspect)

    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except _TargetError as e:
        print(f"euterpe: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
