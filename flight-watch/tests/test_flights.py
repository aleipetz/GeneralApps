from fast_flights.model import Airport, SimpleDatetime, SingleFlight

from flightwatch.google_flights import total_minutes


def seg(dep, arr, dur, a="GRU", b="LIS"):
    return SingleFlight(Airport("", a), Airport("", b), SimpleDatetime(*dep), SimpleDatetime(*arr), dur, "")


def test_total_includes_layover():
    # GRU 20:40 -> LIS 10:30 (+1, 9h50 voando); LIS 13:00 -> BER 17:35 (3h35 voando)
    s1 = seg(((2027, 1, 22), (20, 40)), ((2027, 1, 23), (10, 30)), 590)
    s2 = seg(((2027, 1, 23), (13, 0)), ((2027, 1, 23), (17, 35)), 215, "LIS", "BER")
    assert total_minutes([s1, s2]) == 590 + 150 + 215
