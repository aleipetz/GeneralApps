"""Histórico de observações em arquivos JSONL (um por mês de coleta).

Cada linha é uma busca: rota, cabine, datas, menor preço e as melhores ofertas.
"""
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


@dataclass
class Observation:
    ts: str                 # quando foi coletado (UTC, ISO)
    source: str
    cabin: str
    outbound: str
    inbound: str
    pattern: str
    min_price: int | None   # None = busca sem resultado
    offers: list[dict]
    url: str
    error: str | None = None

    @property
    def key(self) -> str:
        return f"{self.source}|{self.cabin}|{self.outbound}|{self.inbound}"

    @property
    def collected(self) -> datetime:
        return datetime.fromisoformat(self.ts)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def append(data_dir: Path, observations: list[Observation]) -> Path:
    folder = data_dir / "cash"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now(timezone.utc):%Y-%m}.jsonl"
    with path.open("a") as f:
        for o in observations:
            f.write(json.dumps(o.__dict__, ensure_ascii=False) + "\n")
    return path


def load(data_dir: Path, since_days: int = 60) -> list[Observation]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    out: list[Observation] = []
    for path in sorted((data_dir / "cash").glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            o = Observation(**json.loads(line))
            if o.collected >= cutoff:
                out.append(o)
    return out


def load_state(data_dir: Path) -> dict:
    path = data_dir / "state.json"
    return json.loads(path.read_text()) if path.exists() else {}


def save_state(data_dir: Path, state: dict) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=1))


def months_apart(a: str, b: str) -> int:
    da, db = date.fromisoformat(a), date.fromisoformat(b)
    return abs((da.year - db.year) * 12 + da.month - db.month)
