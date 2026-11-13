import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config.toml"


@dataclass(frozen=True)
class DatePattern:
    name: str
    outbound_weekday: int
    trip_days: int
    outbound_min_hour: int | None = None
    outbound_max_hour: int | None = None
    return_min_hour: int | None = None
    return_max_hour: int | None = None


@dataclass(frozen=True)
class Config:
    origin: str
    destination: str
    cabins: list[str]
    min_days_ahead: int
    max_days_ahead: int
    patterns: list[DatePattern] = field(default_factory=list)
    miles_value_per_thousand_brl: float = 25.0


def load(path: Path = DEFAULT_PATH) -> Config:
    raw = tomllib.loads(path.read_text())
    route = raw["route"]
    return Config(
        origin=route["origin"],
        destination=route["destination"],
        cabins=route["cabins"],
        min_days_ahead=route["min_days_ahead"],
        max_days_ahead=route["max_days_ahead"],
        patterns=[DatePattern(**p) for p in route["date_pattern"]],
        miles_value_per_thousand_brl=raw["miles"]["value_per_thousand_brl"],
    )
