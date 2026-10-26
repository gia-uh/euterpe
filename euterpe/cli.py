"""The euterpe command: render a function's unit to a file, or lint a unit or an audio file.

A target is path.py:function, where the function returns a Unit.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from euterpe.io import read, write
from euterpe.lint import lint_audio
from euterpe.sound.core import RATE, Unit, render


class _TargetError(Exception):
    pass


def _is_target(text: str) -> bool:
    return ":" in text and text.rpartition(":")[0].endswith(".py")


def _load(target: str, seed: int | None) -> Unit:
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
        raise _TargetError(f"{path} has no function {name}; its functions are: {', '.join(names)}")
    param = inspect.signature(fn).parameters.get("seed")
    takes_seed = param is not None
    if takes_seed and seed is None and param.default is inspect.Parameter.empty:
        raise _TargetError(f"{target} takes a seed: pass --seed N")
    unit = fn(seed=seed) if takes_seed and seed is not None else fn()
    if not isinstance(unit, Unit):
        raise _TargetError(f"{target} returned {type(unit).__name__}, not a Unit")
    return unit


def _check_seconds(seconds: float) -> None:
    if seconds <= 0:
        raise _TargetError(f"--seconds must be above 0, got {seconds:g}")


def _render(args) -> int:
    _check_seconds(args.seconds)
    samples = render(_load(args.target, args.seed), args.seconds)
    try:
        out = write(samples, args.output, rate=args.rate)
    except ValueError as e:
        raise _TargetError(str(e)) from None
    peak = float(np.abs(samples).max()) if samples.size else 0.0
    level = f"{20 * np.log10(peak):.1f} dBFS" if peak > 0 else "silent"
    print(f"{out}: {args.seconds:g} s, peak {level}")
    if peak >= 1.0:
        print(f"euterpe: warning: {out} is clipped: the samples peak at {level}, above full scale", file=sys.stderr)
    return 0


def _lint(args) -> int:
    if _is_target(args.input):
        if args.seconds is None:
            raise _TargetError(f"linting {args.input} needs --seconds: how long to render it")
        _check_seconds(args.seconds)
        samples, rate = render(_load(args.input, args.seed), args.seconds), RATE
    elif args.input.endswith(".py"):
        raise _TargetError(f"{args.input} needs a function to call: {args.input}:function")
    elif not Path(args.input).is_file():
        raise _TargetError(f"cannot lint {args.input}: no such file")
    else:
        try:
            samples, rate = read(args.input)
        except sf.LibsndfileError as e:
            raise _TargetError(f"cannot read {args.input} as audio: {e.error_string}") from None
    report = lint_audio(samples, rate, loop=args.loop)
    print(report.to_json() if args.json else report.to_text())
    return 1 if report.errors else 0


def main(argv: list[str] | None = None) -> int:
    """Run the euterpe command with argv (default sys.argv[1:]) and return its exit code."""
    parser = argparse.ArgumentParser(prog="euterpe", description="Compose music by writing code.")
    commands = parser.add_subparsers(dest="command", required=True)

    r = commands.add_parser("render", help="render path.py:function to an audio file")
    r.add_argument("target", help="path.py:function, a function that returns a Unit")
    r.add_argument("-o", "--output", required=True, help="the file to write: .wav, .flac, .mp3 or .ogg")
    r.add_argument("--seconds", type=float, required=True, help="how long to render")
    r.add_argument("--seed", type=int, help="passed to the function as seed=, when it takes one")
    r.add_argument("--rate", type=int, default=RATE, help="the file's sample rate (default 48000)")
    r.set_defaults(run=_render)

    lint = commands.add_parser("lint", help="measure an audio file or path.py:function; exit 1 on an error")
    lint.add_argument("input", help="an audio file, or path.py:function")
    lint.add_argument("--seconds", type=float, help="how long to render a function (required for one)")
    lint.add_argument("--seed", type=int, help="passed to the function as seed=, when it takes one")
    lint.add_argument("--loop", action="store_true", help="also check that the end joins the start")
    lint.add_argument("--json", action="store_true", help="print the report as JSON")
    lint.set_defaults(run=_lint)

    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except _TargetError as e:
        print(f"euterpe: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
