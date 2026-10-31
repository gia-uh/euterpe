import json
import sys

import numpy as np
import pytest

from euterpe import Score
from euterpe.cli import main
from euterpe.io import read, write
from tests.helpers import peak_hz

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
    other = tmp_path / "t.wav"
    assert main(["render", f"{piece}:seeded", "-o", str(other), "--seconds", "1", "--seed", "2"]) == 0
    assert peak_hz(read(other)[0]) == pytest.approx(660.0, abs=1.0)    # seeded(2) is 220 * 3 Hz


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


SCORE = '''
from euterpe import Key, Meter, Score, chords, melody
from euterpe.instruments import Harp


def score():
    s = Score(key=Key("D major"), meter=Meter("3/4"), tempo=240)
    s.part("melody", Harp()).add(melody("f#4:q a4 d5"))
    s.part("chords", Harp()).add(chords("I:h.", voicing="close"))
    return s
'''

PARALLEL = '''
from euterpe import Key, Score, melody


def score():
    s = Score(key=Key("C major"))
    s.part("soprano").add(melody("g4:h a4"))
    s.part("alto").add(melody("e4:h f4"))
    s.part("tenor").add(melody("c4:h d4"))
    s.part("bass").add(melody("c3:h d3"))
    return s
'''


@pytest.fixture
def written(tmp_path):
    path = tmp_path / "written.py"
    path.write_text(SCORE)
    return path


def _file(tmp_path, text):
    path = tmp_path / "other.py"
    path.write_text(text)
    return path


def test_render_a_piece_lasts_its_duration(written, tmp_path, capsys):
    out = tmp_path / "piece.wav"
    assert main(["render", str(written), "-o", str(out), "--seed", "7"]) == 0
    assert len(read(out)[0]) > 48_000 * 0.75    # three beats at 240 bpm, and the tails
    assert capsys.readouterr().out.startswith(f"{out}: ")


def test_a_piece_with_seconds_lasts_those_seconds(written, tmp_path):
    out = tmp_path / "piece.wav"
    assert main(["render", str(written), "-o", str(out), "--seconds", "0.5"]) == 0
    assert len(read(out)[0]) == 24_000


@pytest.mark.parametrize("suffix, start", [(".mid", b"MThd"), (".midi", b"MThd"), (".musicxml", b"<?xml"), (".MID", b"MThd")])
def test_render_a_piece_to_notation_writes_no_audio(tmp_path, capsys, suffix, start):
    path = _file(tmp_path, PARALLEL)    # no part has an instrument, so playing it would raise
    out = tmp_path / "sub" / f"piece{suffix}"
    assert main(["render", str(path), "-o", str(out)]) == 0
    assert out.read_bytes().startswith(start)
    assert capsys.readouterr().out == f"{out}: bars 1 to 1\n"


@pytest.mark.parametrize("suffix", [".mid", ".musicxml"])
@pytest.mark.parametrize("flags", [["--seconds", "-3"], ["--seconds", "2"], ["--rate", "8000"]])
def test_notation_takes_no_audio_flags(written, tmp_path, capsys, suffix, flags):
    out = tmp_path / f"x{suffix}"
    assert main(["render", str(written), "-o", str(out), *flags]) == 2
    assert flags[0] in capsys.readouterr().err and not out.exists()


def test_notation_takes_the_default_rate(written, tmp_path):
    assert main(["render", str(written), "-o", str(tmp_path / "x.mid"), "--rate", "48000"]) == 0


@pytest.mark.parametrize("suffix", [".mid", ".musicxml"])
def test_a_function_target_cannot_write_notation(piece, tmp_path, capsys, suffix):
    out = tmp_path / f"x{suffix}"
    assert main(["render", f"{piece}:tone", "-o", str(out), "--seconds", "1"]) == 2
    assert "score()" in capsys.readouterr().err and not out.exists()


def test_a_function_target_still_needs_seconds_to_render(piece, tmp_path, capsys):
    assert main(["render", f"{piece}:tone", "-o", str(tmp_path / "x.wav")]) == 2
    assert "--seconds" in capsys.readouterr().err


@pytest.mark.parametrize("seconds", ["0", "-1"])
def test_a_piece_checks_its_seconds_too(written, tmp_path, capsys, seconds):
    assert main(["render", str(written), "-o", str(tmp_path / "x.wav"), "--seconds", seconds]) == 2
    assert "--seconds" in capsys.readouterr().err


def test_a_piece_that_cannot_play_exits_2(tmp_path, capsys):
    path = _file(tmp_path, PARALLEL)
    assert main(["render", str(path), "-o", str(tmp_path / "x.wav")]) == 2
    assert "no instrument" in capsys.readouterr().err


def test_a_piece_with_nothing_written_exits_2(tmp_path, capsys):
    path = _file(tmp_path, "from euterpe import Score\nfrom euterpe.instruments import Harp\n\n\n"
                           "def score():\n    s = Score()\n    s.part('a', Harp())\n    return s\n")
    assert main(["render", str(path), "-o", str(tmp_path / "x.wav")]) == 2
    assert "nothing written" in capsys.readouterr().err
    assert main(["inspect", str(path), "-o", str(tmp_path / "d")]) == 2
    assert "nothing written" in capsys.readouterr().err


def test_lint_a_piece_under_a_profile_as_json(tmp_path, capsys):
    path = _file(tmp_path, PARALLEL)
    assert main(["lint", str(path), "--profile", "chorale", "--no-audio", "--json"]) == 1
    findings = json.loads(capsys.readouterr().out)["findings"]
    errors = [f for f in findings if f["severity"] == "error"]
    assert errors and errors[0]["rule"] == "V-PARALLEL" and "chorale" in errors[0]["message"]
    assert not any(f["rule"].startswith("A-") for f in findings)


def test_lint_a_piece_exits_0_without_an_error_and_reads_its_audio(written, capsys):
    assert main(["lint", str(written)]) == 0
    assert "A-PEAK" in capsys.readouterr().out


def test_the_profile_is_a_usage_error_when_unknown(written, capsys):
    with pytest.raises(SystemExit) as e:
        main(["lint", str(written), "--profile", "nope"])
    assert e.value.code == 2
    assert "chorale" in capsys.readouterr().err


@pytest.mark.parametrize("args", [["--profile", "pop"], ["--no-audio"]])
def test_only_a_piece_takes_the_score_flags(tmp_path, capsys, args):
    path = write(np.zeros(4_800, np.float32), tmp_path / "a.wav")
    assert main(["lint", str(path), *args]) == 2
    assert "not a piece" in capsys.readouterr().err


@pytest.mark.parametrize("args", [["--seconds", "1"], ["--loop"]])
def test_a_piece_takes_no_audio_length_flags(written, capsys, args):
    assert main(["lint", str(written), *args]) == 2
    assert "takes no" in capsys.readouterr().err


@pytest.mark.parametrize("command", [["render", "{p}", "-o", "{d}/x.wav"], ["lint", "{p}"], ["inspect", "{p}", "-o", "{d}/o"]])
def test_a_generator_score_waits_for_milestone_5(tmp_path, capsys, command):
    path = _file(tmp_path, "def score():\n    yield 1\n")
    assert main([a.format(p=path, d=tmp_path) for a in command]) == 2
    assert "generator scores come with milestone 5" in capsys.readouterr().err


def test_a_file_with_no_score_names_the_piece_form(piece, tmp_path, capsys):
    assert main(["render", str(piece), "-o", str(tmp_path / "x.wav")]) == 2
    err = capsys.readouterr().err
    assert "no function score" in err and "tone" in err and "a piece is path.py with a score() function" in err


def test_a_score_that_is_not_a_score_exits_2(tmp_path, capsys):
    path = _file(tmp_path, "def score():\n    return 3\n")
    assert main(["lint", str(path)]) == 2
    assert "int, not a Score" in capsys.readouterr().err


def test_a_score_that_raises_exits_2_with_its_message(tmp_path, capsys):
    path = _file(tmp_path, "from euterpe import melody\n\n\ndef score():\n    return melody('nonsense!!')\n")
    assert main(["lint", str(path)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("euterpe: ") and "ValueError" in err


SEEDED = '''
from euterpe import Score, melody
from euterpe.instruments import Harp


def score(seed):
    s = Score(tempo=240)
    s.part(f"seed{seed}", Harp()).add(melody("c4:q"))
    return s
'''


def test_score_seed_receives_seed_and_the_same_seed_reaches_the_performance(tmp_path, monkeypatch, capsys):
    path = _file(tmp_path, SEEDED)
    assert main(["render", str(path), "-o", str(tmp_path / "x.musicxml"), "--seed", "1"]) == 0
    assert b"seed1" in (tmp_path / "x.musicxml").read_bytes()
    seeds = []
    real = Score.play
    monkeypatch.setattr(Score, "play", lambda self, seed=0, performance=None: seeds.append(seed) or real(self, seed, performance))
    assert main(["render", str(path), "-o", str(tmp_path / "x.wav"), "--seed", "4"]) == 0
    assert seeds == [4]
    assert main(["render", str(path), "-o", str(tmp_path / "y.mid")]) == 2
    assert "--seed" in capsys.readouterr().err


@pytest.fixture
def played(monkeypatch):
    """The seeds Score.play is called with."""
    seeds = []
    real = Score.play
    monkeypatch.setattr(Score, "play", lambda self, seed=0, performance=None: seeds.append(seed) or real(self, seed, performance))
    return seeds


def test_lint_passes_the_seed_to_the_performance(written, played):
    assert main(["lint", str(written), "--seed", "5"]) == 0
    assert played == [5]


def test_inspect_passes_the_seed_to_the_performance(written, tmp_path, monkeypatch, played):
    monkeypatch.setattr("euterpe.inspect._png", lambda view, path: path)
    assert main(["inspect", str(written), "-o", str(tmp_path / "o"), "--seed", "6"]) == 0
    assert played == [6]


def test_inspect_prints_each_file_and_summary_last(written, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("euterpe.inspect._png", lambda view, path: path)
    out = tmp_path / "look"
    assert main(["inspect", str(written), "-o", str(out), "--seed", "2"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1] == str(out / "summary.txt")
    assert lines[:2] == [str(out / "roll-melody.png"), str(out / "roll-chords.png")]
    assert "key: " in (out / "summary.txt").read_text()


def test_inspect_requires_a_directory(written, capsys):
    with pytest.raises(SystemExit) as e:
        main(["inspect", str(written)])
    assert e.value.code == 2


def test_inspect_cannot_write_over_a_file(written, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("euterpe.inspect._png", lambda view, path: path)
    taken = tmp_path / "taken"
    taken.write_text("")
    assert main(["inspect", str(written), "-o", str(taken)]) == 2
    assert capsys.readouterr().err.startswith("euterpe: ")


def test_inspect_without_matplotlib_says_what_to_install(written, tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    assert main(["inspect", str(written), "-o", str(tmp_path / "o")]) == 2
    assert "pip install 'euterpe[view]'" in capsys.readouterr().err
