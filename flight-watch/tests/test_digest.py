from flightwatch import digest
from flightwatch.store import Observation


def o(cabin, out, price, error=None):
    offers = [] if price is None else [{"price_brl": price, "airlines": ["KLM"], "stops": 1,
                                         "outbound_departure": f"{out} 20:40"}]
    return Observation(ts="2026-11-13T10:17:00+00:00", source="google_flights", cabin=cabin,
                       outbound=out, inbound=out, pattern="p", min_price=price,
                       offers=offers, url="https://x", error=error)


def test_digest_has_every_date_and_csv():
    obs = [o("economy", "2027-01-22", 6865), o("business", "2027-01-22", 21354),
           o("economy", "2027-02-05", None), o("business", "2027-02-05", None, error="Timeout")]
    subj, text, html, csv_bytes = digest.build(obs, [], "GRU", "BER", ["economy", "business"])
    assert "R$ 6.865" in subj and "R$ 21.354" in subj
    assert "sem voos" in html and "erro" in html and "jan/2027" in html and "fev/2027" in html
    lines = csv_bytes.decode("utf-8-sig").strip().splitlines()
    assert len(lines) == 5  # cabeçalho + 4 buscas
