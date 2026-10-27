def test_gain_db_measures_a_filter_and_never_prints_minus_zero():
    from euterpe.book import gain_db
    from euterpe.sound import Gain, LowPass

    assert gain_db(lambda s: LowPass(s, cutoff=1_000.0), 1_000.0) == -3.0
    assert gain_db(lambda s: Gain(s, 0.5), 300.0) == -6.0
    assert str(gain_db(lambda s: LowPass(s, cutoff=1_000.0), 50.0)) == "0.0"
