"""The widget display(x) shows for anything that plays: the envelope with a playhead on the left,
the spectrum on the right (its average until played, then live), the browser's player below,
and above them the object's special view when it has one. Spec 2026-10-28.

Drawn by hand as SVG with text labels, so it needs no matplotlib and stays light: the script
moves the playhead and draws the live spectrum over the static drawing, which is what a page
without scripts and the printed book show."""

from __future__ import annotations

import base64
import hashlib
import html
from functools import cache
from pathlib import Path

import numpy as np

from euterpe.sound.clip import Clip
from euterpe.sound.core import Unit
from euterpe.view.base import View, sources
from euterpe.view.signal import _mono
from euterpe.view.style import INK, MADDER, PRUSSIAN, RULE, WASH

ENV_W, SPEC_W, H = 440, 200, 92  # viewBox sizes: the two drawings stand 2.2 to 1
TOP, BOTTOM, LABEL = 6, 74, 87  # envelope plot rows and the tick labels' baseline
SPEC_TOP, SPEC_H, KEYS_Y = 4, 58, 63  # spectrum plot rows and the keyboard strip
POINTS = 96  # spectrum points, log-spaced from 20 Hz to 20 kHz; widget.js uses the same grid
FFT = 4096  # the analyser's size in widget.js, so the average and the live line agree
FONT = "font-family=\"'Source Serif 4',Georgia,serif\""
BLACK = {1, 3, 6, 8, 10}


@cache
def _script() -> str:
    lines = (Path(__file__).parent / "widget.js").read_text().splitlines()
    return "\n".join(line.strip() for line in lines if line.strip())


def _num(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _step(seconds: float) -> float:
    """A tick spacing that puts at most eight labels under the envelope."""
    for s in (0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 30, 60):
        if seconds / s <= 8:
            return s
    return 60 * np.ceil(seconds / 480)


def _fx(f: float) -> float:
    return SPEC_TOP + 192 * np.log(f / 20) / np.log(1000)


def _level(db: float) -> float:
    return SPEC_TOP + SPEC_H * (1 - min(1.0, max(0.0, (db + 100) / 90)))


def average_spectrum(x: np.ndarray, rate: int) -> np.ndarray:
    """dB at the POINTS frequencies: Blackman frames of FFT samples, magnitude over FFT as the
    browser's analyser computes it, power averaged over the frames, the loudest bin within 3 %
    of each point."""
    if len(x) < FFT:
        x = np.concatenate([x, np.zeros(FFT - len(x))])
    hop = FFT // 2
    frames = np.lib.stride_tricks.sliding_window_view(x, FFT)[::hop]
    power = (np.abs(np.fft.rfft(frames * np.blackman(FFT), axis=1)) / FFT) ** 2
    db = 10 * np.log10(power.mean(axis=0) + 1e-20)
    out = np.empty(POINTS)
    for i in range(POINTS):
        k = 20 * 1000 ** (i / (POINTS - 1)) / (rate / FFT)
        lo, hi = max(1, round(k / 1.03)), min(len(db) - 1, round(k * 1.03))
        out[i] = db[lo:max(hi, lo) + 1].max()
    return out


class Widget(View):
    """What display(x) shows for a unit, a clip, a phrase or a shape, at -16 LUFS unless
    normalize is false."""

    def __init__(self, x: Unit | Clip, *, caption: str | None = None, id: str | None = None,
                 normalize: bool = True, special: tuple | None = None):
        super().__init__(caption=caption, id=id, normalize=normalize)
        self.audio = sources(x)[0]
        if special is None:
            from euterpe.view.special import special_view

            special = special_view(x.source if isinstance(x, Clip) else x, self.audio.seconds)
        self.special = special  # (svg body, width, height, x0, x1) or None

    # -- the drawings, as SVG markup in their own viewBox --------------------------------------

    def _envelope(self) -> str:
        c, g = self.audio, self.gain()[0]
        x = _mono(c) * g
        n = 200
        hop = max(1, len(x) // n)
        env = np.abs(x[: len(x) // hop * hop]).reshape(-1, hop).max(axis=1) if len(x) >= hop else np.abs(x)
        mid, half = (TOP + BOTTOM) / 2, (BOTTOM - TOP) / 2
        xs = 4 + (ENV_W - 8) * np.arange(len(env)) / max(1, len(env) - 1)
        ys = mid - np.minimum(env, 1.0) * half
        top = f"M4,{_num(mid)}" + "".join(f"L{_num(a)},{_num(b)}" for a, b in zip(xs, ys)) + f"L{ENV_W - 4},{_num(mid)}Z"
        u = self.uid
        parts = [
            f'<defs><path id="e{u}" d="{top}"/><clipPath id="p{u}" class="eu-played"><rect x="4" y="0" width="0" height="{H}"/></clipPath></defs>',
            f'<line x1="4" x2="{ENV_W - 4}" y1="{TOP}" y2="{TOP}" stroke="{RULE}" stroke-width="0.6" stroke-dasharray="2 3"/>',
            f'<line x1="4" x2="{ENV_W - 4}" y1="{BOTTOM}" y2="{BOTTOM}" stroke="{RULE}" stroke-width="0.6" stroke-dasharray="2 3"/>',
            f'<g fill="{PRUSSIAN}" fill-opacity="0.18" stroke="{PRUSSIAN}" stroke-width="0.8"><use href="#e{u}"/>'
            f'<use href="#e{u}" transform="matrix(1 0 0 -1 0 {TOP + BOTTOM})"/></g>',
            f'<g fill="{PRUSSIAN}" fill-opacity="0.22" clip-path="url(#p{u})"><use href="#e{u}"/>'
            f'<use href="#e{u}" transform="matrix(1 0 0 -1 0 {TOP + BOTTOM})"/></g>',
        ]
        step = _step(c.seconds)
        ticks = np.arange(0, c.seconds + 1e-9, step)
        decimals = 0 if step >= 1 else 1 if step >= 0.1 else 2
        for t in ticks:
            px = 4 + (ENV_W - 8) * t / c.seconds
            anchor = "start" if t == 0 else "end" if px > ENV_W - 12 else "middle"
            parts.append(f'<text x="{_num(px)}" y="{LABEL}" text-anchor="{anchor}">{t:.{decimals}f}</text>')
        if c.defaulted:
            parts.append(f'<text x="{ENV_W - 6}" y="{TOP + 10}" text-anchor="end" font-style="italic" fill="{MADDER}">'
                         f'{_num(c.seconds)} s (default)</text>')
        parts.append(f'<g class="eu-ph" transform="translate(4,0)"><line y1="0" y2="{BOTTOM}" stroke="{MADDER}" stroke-width="1.6"/>'
                     f'<path d="M-4,0H4L0,6Z" fill="{MADDER}"/><text class="eu-t" x="5" y="{TOP + 9}" font-size="9" '
                     f'fill="{MADDER}"></text></g>')
        return "".join(parts)

    def _spectrum(self) -> str:
        c, g = self.audio, self.gain()[0]
        db = average_spectrum(_mono(c) * g, c.rate)
        xs = SPEC_TOP + 192 * np.arange(POINTS) / (POINTS - 1)
        line = "".join(f"{'L' if i else 'M'}{_num(a)},{_num(_level(b))}" for i, (a, b) in enumerate(zip(xs, db)))
        base = SPEC_TOP + SPEC_H
        parts = [f'<line x1="{_num(_fx(f))}" x2="{_num(_fx(f))}" y1="{SPEC_TOP}" y2="{base}" stroke="{WASH}" stroke-width="0.6"/>'
                 for f in (100, 1000, 10000)]
        parts.append(f'<path class="eu-avg" d="{line}L196,{base}L4,{base}Z" fill="{PRUSSIAN}" fill-opacity="0.1" '
                     f'stroke="{PRUSSIAN}" stroke-width="1"/>')
        parts.append(f'<path class="eu-live" d="" fill="none" stroke="{PRUSSIAN}" stroke-width="1.1" style="display:none"/>')
        keys = "".join(f"M{_num(a)},{KEYS_Y}h{_num(b - a)}v6H{_num(a)}Z" for a, b in
                       ((_fx(440 * 2 ** ((m - 69.5) / 12)), _fx(440 * 2 ** ((m - 68.5) / 12))) for m in range(24, 121) if m % 12 in BLACK))
        parts.append(f'<rect x="4" y="{KEYS_Y}" width="192" height="6" fill="#fff" stroke="{RULE}" stroke-width="0.4"/>'
                     f'<path d="{keys}" fill="{INK}"/>')
        for f, label in ((20, "20"), (100, "100"), (1000, "1k"), (10000, "10k")):
            anchor = "start" if f == 20 else "middle"
            parts.append(f'<text x="{_num(_fx(f))}" y="{LABEL}" text-anchor="{anchor}">{label}</text>')
        parts.append(f'<g class="eu-pk" style="display:none"><circle r="2.2" fill="{MADDER}"/>'
                     f'<text font-size="9" font-style="italic" fill="{MADDER}"></text></g>')
        return "".join(parts)

    # -- the bundle --------------------------------------------------------------------------

    @property
    def uid(self) -> str:
        if not hasattr(self, "_uid"):
            h = hashlib.sha1(np.ascontiguousarray(self.audio.samples).tobytes())
            h.update(repr(self.gain()[0]).encode())
            self._uid = h.hexdigest()[:8]
        return self._uid

    def _svgs(self) -> tuple[str, str, str | None]:
        """The envelope, the spectrum and the special view, each a whole <svg>."""
        attrs = f'{FONT} font-size="9" fill="{INK}" style="width:100%;height:auto;display:block"'
        env = (f'<svg class="eu-env" viewBox="0 0 {ENV_W} {H}" data-x0="4" data-x1="{ENV_W - 4}" {attrs.replace('font-size="9"', 'font-size="10"')} '
               f'role="img" aria-label="envelope over time">{self._envelope()}</svg>')
        spec = (f'<svg class="eu-spec" viewBox="0 0 {SPEC_W} {H}" {attrs} role="img" aria-label="spectrum">'
                f'{self._spectrum()}</svg>')
        sp = None
        if self.special is not None:
            body, w, h, x0, x1 = self.special
            timing = f' data-x0="{_num(x0)}" data-x1="{_num(x1)}"' if x1 is not None else ""
            sp = f'<svg class="eu-sp" viewBox="0 0 {_num(w)} {_num(h)}"{timing} {attrs.replace('font-size="9"', 'font-size="12"')}>{body}</svg>'
        return env, spec, sp

    def svg(self) -> bytes:
        """The static widget for print: the special view over the envelope and the spectrum."""
        if self._svg is None:
            width = ENV_W + 10 + SPEC_W
            y, inner = 0.0, []
            if self.special is not None:
                body, w, h, _, _ = self.special
                sh = width * h / w
                inner.append(f'<svg x="0" y="0" width="{width}" height="{_num(sh)}" viewBox="0 0 {_num(w)} {_num(h)}">{body}</svg>')
                y = sh + 6
            inner.append(f'<svg x="0" y="{_num(y)}" width="{ENV_W}" height="{H}" viewBox="0 0 {ENV_W} {H}">{self._envelope()}</svg>')
            inner.append(f'<svg x="{ENV_W + 10}" y="{_num(y)}" width="{SPEC_W}" height="{H}" viewBox="0 0 {SPEC_W} {H}">'
                         f'{self._spectrum()}</svg>')
            total = y + H
            self._svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {_num(total)}" '
                         f'width="{width}" height="{_num(total)}" {FONT} font-size="9" fill="{INK}">'
                         f'{"".join(inner)}</svg>').encode()
        return self._svg

    def level_line(self) -> str:
        g, lufs = self.gain()
        if not np.isfinite(lufs):
            return "silent"
        if not self.normalize:
            return f"rendered level · {lufs:.1f} LUFS"
        d = 20 * np.log10(g)
        sign = "+" if d >= 0 else "−"
        return f"rendered {lufs:.1f} LUFS · plays {lufs + d:.1f} LUFS ({sign}{abs(d):.1f} dB)".replace("-", "−")

    def html(self, mp3: bytes) -> str:
        env, spec, sp = self._svgs()
        src = "data:audio/mpeg;base64," + base64.b64encode(mp3).decode()
        cap = f'<figcaption style="font-style:italic;font-size:.9em;margin-top:4px">{html.escape(self.caption)}</figcaption>' if self.caption else ""
        return "".join([
            f'<figure class="euterpe-widget" data-dur="{self.audio.seconds:.4f}" style="margin:1em 0;padding:10px 12px;'
            f"background:#fff;color:{INK};border:1px solid {WASH};border-radius:6px;font-family:'Source Serif 4',Georgia,serif\">",
            '<style>@media (max-width:640px){.euterpe-widget .eu-grid{grid-template-columns:1fr!important}.euterpe-widget .eu-spec{max-width:65%;margin:0 auto}}</style>',
            f'<div style="margin-bottom:6px">{sp}</div>' if sp else "",
            f'<div class="eu-grid" style="display:grid;grid-template-columns:2.2fr 1fr;gap:10px">{env}{spec}</div>',
            '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:6px">',
            f'<audio controls preload="metadata" src="{src}" style="flex:1 1 240px;min-width:0;height:34px"></audio>',
            f'<span style="font:11px ui-monospace,monospace;color:#6b7078">{html.escape(self.level_line())}</span></div>',
            cap,
            f"<script>\n{_script()}\n</script></figure>",
        ])

    def _repr_mimebundle_(self, include=None, exclude=None):
        mp3 = self.mp3()
        data = {
            "text/html": self.html(mp3),
            "image/svg+xml": self.svg().decode(),
            "audio/mpeg": base64.b64encode(mp3).decode(),
            "text/plain": repr(self),
        }
        meta = {k: v for k, v in (("caption", self.caption), ("id", self.id)) if v}
        meta["site"] = "html"
        return data, meta


def widget(x: Unit | Clip, **kw) -> Widget:
    return Widget(x, **kw)
