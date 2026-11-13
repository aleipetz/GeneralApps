from dataclasses import dataclass
from datetime import date, timedelta

from .config import Config, DatePattern


@dataclass(frozen=True)
class TripDates:
    outbound: date
    inbound: date
    pattern: DatePattern


def trip_dates(cfg: Config, today: date) -> list[TripDates]:
    """Todos os pares (ida, volta) dentro da janela, em ordem de data."""
    start = today + timedelta(days=cfg.min_days_ahead)
    end = today + timedelta(days=cfg.max_days_ahead)
    out: list[TripDates] = []
    for p in cfg.patterns:
        d = start + timedelta(days=(p.outbound_weekday - start.weekday()) % 7)
        while d + timedelta(days=p.trip_days) <= end:
            out.append(TripDates(d, d + timedelta(days=p.trip_days), p))
            d += timedelta(days=7)
    return sorted(out, key=lambda t: t.outbound)
