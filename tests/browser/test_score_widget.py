"""The score widget in a real browser: dev only, and skipped without Playwright or a browser to launch."""

import sys

import pytest

from euterpe import Score, melody
from euterpe.instruments import Harp

sync_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture
def opened(tmp_path):
    """A function that opens a view as a built page at a viewport's height, and gives back the page."""
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        except sync_api.Error as e:
            pytest.skip(f"no browser to launch: {e}")

        def open_view(view, height=900):
            built = tmp_path / "page.html"
            built.write_text(f"<!doctype html><meta charset=utf-8><body style='height:3000px'>{view.html(view.mp3())}</body>")
            page = browser.new_page(viewport={"width": 1440, "height": height})
            page.goto(built.as_uri())
            page.wait_for_function("document.querySelector('audio').readyState >= 1", timeout=2000)
            return page

        yield open_view
        browser.close()


def _bars() -> Score:
    s = Score(tempo=120)
    s.part("melody", Harp()).add(melody("c4:q d e f | g:q a b c5"))
    return s


CURSOR_X = "+document.querySelector('.eu-cursor').getAttribute('x1')"
LIT = "document.querySelectorAll('.eu-on').length"
PLAY = "document.querySelector('audio').play()"


def _walks(page):
    assert page.evaluate("document.querySelector('.eu-cursor')") is None
    page.evaluate(PLAY)
    page.wait_for_function("document.querySelector('.eu-cursor') !== null", timeout=2000)
    start = page.evaluate(CURSOR_X)
    page.wait_for_timeout(1000)
    assert page.evaluate(LIT) >= 1
    assert page.evaluate(CURSOR_X) > start


def test_playing_lights_notes_and_moves_the_cursor(opened):
    _walks(opened(_bars().view()))


def test_the_roll_does_the_same_without_verovio(opened, monkeypatch):
    s = _bars()
    monkeypatch.setitem(sys.modules, "verovio", None)
    _walks(opened(s.view()))


def test_a_click_on_a_note_seeks_there_and_starts_nothing(opened):
    page = opened(_bars().view())
    page.click(".eu-score g.note .notehead >> nth=2", force=True)
    page.wait_for_function("document.querySelector('audio').currentTime > 0.9", timeout=2000)
    page.wait_for_function(f"{LIT} >= 1", timeout=2000)
    assert page.evaluate("document.querySelector('audio').paused")


def test_the_end_clears_the_highlight_and_hides_the_cursor(opened):
    page = opened(_bars().view())
    page.evaluate("(a => { a = document.querySelector('audio'); a.play(); a.currentTime = a.duration - 0.3; })()")
    page.wait_for_function("document.querySelector('audio').ended", timeout=3000)
    assert page.evaluate(LIT) == 0
    assert page.evaluate("document.querySelector('.eu-cursor').style.display") == "none"


def test_the_panel_scrolls_to_the_system_that_plays_and_the_page_does_not_move(opened):
    s = Score(tempo=1200)
    s.part("melody", Harp()).add(melody(" | ".join(["c4:q d e f"] * 60)))
    page = opened(s.view(), height=300)
    page.evaluate("(a => { a = document.querySelector('audio'); a.play(); a.currentTime = a.duration * 0.6; })()")
    page.wait_for_function("document.querySelector('.eu-score').scrollTop > 0", timeout=2000)
    assert page.evaluate("window.scrollY") == 0
