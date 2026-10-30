import json

from euterpe.lint import Finding, Report


def test_an_audio_finding_has_null_places_in_json():
    [f] = json.loads(Report([Finding("A-PEAK", "metric", "sample peak -6.0 dBFS", -6.02)]).to_json())["findings"]
    assert (f["part"], f["bar"], f["beat"]) == (None, None, None)


def test_json_keeps_the_place_with_beat_a_float_from_1():
    [f] = json.loads(Report([Finding("N-TIE", "error", "x", part="alto", bar=3, beat=2.5)]).to_json())["findings"]
    assert (f["part"], f["bar"], f["beat"]) == ("alto", 3, 2.5)


def test_text_prints_the_place_when_it_has_one():
    report = Report([Finding("N-TIE", "error", "a tie", part="alto", bar=3, beat=2.0)])
    assert report.to_text() == "error  N-TIE          part alto, bar 3, beat 2: a tie"


def test_text_prints_a_beat_between_beats_and_a_part_alone():
    assert "bar 1, beat 2.5: x" in Report([Finding("N-TIE", "warn", "x", bar=1, beat=2.5)]).to_text()
    assert Report([Finding("R-COMFORT", "metric", "x", part="alto")]).to_text().endswith("part alto: x")


def test_text_without_a_place_is_as_before():
    assert Report([Finding("A-PEAK", "metric", "x")]).to_text() == "metric A-PEAK         x"
