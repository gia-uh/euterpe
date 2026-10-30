import numpy as np
import pytest

from euterpe import Humanize, Performance, Score, Swing, drums, melody
from euterpe.instruments import ClassicChip, ElectricPiano, Harp, Kit, Note, Pad, Violin
from euterpe.pitch import C4, D4, E3, F3
from euterpe.score import ScoreAudio, part_seeds
from euterpe.sound import render
from euterpe.sound.core import MAX_DEFAULT, RATE, Unit
from euterpe.view import listen

SHORT = "c4:e d4 e4 f4"


def _score(instrument, text=SHORT, tempo=240, **performance) -> Score:
    s = Score(tempo=tempo, performance=Performance(**performance))
    s.part("a", instrument).add(melody(text))
    return s


def test_play_gives_a_unit_with_one_phrase_per_part():
    s = Score(tempo=240)
    s.part("a", Harp()).add(melody(SHORT))
    s.part("b", Harp()).add(melody("c3:h"))
    audio = s.play()
    assert isinstance(audio, ScoreAudio) and isinstance(audio, Unit)
    assert list(audio.parts) == ["a", "b"]
    assert audio.parts["a"].instrument is s.parts["a"].instrument
    assert audio.inputs() == list(audio.parts.values())


@pytest.mark.parametrize("make", [lambda: Harp(seed=3), lambda: Violin(seed=3), lambda: ClassicChip(seed=3).pulse1],
                         ids=["Harp", "Violin", "chip channel"])
@pytest.mark.parametrize("performance", [{}, {"swing": Swing(), "humanize": Humanize()}], ids=["plain", "humanized"])
def test_one_part_plays_the_samples_of_its_notes_played_directly(make, performance):
    s = _score(make(), **performance)
    direct = make().play(s.performance.notes(s, seed=5)["a"], seed=part_seeds(5, 1)[0][1])
    played = render(s.play(seed=5), 0.3)
    assert np.abs(played).max() > 0.01
    assert np.array_equal(played, render(direct, 0.3))


def test_a_kit_part_plays_the_samples_of_its_notes_played_directly():
    s = Score(tempo=240)
    s.part("drums", Kit()).add(drums({"kick": "x...", "snare": "..x.", "hihat": "xxxx"}))
    direct = Kit().play(s.performance.notes(s)["drums"], seed=part_seeds(0, 1)[0][1])
    played = render(s.play(), 0.2)
    assert np.abs(played).max() > 0.01
    assert np.array_equal(played, render(direct, 0.2))


def test_the_samples_do_not_depend_on_the_block_size():
    s = Score(tempo=240)
    s.part("a", Harp(seed=3)).add(melody(SHORT))
    s.part("b", Violin(seed=3)).add(melody("c5:e e5 g5 c6"))
    audio = s.play()
    assert np.array_equal(render(audio, 0.02, block=1), render(audio, 0.02, block=1024))


def test_the_same_seed_gives_the_same_samples_and_another_another():
    make = lambda: _score(Harp(seed=3), humanize=Humanize())  # noqa: E731
    assert np.array_equal(render(make().play(seed=1), 0.2), render(make().play(seed=1), 0.2))
    assert not np.array_equal(render(make().play(seed=1), 0.2), render(make().play(seed=2), 0.2))


def test_the_score_performance_plays_unless_another_is_given():
    swung = Performance(swing=Swing(ratio=0.75))
    assert _score(Harp()).play().notes != _score(Harp(), swing=Swing(ratio=0.75)).play().notes
    assert (_score(Harp()).play(performance=swung).notes[1].time
            == _score(Harp(), swing=Swing(ratio=0.75)).play().notes[1].time)


def test_adding_a_part_at_the_end_changes_no_earlier_part():
    def make() -> Score:
        s = Score(tempo=240, performance=Performance(humanize=Humanize()))
        s.part("a", Harp(seed=3)).add(melody(SHORT))
        return s

    alone = make()
    with_more = make()
    with_more.part("b", Harp(seed=3)).add(melody("c3:h"))
    assert np.array_equal(render(alone.play().parts["a"], 0.2), render(with_more.play().parts["a"], 0.2))


def test_a_stereo_part_makes_the_score_stereo_and_a_mono_part_takes_both_channels_equally():
    s = Score(tempo=240)
    s.part("mono", Harp(seed=3)).add(melody(SHORT))
    s.part("wide", Pad(seed=3)).add(melody("c3:h"))
    audio = s.play()
    assert audio.parts["mono"].channels == 1 and audio.parts["wide"].channels == 2
    assert audio.channels == 2
    x = render(audio, 0.1)
    assert x.shape == (round(0.1 * RATE), 2)
    mono, wide = render(audio.parts["mono"], 0.1), render(audio.parts["wide"], 0.1)
    assert np.abs(mono).max() > 0.01
    assert np.abs(wide[:, 0] - wide[:, 1]).max() > 0.001  # a stereo part keeps its two sides
    assert np.array_equal(x, mono[:, None] + wide)


def test_mono_parts_stay_mono():
    s = Score(tempo=240)
    s.part("a", Harp()).add(melody(SHORT))
    s.part("b", Harp()).add(melody("c3:h"))
    assert s.play().channels == 1
    assert render(s.play(), 0.01).ndim == 1


def test_a_part_gain_scales_that_part_by_its_factor():
    def make(gain: float) -> Score:
        s = Score(tempo=240)
        s.part("a", Harp(seed=3), gain=gain).add(melody(SHORT))
        s.part("b", Harp(seed=4)).add(melody("c3:h"))
        return s

    full, half = make(1.0).play(), make(0.5).play()
    a, b = render(full.parts["a"], 0.2), render(full.parts["b"], 0.2)
    assert np.abs(a).max() > 0.01
    assert np.array_equal(render(half, 0.2), np.float32(0.5) * a + b)


def test_duration_is_the_longest_phrases_with_its_tail():
    s = Score(tempo=240)
    s.part("short", Harp()).add(melody("c4:e"))
    s.part("long", Harp()).add(melody(SHORT))
    audio = s.play()
    assert audio.duration == max(phrase.duration for phrase in audio.parts.values())
    assert audio.duration == audio.parts["long"].duration
    assert audio.duration > 4 * 0.125  # the tail rings past the written notes


def test_a_score_with_no_parts_does_not_play():
    with pytest.raises(ValueError, match="no parts"):
        Score().play()


def test_a_part_with_no_instrument_does_not_play_and_the_error_names_it():
    s = Score()
    s.part("right hand").add(melody(SHORT))
    with pytest.raises(ValueError, match="'right hand'.*no instrument"):
        s.play()


def test_a_part_with_no_notes_plays_silence():
    s = Score(tempo=240)
    s.part("empty", Harp())
    alone = s.play()
    assert alone.duration == 0.0 and alone.notes == []
    assert not render(alone, 0.05).any()
    assert len(alone.take()) == 0
    s.part("a", Harp(seed=3)).add(melody(SHORT))
    audio = s.play()
    assert audio.duration == audio.parts["a"].duration
    assert np.array_equal(render(audio, 0.1), render(audio.parts["a"], 0.1))


def _hands(piano, right: bool = True, left: bool = True) -> Score:
    s = Score(tempo=240)
    written = s.part("right", piano)
    if right:
        written.add(melody("c5:e e5 g5 c6"))
    written = s.part("left", piano)
    if left:
        written.add(melody("c3:q g3"))
    return s


def test_two_parts_on_one_instrument_render_the_same_twice_in_a_row():
    s = _hands(ElectricPiano(seed=3))
    audio = s.play()
    first = render(audio, 0.2)
    assert np.abs(first).max() > 0.01
    assert np.array_equal(first, render(audio, 0.2))
    assert np.array_equal(first, render(s.play(), 0.2))


def test_two_parts_on_one_instrument_each_equal_the_part_alone():
    together = _hands(ElectricPiano(seed=3)).play()
    right_alone = render(_hands(ElectricPiano(seed=3), left=False).play(), 0.2)
    left_alone = render(_hands(ElectricPiano(seed=3), right=False).play(), 0.2)
    assert np.abs(right_alone).max() > 0.01 and np.abs(left_alone).max() > 0.01
    assert np.array_equal(render(together.parts["right"], 0.2), right_alone)
    assert np.array_equal(render(together.parts["left"], 0.2), left_alone)
    assert np.array_equal(render(together, 0.2), right_alone + left_alone)


def test_two_parts_on_one_instrument_do_not_steal_each_others_voices():
    piano = ElectricPiano(seed=3)
    piano.polyphony = 1
    s = Score(tempo=240)
    s.part("right", piano).add(melody("c5:h"))
    s.part("left", piano).add(melody("r:q c3"))
    audio = s.play()
    assert audio.parts["right"].stops == audio.parts["right"].ends


def test_notes_are_every_parts_in_time_order():
    s = Score(tempo=240)
    s.part("a", Harp()).add(melody("r:e c4 r d4"))
    s.part("b", Harp()).add(melody("e3:e r f3 r"))
    notes = s.play().notes
    assert all(isinstance(note, Note) for note in notes)
    assert [note.pitch for note in notes] == [E3, C4, F3, D4]
    assert [note.time for note in notes] == sorted(note.time for note in notes)


def _long() -> Score:
    s = Score(tempo=120)
    s.part("a", Harp(seed=3)).add(melody(" | ".join(["c4:w"] * 6)))  # 6 bars of 2 s
    return s


def test_take_of_a_long_score_is_its_whole_length_and_not_defaulted():
    audio = _long().play()
    assert audio.duration > 12 > MAX_DEFAULT
    clip = audio.take(caption="all of it")
    assert clip.seconds == pytest.approx(audio.duration, abs=1 / RATE)
    assert not clip.defaulted
    assert clip.caption == "all of it"
    assert clip.source is audio


def test_take_with_seconds_renders_those_seconds():
    clip = _score(Harp()).play().take(0.05)
    assert clip.seconds == 0.05 and not clip.defaulted


def test_listen_carries_the_full_length():
    audio = _long().play()
    assert listen(audio).audio.seconds == pytest.approx(audio.duration, abs=1 / RATE)
