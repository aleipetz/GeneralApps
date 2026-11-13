from datetime import date

from flightwatch import config, dates


def test_fridays_to_sundays_six_months():
    cfg = config.load()
    today = date(2026, 11, 13)  # sexta
    trips = dates.trip_dates(cfg, today)
    assert 24 <= len(trips) <= 27
    for t in trips:
        assert t.outbound.weekday() == 4 and t.inbound.weekday() == 6
        assert (t.outbound - today).days <= 183
    assert trips[0].outbound == today
