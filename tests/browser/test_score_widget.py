"""The score widget in a real browser: dev only, and skipped without Playwright or a browser to launch."""

import sys

import pytest

from euterpe import Key, Score, melody
from euterpe.instruments import Harp

sync_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture
def opened(tmp_path):
    """A function that opens a view as a built page at a viewport's size, and gives back the page."""
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        except sync_api.Error as e:
            pytest.skip(f"no browser to launch: {e}")

        def open_view(view, height=900, width=1440):
            built = tmp_path / "page.html"
            built.write_text(f"<!doctype html><meta charset=utf-8><body style='height:3000px;max-width:576px;margin:auto'>{view.html(view.mp3())}</body>")
            page = browser.new_page(viewport={"width": width, "height": height})
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
    s.part("melody", Harp()).add(melody(" | ".join(["c4:q d e f"] * 30)))
    page = opened(s.view(), height=200)
    page.evaluate("(a => { a = document.querySelector('audio'); a.play(); a.currentTime = a.duration * 0.6; })()")
    page.wait_for_function("document.querySelector('.eu-score').scrollTop > 0", timeout=2000)
    assert page.evaluate("window.scrollY") == 0


def test_a_phone_scrolls_down_to_the_next_system_in_plain_playback(opened):
    s = Score(tempo=1200)
    s.part("melody", Harp()).add(melody(" | ".join(["c4:q d e f"] * 12)))
    page = opened(s.view(), height=160, width=390)
    page.evaluate(PLAY)
    page.wait_for_function("document.querySelector('.eu-score').scrollTop > 0", timeout=3500)
    page.evaluate("document.querySelector('audio').pause()")
    page.wait_for_timeout(600)
    inside = """() => {
      const p = document.querySelector('.eu-score').getBoundingClientRect(), c = document.querySelector('.eu-cursor').getBoundingClientRect();
      return c.left >= p.left && c.right <= p.right && c.top < p.bottom && c.bottom > p.top;
    }"""
    assert page.evaluate(inside)


def test_every_notehead_can_be_clicked(opened):
    s = Score(key=Key("G major"), tempo=132)  # as chapter 16 opens: a high first note, under the tempo mark
    s.part("violin", Harp()).add(melody("g5:q r:e d5 g5:q r:e d5"))
    page = opened(s.view())
    missed = page.evaluate("""() => {
      const ids = new Set(JSON.parse(document.querySelector('.eu-map').textContent).flatMap(e => e[1]));
      return [...document.querySelectorAll('.eu-score g.note .notehead')].filter(head => {
        head.scrollIntoView({ block: 'center' });
        const r = head.getBoundingClientRect();
        for (let e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); e; e = e.parentNode) if (ids.has(e.id)) return false;
        return true;
      }).length;
    }""")
    assert missed == 0
    # The fallback font here differs from the book's, whose tempo mark covers this head: no text may take a click at all.
    assert page.evaluate("getComputedStyle(document.querySelector('.eu-score text')).pointerEvents") == "none"


def test_a_click_on_the_first_note_while_paused_lights_it(opened):
    page = opened(_bars().view())
    page.evaluate("document.querySelector('audio').currentTime = 1.2")
    page.wait_for_function(f"{LIT} >= 1", timeout=2000)
    page.click(".eu-score g.note .notehead >> nth=0", force=True)
    page.wait_for_function("document.querySelector('audio').currentTime === 0", timeout=2000)
    page.wait_for_timeout(200)
    assert page.evaluate(LIT) == 1
    assert page.evaluate("document.querySelector('.eu-cursor').style.display") == ""
