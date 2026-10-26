import re

from euterpe.book import listen
from euterpe.sound import Saw, Sine

AUDIO_LINE = re.compile(r"^!\[A tone\]\(build/audio/a-tone-[0-9a-f]{8}\.mp3\)\n$")


def test_listen_takes_a_caption_and_names_the_file_after_it(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    listen(Sine(440.0), 0.1, "A tone")
    out = capsys.readouterr().out
    assert AUDIO_LINE.match(out)
    assert (tmp_path / out[out.index("(") + 1:out.index(")")]).is_file()


def test_the_same_caption_on_different_sounds_gives_different_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    listen(Sine(440.0), 0.1, "A tone")
    listen(Saw(440.0), 0.1, "A tone")
    first, second = capsys.readouterr().out.splitlines()
    assert first != second


def test_listen_with_an_id_adds_the_reference_target(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    listen(Sine(440.0), 0.1, "A tone", id="tone")
    assert capsys.readouterr().out.rstrip().endswith("{#aud-tone}")


def test_show_takes_a_caption_and_saves_an_svg(tmp_path, monkeypatch, capsys):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from euterpe.book import show

    monkeypatch.chdir(tmp_path)
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    show(fig, "A line")
    out = capsys.readouterr().out
    assert re.match(r"^!\[A line\]\(build/img/a-line-[0-9a-f]{8}\.svg\)\n$", out)
    assert (tmp_path / out[out.index("(") + 1:out.index(")")]).read_text().lstrip().startswith("<?xml")


def test_gain_db_measures_a_filter_and_never_prints_minus_zero():
    from euterpe.book import gain_db
    from euterpe.sound import Biquad, Gain

    assert gain_db(lambda s: Biquad(s, "lowpass", cutoff=1_000.0), 1_000.0) == -3.0
    assert gain_db(lambda s: Gain(s, 0.5), 300.0) == -6.0
    assert str(gain_db(lambda s: Biquad(s, "lowpass", cutoff=1_000.0), 50.0)) == "0.0"
