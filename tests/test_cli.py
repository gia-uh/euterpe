import json

import numpy as np
import pytest

from euterpe.cli import main
from euterpe.io import read, write

PIECE = '''
from euterpe.sound import Saw, Sine


def tone():
    return Sine(440.0) * 0.5


def seeded(seed):
    return Sine(220.0 * (1 + seed)) * 0.5


def loud():
    return Saw(110.0) * 2.0
'''


@pytest.fixture
def piece(tmp_path):
    path = tmp_path / "piece.py"
    path.write_text(PIECE)
    return path


def test_render_writes_the_file_and_reports_its_peak(piece, tmp_path, capsys):
    out = tmp_path / "tone.mp3"
    assert main(["render", f"{piece}:tone", "-o", str(out), "--seconds", "1"]) == 0
    assert out.is_file()
    assert capsys.readouterr().out == f"{out}: 1 s, peak -6.0 dBFS\n"


def test_render_passes_the_seed_and_the_rate(piece, tmp_path):
    out = tmp_path / "s.wav"
    assert main(["render", f"{piece}:seeded", "-o", str(out), "--seconds", "1", "--seed", "1", "--rate", "44100"]) == 0
    x, rate = read(out)
    assert rate == 44_100 and len(x) == 44_100


def test_lint_a_clipped_file_exits_1(tmp_path, capsys):
    path = write(np.full(48_000, 1.0, np.float32), tmp_path / "clip.wav")
    assert main(["lint", str(path)]) == 1
    assert "A-CLIP" in capsys.readouterr().out


def test_lint_a_target_as_json(piece, capsys):
    assert main(["lint", f"{piece}:tone", "--seconds", "1", "--json"]) == 0
    rules = [f["rule"] for f in json.loads(capsys.readouterr().out)["findings"]]
    assert "A-PEAK" in rules and "A-CLIP" not in rules


def test_lint_a_target_that_clips(piece):
    assert main(["lint", f"{piece}:loud", "--seconds", "1"]) == 1


def test_a_missing_function_exits_2_naming_the_functions(piece, tmp_path, capsys):
    assert main(["render", f"{piece}:nope", "-o", str(tmp_path / "x.mp3"), "--seconds", "1"]) == 2
    err = capsys.readouterr().err
    assert "nope" in err and "loud, seeded, tone" in err


def test_a_target_needs_seconds(piece, capsys):
    assert main(["lint", f"{piece}:tone"]) == 2
    assert "--seconds" in capsys.readouterr().err


def test_render_warns_when_the_file_clips(piece, tmp_path, capsys):
    assert main(["render", f"{piece}:loud", "-o", str(tmp_path / "l.wav"), "--seconds", "1"]) == 0
    assert "clipped" in capsys.readouterr().err


@pytest.mark.parametrize("args", [["nofile.wav"], ["notes.txt"], ["{piece}", "--seconds", "1"]])
def test_lint_input_it_cannot_read_exits_2(piece, tmp_path, monkeypatch, capsys, args):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "notes.txt").write_text("not audio")
    assert main(["lint", *(a.format(piece=piece) for a in args)]) == 2
    assert capsys.readouterr().err.startswith("euterpe: ")


def test_a_function_that_needs_a_seed_exits_2_without_one(piece, tmp_path, capsys):
    assert main(["render", f"{piece}:seeded", "-o", str(tmp_path / "s.wav"), "--seconds", "1"]) == 2
    assert "--seed" in capsys.readouterr().err


def test_an_unknown_output_extension_exits_2(piece, tmp_path, capsys):
    assert main(["render", f"{piece}:tone", "-o", str(tmp_path / "a.xyz"), "--seconds", "1"]) == 2
    assert ".wav" in capsys.readouterr().err


def test_a_module_that_fails_to_import_exits_2(tmp_path, capsys):
    bad = tmp_path / "bad.py"
    bad.write_text("def tone(:\n")
    assert main(["lint", f"{bad}:tone", "--seconds", "1"]) == 2
    assert "SyntaxError" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["render", "lint"])
@pytest.mark.parametrize("seconds", ["0", "-1"])
def test_seconds_must_be_positive(piece, tmp_path, capsys, command, seconds):
    args = [command, f"{piece}:tone", "--seconds", seconds] + (["-o", str(tmp_path / "x.wav")] if command == "render" else [])
    assert main(args) == 2
    assert "--seconds" in capsys.readouterr().err


def test_render_prints_the_seconds_as_given(piece, tmp_path, capsys):
    out = tmp_path / "q.wav"
    assert main(["render", f"{piece}:tone", "-o", str(out), "--seconds", "0.25"]) == 0
    assert capsys.readouterr().out.startswith(f"{out}: 0.25 s,")
