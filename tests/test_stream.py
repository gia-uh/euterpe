from itertools import islice

import numpy as np

from euterpe.instruments import play
from euterpe.sound import ADSR, RATE, Sine, render
from euterpe.stream import Chunk, chunks, join


def voice(n):
    return Sine(n.freq) * ADSR(0.005, 0.05, 0.6, 0.2, gate=n.duration)


NOTES = [(i * 0.25, 220.0 * 2 ** ((i % 5) / 12), 0.2) for i in range(32)]  # 8 s


def window(k):
    """Chunk k: the notes of [2k, 2k + 2), shifted to start at 0."""
    ev = [(t - 2 * k, f, d) for t, f, d in NOTES if 2 * k <= t < 2 * k + 2]
    return play(voice, ev), 2.0


def first(n, it):
    return list(islice(it, n))


def test_chunks_start_where_the_last_ended():
    assert [c.start for c in first(4, chunks(window))] == [0.0, 2.0, 4.0, 6.0]


def test_each_chunk_carries_its_tail():
    c = next(chunks(window, tail=2.5))
    assert isinstance(c, Chunk) and len(c.samples) == round(4.5 * RATE)


def test_joined_chunks_equal_one_render_for_independent_voices():
    joined = join(first(4, chunks(window)), 8.0)
    whole = render(play(voice, NOTES), 8.0)
    np.testing.assert_allclose(joined, whole, atol=1e-6)


def test_join_cuts_at_seconds():
    assert len(join(first(4, chunks(window)), 5.0)) == 5 * RATE


def test_chunks_of_varying_length():
    lengths = [1.0, 0.5, 2.0]
    starts = [c.start for c in first(3, chunks(lambda k: (Sine(220.0) * 0.1, lengths[k]), tail=0.0))]
    assert starts == [0.0, 1.0, 1.5]
