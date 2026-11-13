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
    pause_seconds: tuple[float, float] = (2.0, 5.0)
    alerts: "AlertRules" = None  # type: ignore[assignment]


@dataclass(frozen=True)
class AlertRules:
    pct_below_baseline: float = 0.20
    baseline_days: int = 30
    season_months: int = 1
    min_baseline_samples: int = 8
    realert_drop: float = 0.05
    absolute_max_brl: dict[str, int] = field(default_factory=dict)


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
        pause_seconds=tuple(raw.get("sweep", {}).get("pause_seconds", (2.0, 5.0))),
        alerts=AlertRules(**raw.get("alerts", {})),
    )
