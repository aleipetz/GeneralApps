"""Decide quais preços estão abaixo da média e merecem alerta."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import median

from .config import AlertRules
from .store import Observation, months_apart


@dataclass
class Deal:
    obs: Observation
    baseline: float | None      # mediana de referência (R$)
    samples: int                # quantas observações formam a referência
    pct_below: float | None     # 0.25 = 25% abaixo da referência
    reason: str


def baseline_for(obs: Observation, history: list[Observation], rules: AlertRules,
                 now: datetime | None = None) -> tuple[float | None, int]:
    """Mediana dos menores preços da mesma cabine, ida em mês próximo, coletados
    nos últimos `baseline_days`. Usa o último preço de cada par de datas por dia,
    para que datas muito buscadas não pesem mais."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=rules.baseline_days)
    latest: dict[tuple[str, str], int] = {}
    for h in history:
        if (h.min_price is None or h.cabin != obs.cabin or h.source != obs.source
                or h.collected < cutoff
                or months_apart(h.outbound, obs.outbound) > rules.season_months):
            continue
        latest[(h.key, h.ts[:10])] = h.min_price
    prices = list(latest.values())
    if len(prices) < rules.min_baseline_samples:
        return None, len(prices)
    return float(median(prices)), len(prices)


def find_deals(current: list[Observation], history: list[Observation], rules: AlertRules,
               now: datetime | None = None) -> list[Deal]:
    deals = []
    for obs in current:
        if obs.min_price is None:
            continue
        base, n = baseline_for(obs, history, rules, now)
        pct = (1 - obs.min_price / base) if base else None
        absolute = rules.absolute_max_brl.get(obs.cabin)
        if pct is not None and pct >= rules.pct_below_baseline:
            deals.append(Deal(obs, base, n, pct, f"{pct:.0%} abaixo da mediana"))
        elif absolute and obs.min_price <= absolute:
            deals.append(Deal(obs, base, n, pct, f"abaixo de R$ {absolute:,}".replace(",", ".")))
    return sorted(deals, key=lambda d: (d.obs.cabin, -(d.pct_below or 0), d.obs.min_price))


def filter_already_alerted(deals: list[Deal], state: dict, rules: AlertRules) -> list[Deal]:
    """Remove ofertas já avisadas, a não ser que o preço tenha caído mais."""
    alerted = state.get("alerted", {})
    fresh = []
    for d in deals:
        prev = alerted.get(d.obs.key)
        if prev is None or d.obs.min_price <= prev["price"] * (1 - rules.realert_drop):
            fresh.append(d)
    return fresh


def mark_alerted(deals: list[Deal], state: dict) -> None:
    alerted = state.setdefault("alerted", {})
    for d in deals:
        alerted[d.obs.key] = {"price": d.obs.min_price, "ts": d.obs.ts}
    # esquece datas que já passaram
    today = datetime.now(timezone.utc).date().isoformat()
    for k in [k for k in alerted if k.split("|")[2] < today]:
        del alerted[k]
