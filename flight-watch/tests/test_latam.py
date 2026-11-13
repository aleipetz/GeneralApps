"""Testes do parser LATAM Pass com respostas reais (capturadas em 2026-11-13).

Fixtures: etapas 1 (ida GRU→BER 22/01/2027, sexta) e 2 (volta BER→GRU
06/02/2027, sábado) da mesma busca ida e volta com milhas.
"""
import json
import re
from datetime import date
from pathlib import Path

from flightwatch import config, latam
from flightwatch.config import DatePattern
from flightwatch.dates import TripDates

FIX = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


OUT = load("latam_redemption_GRU_BER_2027-01-22.json")
IN = load("latam_redemption_BER_GRU_2027-02-06.json")


def cfg():
    return config.load()


# Padrões fixos nos testes (independentes do config.toml atual).
PATTERNS = {
    "sex-noite": DatePattern("sex-noite -> sab-noite", 4, 15,
                             outbound_min_hour=18, return_min_hour=18),
    "sab-manha": DatePattern("sab-manha -> dom-manha", 5, 15,
                             outbound_max_hour=12, return_max_hour=12),
    "livre": DatePattern("sex -> dom", 4, 16),
}


def pattern(name: str) -> DatePattern:
    return PATTERNS[name]


def test_no_time_limits_keeps_everything():
    p = pattern("livre")
    legs = latam.parse_offers(OUT) + latam.parse_offers(IN)
    assert all(latam.outbound_ok(l, p) and latam.return_ok(l, p) for l in legs)


def test_parse_outbound_basic():
    legs = latam.parse_offers(OUT)
    assert legs
    assert {l.cabin for l in legs} == {"economy", "business"}
    for l in legs:
        assert l.origin == "GRU" and l.destination == "BER"
        assert l.departure.startswith("2027-01-22")
        assert l.miles > 10_000 and l.taxes_brl > 0
        assert l.flights and all(re.fullmatch(r"[A-Z0-9]{2}\d{1,4}", f) for f in l.flights)


def test_cheapest_brand_per_cabin():
    legs = latam.parse_offers(OUT)
    la8070 = [l for l in legs if l.flights[0] == "LA8070" and l.departure.endswith("23:30:00")
              and l.arrival == "2027-01-23T20:50:00"]
    by_cabin = {l.cabin: l for l in la8070}
    assert by_cabin["economy"].miles == 100_784 and by_cabin["economy"].brand == "KM"
    assert by_cabin["business"].miles == 387_348 and by_cabin["business"].brand == "EV"
    assert by_cabin["economy"].taxes_brl == 319.69
    assert by_cabin["economy"].stops == 1


def test_parse_inbound():
    legs = latam.parse_offers(IN)
    assert all(l.origin == "BER" and l.destination == "GRU" for l in legs)
    eco = min((l for l in legs if l.cabin == "economy"), key=lambda l: l.miles)
    assert eco.miles == 86_554 and eco.taxes_brl == 656.47
    assert "Lufthansa" in eco.airlines


def test_time_windows():
    p = pattern("sex-noite")
    legs = latam.parse_offers(OUT)
    ok = [l for l in legs if latam.outbound_ok(l, p)]
    assert ok and all(l.dep.hour >= 18 for l in ok)
    assert any(not latam.outbound_ok(l, p) for l in legs)  # há voos antes das 18h
    p2 = pattern("sab-manha")
    ins = latam.parse_offers(IN)
    assert all((l.dep.hour, l.dep.minute) <= (12, 0) for l in ins if latam.return_ok(l, p2))


def test_combine_roundtrip():
    c = cfg()
    trip = TripDates(date(2027, 1, 22), date(2027, 2, 6), pattern("sex-noite"))
    out, inn = latam.parse_offers(OUT), latam.parse_offers(IN)
    offers = latam.combine(out, inn, trip, "economy", c)
    assert offers
    best = offers[0]
    # Ida sexta a partir das 18h e volta sábado a partir das 18h.
    for o in offers:
        assert o.outbound_departure[11:13] >= "18"
        assert o.inbound_departure[11:13] >= "18"
        assert o.equivalent_brl == round(o.miles / 1000 * c.miles_value_per_thousand_brl
                                         + o.taxes_brl, 2)
        assert "redemption=true" in o.link and "trip=RT" in o.link
    assert offers == sorted(offers, key=lambda x: x.equivalent_brl)
    assert best.cabin == "economy" and best.source == "latam_pass"


def test_combine_respects_cabin():
    c = cfg()
    trip = TripDates(date(2027, 1, 22), date(2027, 2, 6), pattern("sex-noite"))
    offers = latam.combine(latam.parse_offers(OUT), latam.parse_offers(IN), trip, "business", c)
    assert all(o.cabin == "business" for o in offers)
    assert all(o.miles > 500_000 for o in offers)


def test_empty_response():
    assert latam.parse_offers({"content": []}) == []
    assert latam.parse_offers({}) == []
