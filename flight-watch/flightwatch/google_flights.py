"""Preços em dinheiro via Google Flights (scraping com fast-flights, sem chave)."""
from dataclasses import asdict, dataclass

from fast_flights import FlightQuery, FlightsNotFound, create_query, get_flights

from .dates import TripDates


@dataclass
class CashOffer:
    source: str
    cabin: str
    outbound: str
    inbound: str
    pattern: str
    price_brl: int
    airlines: list[str]
    stops: int
    outbound_departure: str
    outbound_arrival: str
    duration_min: int
    url: str

    def to_dict(self) -> dict:
        return asdict(self)


def _hhmm(dt) -> str:
    y, m, d = dt.date
    return f"{y:04d}-{m:02d}-{d:02d} {dt.time[0]:02d}:{dt.time[1]:02d}"


def build_query(origin: str, destination: str, trip: TripDates, cabin: str):
    p = trip.pattern
    return create_query(
        flights=[
            FlightQuery(
                date=trip.outbound.isoformat(),
                from_airport=origin,
                to_airport=destination,
                earliest_departure_hour=p.outbound_min_hour,
                latest_departure_hour=p.outbound_max_hour,
            ),
            FlightQuery(
                date=trip.inbound.isoformat(),
                from_airport=destination,
                to_airport=origin,
                earliest_departure_hour=p.return_min_hour,
                latest_departure_hour=p.return_max_hour,
            ),
        ],
        seat=cabin,
        trip="round-trip",
        language="pt-BR",
        currency="BRL",
    )


def search(origin: str, destination: str, trip: TripDates, cabin: str) -> list[CashOffer]:
    """Opções de ida (com preço total de ida e volta) que respeitam as janelas de horário."""
    q = build_query(origin, destination, trip, cabin)
    try:
        results = get_flights(q)
    except FlightsNotFound:
        return []
    offers = []
    for r in results:
        if not r.flights or not r.price:
            continue
        first, last = r.flights[0], r.flights[-1]
        offers.append(
            CashOffer(
                source="google_flights",
                cabin=cabin,
                outbound=trip.outbound.isoformat(),
                inbound=trip.inbound.isoformat(),
                pattern=trip.pattern.name,
                price_brl=r.price,
                airlines=list(r.airlines),
                stops=len(r.flights) - 1,
                outbound_departure=_hhmm(first.departure),
                outbound_arrival=_hhmm(last.arrival),
                duration_min=sum(f.duration or 0 for f in r.flights),
                url=q.url(),
            )
        )
    return sorted(offers, key=lambda o: o.price_brl)
