from datetime import date

from flightwatch import config, dates


def test_patterns():
    cfg = config.load()
    trips = dates.trip_dates(cfg, date(2026, 11, 13))
    assert trips, "deveria haver datas"
    for t in trips:
        assert (t.inbound - t.outbound).days == 15
        if t.pattern.outbound_weekday == 4:
            assert t.outbound.weekday() == 4 and t.inbound.weekday() == 5
        else:
            assert t.outbound.weekday() == 5 and t.inbound.weekday() == 6
    assert trips[0].outbound >= date(2026, 11, 27)
