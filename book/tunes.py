"""The tunes the book plays, transcribed from public-domain scores: each is a list of
(beat, pitch, beats). notes() turns one into Notes at a tempo. The book's freeze cache keys on
each chapter's text, not on this file: after changing a tune, clear the cache."""

from euterpe.instruments import Note
from euterpe.pitch import (A2, A3, A4, A5, B2, B3, B4, B5, C5, C6, Cs3, Cs4, Cs5, D2, D3, D4, D5, Ds4, Ds5,
                           E2, E3, E4, E5, F4, Fs2, Fs3, Fs4, Fs5, G2, G3, G4, G5, Gs3, Gs4, Gs5)

s = 1 / 6  # a sixth of a beat
TUNES = {
    "air": [(0, Fs5, 4.5), (4.5, B5, .25), (4.75, G5, .25), (5, E5, .25), (5.25, D5, .25), (5.5, Cs5, .25),
            (5.75, D5, .25), (6, Cs5, .5), (6.5, A4, .5), (7, A5, 1.5), (8.5, Fs5, .25), (8.75, C5, .25),
            (9, B4, .25), (9.25, E5, .25), (9.5, Ds5, .25), (9.75, A5, .25), (10, G5, 1), (11, E5, 1),
            (12, Fs5, .5), (12.5, E5, .5), (13, D5, .5), (13.5, Cs5, .5), (14, D5, 2)],
    "air inner": [(b, p, 2) for b, ps in ((0, (A3, D4)), (2, (B3, D4)), (4, (B3, D4)), (6, (A3, E4)),
                                          (8, (A3, D4)), (10, (G3, E4))) for p in ps]
                 + [(12, B3, 1), (12, D4, 1), (13, A3, 1), (13, Cs4, 1), (14, A3, 2), (14, D4, 2)],
    "air bass": [(i * .5, p, .5) for i, p in enumerate([D3, D4, Cs3, Cs4, B2, B3, A2, A3, G2, G3, Fs2, Fs3, E2, E3,
                                                       A2, A3, Fs2, Fs3, B2, B3, E2, E3, E2, E3, G2, G3, A2, A3])]
                + [(14, D2, 2)],
    "morning": [(0, Gs5, 2), (2, E5, 1), (3, Ds5, 2), (5, Cs5, 1), (6, Ds5, 2), (7, E5, 1),
                                          (8, Gs5, 2), (10, E5, 1), (12, Ds5, 2), (14, Cs5, 1), (15, Ds5, 1),
                                          (16, E5, 1), (17, Ds5, 1), (18, E5, 2), (20, Gs5, 1), (21, E5, 2),
                                          (23, Gs5, 1), (24, A5, 2), (26, E5, 1), (27, A5, 2), (29, Gs5, 1),
                                          (30, E5, 2), (32, Ds5, 1), (33, Cs5, 3)],
    "adagio": [(0, A4, 2), (2, Fs4, .5), (2.5, G4, .5), (3, A4, 1.5), (4.5, B4, .5), (5, Cs5, .5), (5.5, D5, .5),
               (6, D5, 2), (8, Cs5, .5), (8.5, B4, .5), (9, A4, 1), (10, G4, .5), (10.5, Fs4, .5), (11, E4, 1),
               (12, D4, 3)],
    "adagio chords": [(b, p, 3) for b, ps in ((0, (D3, A3)), (3, (Fs3, A3)), (6, (G3, B3)), (9, (G3, Cs4)),
                                              (12, (Fs3, D4))) for p in ps],
    "tell": [(b, p, .2) for b, p in [(0, B3), (.25, B3), (.5, B3), (1, B3), (1.25, B3), (1.5, B3), (2, B3), (2.25, B3),
                                      (2.5, E4), (3, Fs4), (3.5, Gs4), (4, B3), (4.25, B3), (4.5, B3), (5, B3),
                                      (5.25, B3), (5.5, E4), (6, Gs4), (6.5, Fs4), (7, Ds4), (7.5, B3)]],
    "tell end": [(b, p, d) for b, p, d in [(0, B3, .2), (.25, B3, .2), (.5, B3, .2), (1, B3, .2), (1.25, B3, .2),
                                            (1.5, B3, .2), (2, B3, .2), (2.25, B3, .2), (2.5, E4, .4), (3, Fs4, .4),
                                            (3.5, Gs4, .4), (4, Gs4, .4), (4.5, Fs4, .4), (5, E4, .9)]],
    "tell bass": [(b, (E2, B2)[b % 2], .6) for b in range(22)],  # the low players on E and B, a beat each
    "bolero": [(0, C5, 2), (2, B4, s), (2 + s, C5, s), (2 + 2 * s, D5, s), (2.5, C5, s), (2 + 4 * s, B4, s),
               (2 + 5 * s, A4, s), (3, C5, .5), (3.5, C5, .25), (3.75, A4, .25), (4, C5, 1), (5, B4, .25),
               (5.25, C5, .25), (5.5, A4, .25), (5.75, G4, .25), (6, E4, .25), (6.25, F4, .25), (6.5, G4, .5),
               (7, A4, 2), (9, G4, .5), (9.5, A4, .25), (9.75, B4, .25), (10, D5, .5), (10.5, C5, .25),
               (10.75, B4, .25), (11, C5, 1)],
}


def notes(tune, at, beat, up=0, velocity=0.7):
    """The tune's notes from at seconds, beat seconds a beat, up semitones higher."""
    return [Note(at + b * beat, p + up, d * beat, velocity) for b, p, d in TUNES[tune]]
