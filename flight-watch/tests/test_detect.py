from datetime import datetime, timedelta, timezone

from flightwatch import detect
from flightwatch.config import AlertRules
from flightwatch.store import Observation

NOW = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)
RULES = AlertRules(min_baseline_samples=5, absolute_max_brl={"economy": 4500})


def obs(price, outbound="2027-01-22", cabin="economy", days_ago=0, inbound=None):
    ts = (NOW - timedelta(days=days_ago)).isoformat()
    return Observation(ts=ts, source="google_flights", cabin=cabin, outbound=outbound,
                       inbound=inbound or outbound.replace("-22", "-29"), pattern="p",
                       min_price=price, offers=[], url="u")


def history():
    # 6 datas diferentes em janeiro, ~R$ 7.000
    return [obs(7000 + i * 100, outbound=f"2027-01-{10 + i:02d}", days_ago=1) for i in range(6)]


def test_deal_below_baseline():
    cur = obs(5200)
    deals = detect.find_deals([cur], history() + [cur], RULES, NOW)
    assert len(deals) == 1 and deals[0].pct_below > 0.2


def test_normal_price_no_deal():
    cur = obs(7100)
    assert detect.find_deals([cur], history() + [cur], RULES, NOW) == []


def test_absolute_threshold_without_history():
    cur = obs(4300)
    deals = detect.find_deals([cur], [cur], RULES, NOW)
    assert len(deals) == 1 and deals[0].baseline is None


def test_other_cabin_and_far_months_ignored():
    hist = [obs(30000, cabin="business", outbound=f"2027-01-{10 + i:02d}") for i in range(6)]
    hist += [obs(3000, outbound=f"2027-06-{10 + i:02d}") for i in range(6)]
    base, n = detect.baseline_for(obs(7000), hist, RULES, NOW)
    assert base is None and n == 0


def test_old_history_ignored():
    hist = [obs(7000, outbound=f"2027-01-{10 + i:02d}", days_ago=60) for i in range(6)]
    assert detect.baseline_for(obs(5000), hist, RULES, NOW) == (None, 0)


def test_realert_only_on_further_drop():
    cur = obs(5200)
    deals = detect.find_deals([cur], history() + [cur], RULES, NOW)
    state = {}
    detect.mark_alerted(deals, state)
    assert detect.filter_already_alerted(deals, state, RULES) == []
    cheaper = obs(4900)
    d2 = detect.find_deals([cheaper], history() + [cheaper], RULES, NOW)
    assert detect.filter_already_alerted(d2, state, RULES) == d2


def test_other_pattern_ignored():
    hist = [obs(15000, outbound=f"2027-01-{10 + i:02d}") for i in range(6)]
    for h in hist:
        h.pattern = "sab-manha"
    assert detect.baseline_for(obs(7000), hist, RULES, NOW) == (None, 0)
