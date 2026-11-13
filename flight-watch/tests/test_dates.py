from datetime import date

from flightwatch import config, dates


def test_patterns():
    cfg = config.load()
    today = date(2026, 11, 13)
    trips = dates.trip_dates(cfg, today)
    assert trips, "deveria haver datas"
    for t in trips:
        assert t.outbound.weekday() == 4 and t.inbound.weekday() == 6   # sexta -> domingo
        assert (t.inbound - t.outbound).days == 16
        assert today <= t.outbound and (t.inbound - today).days <= cfg.max_days_ahead
    assert trips[0].outbound == date(2026, 11, 13)
