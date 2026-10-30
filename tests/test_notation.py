from fractions import Fraction

import pytest

import euterpe
from euterpe import Chord, Interval, Key, Meter, Pitch, Score, arpeggiate, chords, drums, melody
from euterpe.instruments import Accent, Harp, Kit, Legato, Staccato, Tenuto
from euterpe.score import BarRest, Hit, Line, Note, Numeral, Rest, Tuplet

W = Fraction(1)
H = Fraction(1, 2)
Q = Fraction(1, 4)
E = Fraction(1, 8)
S = Fraction(1, 16)


def note(name, duration=Q, **kwargs):
    return Note(Pitch(name), duration, **kwargs)


def stack(names, duration=Q, **kwargs):
    return Note(tuple(Pitch(name) for name in names.split()), duration, **kwargs)


def events(line):
    """The events of a one-bar line."""
    assert len(line.bars) == 1
    return list(line.bars[0])


def names(line):
    """Each note's pitches by name, bar by bar, in a line that resolves without a score."""
    return [[" ".join(str(p) for p in event.pitches) for event in bar if isinstance(event, Note)] for bar in line.bars]


def placed(score, part):
    return [(p.offset, p.event) for p in score.events(part)]


# melody: each row of the table in section 05


def test_a_note_and_a_duration():
    assert events(melody("f#4:q")) == [note("F#4", Q)]


@pytest.mark.parametrize("text, name, duration", [
    ("c4:w", "C4", W), ("c4:h", "C4", H), ("c4:q", "C4", Q), ("c4:e", "C4", E), ("c4:s", "C4", S),
    ("c4:t", "C4", Fraction(1, 32)), ("c#4:q", "C#4", Q), ("cb4:q", "Cb4", Q), ("c##4:q", "C##4", Q),
    ("cbb4:q", "Cbb4", Q), ("bb4:q", "Bb4", Q), ("bbb4:q", "Bbb4", Q), ("c-1:q", "C-1", Q),
])
def test_letters_accidentals_and_durations(text, name, duration):
    assert events(melody(text)) == [note(name, duration)]


def test_each_dot_adds_half_again():
    assert events(melody("a4:q."))[0].duration == Fraction(3, 8)
    assert events(melody("a4:q.."))[0].duration == Fraction(7, 16)


def test_a_missing_duration_repeats_the_last_one():
    assert [e.duration for e in events(melody("a4:e d5 r g4:h b4"))] == [E, E, E, H, H]


def test_the_first_note_takes_a_quarter_without_a_duration():
    assert events(melody("a4")) == [note("A4", Q)]


def test_a_missing_octave_takes_the_nearest():
    assert names(melody("f4 g a")) == [["F4", "G4", "A4"]]
    assert names(melody("c5 a")) == [["C5", "A4"]]
    assert names(melody("b3 c")) == [["B3", "C4"]]
    assert names(melody("c4 b")) == [["C4", "B3"]]


def test_a_tritone_away_goes_up():
    assert names(melody("f4 b")) == [["F4", "B4"]]
    assert names(melody("b4 f")) == [["B4", "F5"]]


def test_the_nearest_octave_counts_the_accidentals():
    assert names(melody("b3 cb")) == [["B3", "Cb4"]]
    assert names(melody("c4 b#")) == [["C4", "B#3"]]


def test_a_rest_does_not_reset_the_octave():
    assert names(melody("g4 r a")) == [["G4", "A4"]]


def test_a_stack_passes_its_last_note_on():
    assert names(melody("<c4 e g> a")) == [["C4 E4 G4", "A4"]]


def test_the_first_note_without_an_octave_raises():
    with pytest.raises(ValueError, match=r'melody: bar 1, token "c:q": the first note of a line needs its octave'):
        melody("c:q d")
    with pytest.raises(ValueError, match=r'melody: bar 2, token "c": the first note of a line needs its octave'):
        melody("r:q | c")


def test_a_rest():
    assert events(melody("r:q")) == [Rest(Q)]
    assert events(melody("c4:e r")) == [note("C4", E), Rest(E)]


def test_a_whole_bar_rest():
    assert melody("R | c4:q").bars[0] == (BarRest(),)


@pytest.mark.parametrize("meter, length", [("3/4", Fraction(3, 4)), ("6/8", Fraction(3, 4)), ("4/4", W), ("7/8", Fraction(7, 8))])
def test_a_whole_bar_rest_fills_the_bar(meter, length):
    s = Score(meter=Meter(meter))
    s.part("a").add(melody("R | c4:q"))
    assert placed(s, "a") == [(0, Rest(length)), (length, note("C4", Q))]


def test_a_bar_line_splits_the_bars_and_does_not_check_them():
    line = melody("c4:q d | e:h f:h g:h |")
    assert len(line.bars) == 2
    assert names(line) == [["C4", "D4"], ["E4", "F4", "G4"]]


def test_a_tie():
    assert events(melody("a4:q~ a4:e")) == [note("A4", Q, tie=True), note("A4", E)]


def test_a_tie_to_another_note_is_for_lint_to_report():
    assert events(melody("c4~ d4"))[0].tie


def test_a_tie_crosses_a_bar():
    line = melody("c4:h~ | c4:h")
    assert line.bars[0][0].tie
    assert not line.bars[1][0].tie


def test_notes_that_sound_together_are_one_note():
    assert events(melody("<c4 e4 g4>:h")) == [stack("C4 E4 G4", H)]


def test_a_stack_takes_ties_and_articulations():
    assert events(melody("<c4 e4>:q~>")) == [stack("C4 E4", Q, tie=True, articulations=(Accent(),))]


def test_a_triplet_sums_exactly():
    line = melody("3[c5:e d5 e5]")
    assert events(line) == [note(n, Fraction(1, 12), tuplet=Tuplet(3, 2)) for n in ("C5", "D5", "E5")]
    assert line.duration == Q


def test_a_tuplet_with_its_own_ratio():
    line = melody("5:4[c5:s d e f g]")
    assert line.duration == Q
    assert {e.tuplet for e in events(line)} == {Tuplet(5, 4)}
    assert events(line)[0].duration == Fraction(1, 20)


def test_a_bare_count_takes_the_power_of_two_below_it():
    assert events(melody("5[c5:s]"))[0].tuplet == Tuplet(5, 4)
    assert events(melody("7[c5:s]"))[0].tuplet == Tuplet(7, 4)
    assert events(melody("4[c5:s]"))[0].tuplet == Tuplet(4, 2)


def test_a_duration_after_a_tuplet_is_the_written_one():
    assert events(melody("3[c5:e d e] f"))[-1] == note("F5", E)


def test_a_rest_in_a_tuplet_carries_it():
    assert events(melody("3[c5:e r:e d]"))[1] == Rest(Fraction(1, 12), tuplet=Tuplet(3, 2))


def test_a_short_tuplet_is_for_lint_to_report():
    assert melody("3[c5:e d]").duration == Fraction(1, 6)


def test_a_slur():
    first, second, third = events(melody("( e4:q f4 g4 )"))
    assert first == note("E4", Q, slur="start")
    assert second == note("F4", Q, articulations=(Legato(),))
    assert third == note("G4", Q, articulations=(Legato(),), slur="stop")


def test_a_slur_may_touch_its_notes_and_cross_a_bar():
    line = melody("(e4:q f | g)")
    assert line.bars[0][0].slur == "start"
    assert line.bars[1][0].slur == "stop"
    assert line.bars[1][0].articulations == (Legato(),)


@pytest.mark.parametrize("text, articulation", [("e4:q'", Staccato()), ("e4:q>", Accent()), ("e4:q_", Tenuto())])
def test_articulations(text, articulation):
    assert events(melody(text)) == [note("E4", Q, articulations=(articulation,))]


def test_marks_may_follow_a_note_with_no_duration():
    assert events(melody("e4'"))[0].articulations == (Staccato(),)
    assert events(melody("e4:q'>"))[0].articulations == (Staccato(), Accent())
    assert events(melody("e4:q'~"))[0].tie


def test_a_slurred_note_keeps_its_own_articulation():
    assert events(melody("(e4:q f' )"))[1].articulations == (Staccato(), Legato())


@pytest.mark.parametrize("token, mark", [("pp", "pp"), ("p", "p"), ("mp", "mp"), ("mf", "mf"), ("f!", "f"), ("ff", "ff")])
def test_a_dynamic_from_the_next_note_on(token, mark):
    first, second = events(melody(f"c4:q {token} d4"))
    assert first.dynamic is None
    assert second.dynamic == mark


def test_a_bare_f_is_the_note():
    assert events(melody("f4 f")) == [note("F4"), note("F4")]
    assert events(melody("f4 f! f"))[1] == note("F4", dynamic="f")


def test_a_dynamic_waits_past_a_rest():
    assert events(melody("p r:q c4"))[1].dynamic == "p"


def test_a_lone_angle_is_a_hairpin_and_an_attached_one_is_not():
    rising, falling = events(melody("< c4:q > d4"))
    assert (rising.hairpin, rising.articulations) == ("<", ())
    assert (falling.hairpin, falling.articulations) == (">", ())
    assert events(melody("c4:q> <d4 e4>"))[0].articulations == (Accent(),)
    assert events(melody("c4:q> <d4 e4>"))[1] == stack("D4 E4")


def test_a_written_dynamic_reaches_the_part():
    s = Score()
    part = s.part("a").add(melody("c4:q p d4 e4 f4 | ff g4:w"))
    assert [(mark.bar, mark.in_bar, mark.offset, mark.mark) for mark in part.dynamics] == [(1, Q, Q, "p"), (2, 0, W, "ff")]


def test_a_written_dynamic_joins_the_placed_ones_in_order():
    s = Score()
    part = s.part("a").add(melody("c4:q p d4 e4 f4")).dynamic(1, 3, "f")
    assert [mark.mark for mark in part.dynamics] == ["p", "f"]


def test_a_hairpin_runs_up_to_the_next_dynamic():
    s = Score()
    part = s.part("a").add(melody("p < c4:q d4 e4 f4 | f! g4:w"))
    pin = part.hairpins[0]
    assert (pin.kind, pin.start, pin.end, pin.start_at, pin.end_at) == ("<", 0, W, (1, 0), (2, 0))


def test_a_hairpin_runs_up_to_the_next_hairpin():
    part = Score().part("a").add(melody("< c4:q d4 > e4 f4"))
    assert [(pin.kind, pin.start, pin.end) for pin in part.hairpins] == [("<", 0, H), (">", H, W)]


def test_a_hairpin_with_no_mark_after_it_runs_to_the_end_of_its_line():
    part = Score().part("a").add(melody("c4:q < d4 e4 f4"))
    assert [(pin.start, pin.end) for pin in part.hairpins] == [(Q, W)]


def test_a_hairpin_in_a_pickup_counts_from_the_end_of_the_bar():
    s = Score(pickup=Q)
    pin = s.part("a").add(melody("< c4:q | d4:w f! | e4:w")).hairpins[0]
    assert (pin.start, pin.end, pin.start_at, pin.end_at) == (0, Fraction(5, 4), (1, Fraction(3, 4)), (3, 0))


def test_written_marks_survive_a_transpose():
    s = Score()
    s.part("a").add(melody("p < c4:q d4 f! e4"))
    moved = s.transpose(Interval("M2")).parts["a"]
    assert [mark.mark for mark in moved.dynamics] == ["p", "f"]
    assert [pin.kind for pin in moved.hairpins] == ["<"]


# melody: errors


def test_the_error_names_the_token_and_its_bar():
    with pytest.raises(ValueError) as error:
        melody("c4:q | d4 | h4:q")
    assert str(error.value) == 'melody: bar 3, token "h4:q": no note h'


@pytest.mark.parametrize("text, message", [
    ("c4:z", 'melody: bar 1, token "c4:z": no duration z'),
    ("c4:", 'melody: bar 1, token "c4:": no duration '),
    ("c:q'4", 'melody: bar 1, token "c:q\'4": cannot read it'),
    ("c4x", 'melody: bar 1, token "c4x": cannot read the note c4x'),
    ("C4", 'melody: bar 1, token "C4": no note C'),
    ("fff", 'melody: bar 1, token "fff": cannot read the note fff'),
    ("<c4 e4", 'melody: bar 1, token "<c4": a stack needs its closing >'),
    ("<>", 'melody: bar 1, token "<>": a stack needs a note'),
    ("<c4:q e4>", 'melody: bar 1, token "<c4:q e4>": cannot read the note c4:q'),
    ("c4 <h4 e4>", 'melody: bar 1, token "<h4 e4>": no note h'),
    ("r'", 'melody: bar 1, token "r\'": a rest takes no marks'),
    ("R:q", 'melody: bar 1, token "R:q": R fills its bar and takes no duration'),
    ("c4''", 'melody: bar 1, token "c4\'\'": a mark written twice'),
    ("3[c5:e | d e]", 'melody: bar 1, token "|": a tuplet must close inside its bar'),
    ("3[c5:e 3[d e]]", 'melody: bar 1, token "3[": a tuplet cannot hold a tuplet'),
    ("3[c5:e d", 'melody: bar 1, token "3[": a tuplet needs its closing ]'),
    ("c4 ]", 'melody: bar 1, token "]": no tuplet to close'),
    ("[c4", 'melody: bar 1, token "[": a tuplet needs its count, as 3[...]'),
    ("2[c4]", 'melody: bar 1, token "2[": a tuplet needs at least 3 notes, or its ratio, as 2:3[...]'),
    ("0:4[c4]", 'melody: bar 1, token "0:4[": a tuplet needs at least one note in the time of one'),
    ("3:0[c4]", 'melody: bar 1, token "3:0[": a tuplet needs at least one note in the time of one'),
    ("( c4 ( d4 ) )", 'melody: bar 1, token "(": a slur cannot hold a slur'),
    ("c4 )", 'melody: bar 1, token ")": no slur to close'),
    ("( c4 )", 'melody: bar 1, token ")": a slur needs two notes'),
    ("( c4 d4", 'melody: bar 1, token "(": a slur needs its closing )'),
    ("c4 p", 'melody: bar 1, token "p": no note after it'),
    ("p mf c4", 'melody: bar 1, token "mf": no note after the last mark'),
    ("c4 <", 'melody: bar 1, token "<": no note after it'),
    ("< > c4", 'melody: bar 1, token ">": no note after the last mark'),
])
def test_parse_errors(text, message):
    with pytest.raises(ValueError) as error:
        melody(text)
    assert str(error.value) == message


def test_text_too_short_to_be_a_bar_is_no_bar():
    assert melody("").bars == ()
    assert melody("c4 |").duration == Q


def test_melody_returns_a_line():
    line = melody("f#4:q a4 d5 | c#5:h b4:q | a4:h.")
    assert isinstance(line, Line)
    assert line.duration == Fraction(9, 4)


def test_a_melody_transposes_by_its_spelling():
    assert names(melody("c4:q e").transpose(Interval("m3"))) == [["Eb4", "G4"]]


def test_a_melody_joins_and_repeats():
    assert (melody("c4:q") + melody("d4:q")).bars == (melody("c4:q").bars[0], melody("d4:q").bars[0])
    assert (melody("c4:q") * 2).duration == H


# chords


def bar_roots(score, part):
    return [Chord.from_pitches(p.event.pitches).root for p in score.events(part)]


def test_a_symbol_resolves_now():
    first, second = events(chords("Am:q G/B:q"))
    assert (first.pitches, first.duration) == (Chord("Am").pitches(4), Q)
    assert (Chord.from_pitches(second.pitches), second.duration) == (Chord("G/B"), Q)


def test_a_numeral_waits_for_the_key():
    item = events(chords("V7:h."))[0]
    assert isinstance(item, Numeral)
    assert (item.text, item.duration) == ("V7", Fraction(3, 4))


def test_numerals_resolve_in_the_key_in_force():
    s = Score(key=Key("D major"), meter=Meter("3/4"))
    s.part("a").add(chords("I:h. | V:h. | I:h."))
    assert bar_roots(s, "a") == ["D", "A", "D"]
    s.change(3, key=Key("G major"))
    assert bar_roots(s, "a") == ["D", "A", "G"]


def test_uppercase_a_to_g_is_a_symbol_and_anything_else_a_numeral():
    line = chords("C:q III:q bVI:q #iv:q vii°7/V:q")
    assert isinstance(line.bars[0][0], Note)
    assert [isinstance(item, Numeral) for item in line.bars[0][1:]] == [True] * 4


def test_close_picks_the_inversion_that_moves_least():
    assert names(chords("C:q F G C")) == [["C4 E4 G4", "C4 F4 A4", "D4 G4 B4", "E4 G4 C5"]]


def test_close_on_numerals_reads_the_chord_before():
    s = Score()
    s.part("a").add(chords("I:q IV"))
    assert [[str(x) for x in pitches.event.pitches] for pitches in s.events("a")] == [["C4", "E4", "G4"], ["C4", "F4", "A4"]]


def test_a_figure_sets_the_bass():
    assert names(chords("C:q G/B")) == [["C4 E4 G4", "B4 D5 G5"]]
    s = Score()
    s.part("a").add(chords("I:q V6"))
    assert str(next(p for p in s.events("a") if p.offset == Q).event.pitches[0]) == "B4"


def test_close_after_a_rest_still_reads_the_last_chord():
    assert names(chords("C:q r F")) == [["C4 E4 G4", "C4 F4 A4"]]


def test_a_symbol_after_a_numeral_takes_its_plain_close_voicing():
    s = Score()
    s.part("a").add(chords("I:q G"))
    assert [str(x) for x in next(p for p in s.events("a") if p.offset == Q).event.pitches] == ["G4", "B4", "D5"]


def test_root_and_open_voicings():
    assert names(chords("C/E:q G", voicing="root")) == [["C4 E4 G4", "G4 B4 D5"]]
    assert names(chords("C:q F", voicing="open")) == [["E3 C4 G4", "A3 F4 C5"]]


def test_an_unknown_voicing_raises():
    with pytest.raises(ValueError, match="no voicing 'wide'"):
        chords("I:q", voicing="wide")


def test_octave_places_the_chord():
    assert names(chords("C:q", octave=3)) == [["C3 E3 G3"]]


def test_bass_adds_the_bass_note_in_its_octave():
    assert names(chords("C:q C/E", bass=2)) == [["C2 C4 E4 G4", "E2 E4 G4 C5"]]


def test_the_added_bass_does_not_steer_the_close_voicing():
    assert names(chords("C:q F G", bass=2)) == [["C2 C4 E4 G4", "F2 C4 F4 A4", "G2 D4 G4 B4"]]
    assert names(chords("D:q Cm", bass=2))[0][1] == "C2 Eb4 G4 C5"


def test_chords_read_rests():
    s = Score(meter=Meter("3/4"))
    s.part("a").add(chords("R | C:h. r:q"))
    assert placed(s, "a")[0] == (0, Rest(Fraction(3, 4)))
    assert isinstance(chords("r:q").bars[0][0], Rest)


def test_a_duration_carries_over_in_chords():
    assert chords("C:h. F G").duration == Fraction(9, 4)
    assert chords("C F").duration == H
    assert chords("I:e V").duration == Q


@pytest.mark.parametrize("text, message", [
    ("C | H7:q", 'chords: bar 2, token "H7:q": no numeral or chord H7'),
    ("Cq:q", 'chords: bar 1, token "Cq:q": Chord: cannot read \'Cq\'; write a root, a quality and any bass: F#m7b5, C/E'),
    ("xyz", 'chords: bar 1, token "xyz": no numeral or chord xyz'),
    ("I:z", 'chords: bar 1, token "I:z": no duration z'),
    ("I:q~", 'chords: bar 1, token "I:q~": a chord takes no marks'),
    ("<c4 e4 g4>:q", 'chords: bar 1, token "<c4 e4 g4>:q": no numeral or chord <c4 e4 g4>'),
])
def test_chord_errors(text, message):
    with pytest.raises(ValueError) as error:
        chords(text)
    assert str(error.value) == message


def test_a_numeral_a_key_cannot_read_raises_at_the_add():
    with pytest.raises(ValueError, match=r"part 'a', bar 1: .*half-diminished"):
        Score().part("a").add(chords("viiø:q"))


def test_a_chord_line_transposes_only_without_numerals():
    assert names(chords("C:q").transpose(Interval("M2"))) == [["D4 F#4 A4"]]
    with pytest.raises(ValueError, match="numerals move with the key"):
        chords("I:q").transpose(Interval("M2"))


# arpeggiate


def test_a_figure_repeats_to_fill_the_chord():
    line = arpeggiate("<g3 c4 eb4 g4>:w", "0 1 2 3 2 1", step="e")
    assert names(line) == [["G3", "C4", "Eb4", "G4", "Eb4", "C4", "G3", "C4"]]
    assert {e.duration for e in events(line)} == {E}
    assert line.duration == W


def test_the_last_step_is_cut():
    line = arpeggiate("<c4 e4>:q.", "0 1", step="q")
    assert [e.duration for e in events(line)] == [Q, E]
    assert line.duration == Fraction(3, 8)


def test_a_stack_plays_from_low_to_high_whatever_its_order():
    assert names(arpeggiate("<g4 c4 e4>:e.", "0 1 2", step="s")) == [["C4", "E4", "G4"]]


def test_the_step_defaults_to_a_sixteenth():
    assert {e.duration for e in events(arpeggiate("<c4 e4>:q", "0 1"))} == {S}


def test_arpeggiate_takes_a_symbol():
    assert names(arpeggiate("C/E:q", "0 1 2 1", step="s")) == [["E4", "G4", "C5", "G4"]]


def test_arpeggiate_takes_a_numeral_in_the_key_in_force():
    s = Score(key=Key("G major"))
    s.part("a").add(arpeggiate("I:q V", "0 1 2 1", step="s"))
    assert [str(p.event.pitches[0]) for p in s.events("a")] == ["G4", "B4", "D5", "B4", "D4", "F#4", "A4", "F#4"]
    assert [p.offset for p in s.events("a")][4] == Q
    s.change(1, key=Key("D major"))
    assert str(next(s.events("a")).event.pitches[0]) == "D4"


def test_arpeggiate_keeps_bars_and_rests():
    line = arpeggiate("<c4 e4>:e r:e | R | <d4 f4>:e", "0 1", step="s")
    assert line.bars[0][-1] == Rest(E)
    assert line.bars[1] == (BarRest(),)
    assert names(line)[2] == ["D4", "F4"]


def test_arpeggiate_reads_relative_octaves_in_stacks():
    assert names(arpeggiate("<c4 e g>:e <f a c>:e", "0", step="e")) == [["C4", "F4"]]


@pytest.mark.parametrize("text, figure, step, message", [
    ("<c4 e4>:q", "0 2", "s", 'arpeggiate: bar 1, token "<c4 e4>:q": figure index 2 is past the top of a chord of 2 notes'),
    ("<c4 e4>:q", "0 x", "s", 'arpeggiate: figure index x is not a number from 0 up'),
    ("<c4 e4>:q", "0 -1", "s", 'arpeggiate: figure index -1 is not a number from 0 up'),
    ("<c4 e4>:q", "", "s", 'arpeggiate: a figure needs at least one index'),
    ("<c4 e4>:q", "0", "z", 'arpeggiate: no step z'),
    ("<c4 e4>:q~", "0", "s", 'arpeggiate: bar 1, token "<c4 e4>:q~": a chord takes no marks'),
    ("<c4 h4>:q", "0", "s", 'arpeggiate: bar 1, token "<c4 h4>:q": no note h'),
])
def test_arpeggiate_errors(text, figure, step, message):
    with pytest.raises(ValueError) as error:
        arpeggiate(text, figure, step=step)
    assert str(error.value) == message


def test_a_numeral_too_small_for_the_figure_raises_at_the_add():
    with pytest.raises(ValueError, match=r"part 'a', bar 1: figure index 5 is past the top of a chord of 3 notes"):
        Score().part("a").add(arpeggiate("I:q", "0 5"))


# drums


def row(line, voice):
    """The events of a voice of a one-bar drum line."""
    return list(([line, *line.together][voice]).bars[0])


def test_a_grid_has_one_event_per_step():
    line = drums({"kick": "x... x...", "snare": "..x. ..x."})
    assert len(line.bars) == 1
    assert len(line.bars[0]) == 8
    assert line.duration == H
    assert row(line, 0) == [Hit("kick", S, "x"), Rest(S), Rest(S), Rest(S), Hit("kick", S, "x"), Rest(S), Rest(S), Rest(S)]
    assert row(line, 1)[2] == Hit("snare", S, "x")


def test_a_bar_line_in_the_grid_is_a_bar():
    line = drums({"kick": "x...|x..."})
    assert len(line.bars) == 2
    assert line.duration == Q * 2
    assert len(drums({"kick": "x...|x...|"}).bars) == 2


def test_the_accent_is_the_grid_character():
    assert [e.accent for e in row(drums({"hihat": "xXgo"}), 0)] == ["x", "X", "g", "o"]


def test_a_step_sets_the_length():
    assert row(drums({"kick": "x"}, step="e"), 0) == [Hit("kick", E, "x")]
    assert row(drums({"kick": "x"}, step="q."), 0) == [Hit("kick", Fraction(3, 8), "x")]


@pytest.mark.parametrize("name", ["kick", "snare", "hihat", "crash", "ride", "tom1", "tom2", "tom3"])
def test_every_drum_name(name):
    assert row(drums({name: "x"}), 0)[0].drum == name


def test_drums_struck_together_sit_at_one_place_in_a_score():
    s = Score()
    s.part("drums", Kit()).add(drums({"kick": "x...", "snare": "x...", "hihat": "x.x."}, step="e"))
    hits = [(p.offset, p.event.drum) for p in s.events("drums") if isinstance(p.event, Hit)]
    assert sorted(hits) == [(0, "hihat"), (0, "kick"), (0, "snare"), (Q, "hihat")]


def test_each_row_takes_its_own_voice_from_the_voice_asked_for():
    s = Score()
    part = s.part("drums", Kit()).add(drums({"kick": "x", "snare": "x"}), voice=2)
    assert [len(voice) for voice in part.measures[0].voices] == [0, 0, 1, 1]


def test_a_short_row_is_filled_with_rests():
    s = Score()
    s.part("drums").add(drums({"kick": "x...", "snare": "x"}, step="q"))
    assert {p.voice: p.offset for p in s.events("drums")} == {0: Fraction(3, 4), 1: Fraction(3, 4)}


def test_drum_lines_join_and_repeat_with_their_rows():
    s = Score()
    joined = drums({"kick": "x", "snare": "x"}) + drums({"hihat": "x"}) + drums({"kick": "x", "ride": "x", "crash": "x"})
    s.part("drums").add(joined * 2)
    assert s.bars == 6
    hits = [(p.bar, p.event.drum) for p in s.events("drums")]
    assert [drum for bar, drum in hits if bar == 1] == ["kick", "snare"]
    assert [drum for bar, drum in hits if bar == 3] == ["kick", "ride", "crash"]
    assert [drum for bar, drum in hits if bar == 4] == ["kick", "snare"]


def test_a_drum_line_appends_after_itself():
    s = Score()
    s.part("drums").add(drums({"kick": "x", "snare": "x"})).add(drums({"kick": "x", "snare": "x"}))
    assert s.bars == 2


def test_a_row_that_collides_with_a_written_voice_raises():
    part = Score().part("drums").add(melody("c4:q"), voice=1)
    with pytest.raises(ValueError, match="voice 1 already holds bar 1"):
        part.add(drums({"kick": "x", "snare": "x"}))


def test_a_drum_line_transposes_as_it_stands():
    line = drums({"kick": "x", "snare": "x"})
    assert line.transpose(Interval("M2")) == line


def test_a_score_transposes_a_drum_part():
    s = Score()
    s.part("drums", Kit()).add(drums({"kick": "x", "snare": "x"}))
    assert [p.event.drum for p in s.transpose(Interval("M2")).events("drums")] == ["kick", "snare"]


def test_drums_need_a_kit():
    with pytest.raises(ValueError, match="a drum hit needs a Kit"):
        Score().part("lead", Harp()).add(drums({"kick": "x"}))
    with pytest.raises(ValueError, match="a drum hit needs a Kit"):
        Score().part("lead", Harp()).add(drums({"kick": ".", "snare": "x"}))


@pytest.mark.parametrize("grid, step, message", [
    ({}, "s", "drums: a grid needs at least one row"),
    ({"cowbell": "x"}, "s", "drums: no drum 'cowbell'; the drums are kick, snare, hihat, crash, ride, tom1, tom2, tom3"),
    ({"kick": "x|x", "snare": "x"}, "s", "drums: kick has 2 bars and snare has 1"),
    ({"kick": "xz"}, "s", "drums: kick: pattern: 'z' at step 1 is not one of x X g o . (a space or | groups)"),
    ({"kick": "x"}, "z", "drums: no step z"),
])
def test_drum_errors(grid, step, message):
    with pytest.raises(ValueError) as error:
        drums(grid, step=step)
    assert str(error.value) == message


# the whole of it


def test_the_spec_piece_is_written_from_the_top_of_the_package():
    assert {"melody", "chords", "arpeggiate", "drums"} <= set(euterpe.__all__)
    s = Score(key=Key("D major"), meter=Meter("3/4"), tempo=84)
    s.part("melody", Harp()).add(melody("f#4:q a4 d5 | c#5:h b4:q | a4:h."))
    s.part("chords", Harp()).add(chords("I:h. | V:h. | I:h.", voicing="close"))
    assert s.bars == 3
    assert [str(p.event.pitches[0]) for p in s.events("melody")] == ["F#4", "A4", "D5", "C#5", "B4", "A4"]
    assert [h.chord.root for h in s.harmony() if h.beat == 1] == ["D", "A", "D"]


def test_a_hairpin_ends_where_its_voice_ends_and_not_where_the_part_does():
    s = Score()
    part = s.part("a").add(melody("< c4:w")).add(melody("c5:w | d5:w"), voice=1)
    assert [(pin.start, pin.end, pin.end_at) for pin in part.hairpins] == [(0, W, (1, W))]
