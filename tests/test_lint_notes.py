from euterpe.cli import main
from euterpe.lint import lint_notes
from euterpe.pitch import A4, B7, C4, D6, E4, G4
from tests.helpers import Theremin


def test_playable():
    r = lint_notes(Theremin().play([(0.0, A4, 0.5), (1.5, B7, 0.5)]))
    [f] = [f for f in r.findings if f.rule == "R-PLAYABLE"]
    assert f.severity == "error" and f.at == 1.5 and "B7" in f.message


def test_comfort_share():
    r = lint_notes(Theremin().play([(0.0, A4, 1.0), (1.0, D6, 1.0)]))
    assert r.value("R-COMFORT") == 0.5 and any(f.severity == "warn" and f.rule == "R-COMFORT" for f in r.findings)


def test_polyphony():
    r = lint_notes(Theremin().play([(0.0, C4, 1.0), (0.0, E4, 1.0), (0.0, G4, 1.0)]))
    [f] = [f for f in r.findings if f.rule == "R-POLYPHONY"]
    assert f.value == 3 and f.at == 0.0


def test_cli_lints_a_phrase(tmp_path, capsys):
    src = tmp_path / "piece.py"
    src.write_text("from tests.helpers import Theremin\nfrom euterpe.pitch import B7\n"
                   "def piece():\n    return Theremin().play([(0.0, B7, 0.5)])\n")
    assert main(["lint", f"{src}:piece", "--seconds", "1"]) == 1
    assert "R-PLAYABLE" in capsys.readouterr().out
