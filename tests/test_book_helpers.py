from euterpe.book import listen
from euterpe.sound import Sine


def test_listen_renders_and_prints_the_audio_line(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    listen(Sine(440.0), 0.1, "a", "A tone", id="tone")
    assert capsys.readouterr().out == "![A tone](build/audio/a.mp3){#aud-tone}\n"
    assert (tmp_path / "build/audio/a.mp3").is_file()


def test_listen_without_id_has_no_attribute_block(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    listen(Sine(440.0), 0.1, "b", "Another tone")
    assert capsys.readouterr().out == "![Another tone](build/audio/b.mp3)\n"


def test_show_saves_an_svg_and_prints_the_image_line(tmp_path, monkeypatch, capsys):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from euterpe.book import show

    monkeypatch.chdir(tmp_path)
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    show(fig, "line", "A line")
    assert capsys.readouterr().out == "![A line](build/img/line.svg)\n"
    assert (tmp_path / "build/img/line.svg").read_text().lstrip().startswith("<?xml")
