"""Varredura de preços em dinheiro + detecção + alerta por e-mail.

Uso: python -m flightwatch.sweep --data-dir data [--limit N] [--no-email]
"""
import argparse
import random
import time
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

from . import config, dates, detect, digest, email_report, google_flights, notify, store


def search_once(cfg, trip, cabin) -> store.Observation:
    url = google_flights.build_query(cfg.origin, cfg.destination, trip, cabin).url()
    error, offers = None, []
    for attempt in range(2):
        try:
            offers = google_flights.search(cfg.origin, cfg.destination, trip, cabin)
            error = None
            break
        except Exception as e:
            error = f"{type(e).__name__}: {e}"[:200]
            if attempt == 0:
                time.sleep(10)
    keep = [{k: v for k, v in o.to_dict().items() if k in (
        "price_brl", "airlines", "stops", "outbound_departure", "outbound_arrival",
        "duration_min")} for o in offers[:3]]
    return store.Observation(
        ts=store.now_iso(), source="google_flights", cabin=cabin,
        outbound=trip.outbound.isoformat(), inbound=trip.inbound.isoformat(),
        pattern=trip.pattern.name, min_price=offers[0].price_brl if offers else None,
        offers=keep, url=url, error=error)


def confirm(cfg, trips, deals: list[detect.Deal]) -> list[detect.Deal]:
    """Refaz a busca de cada oferta; descarta se o preço sumiu ou subiu mais de 3%."""
    by_date = {(t.outbound.isoformat(), t.inbound.isoformat()): t for t in trips}
    kept = []
    for d in deals:
        trip = by_date[(d.obs.outbound, d.obs.inbound)]
        again = search_once(cfg, trip, d.obs.cabin)
        ok = again.min_price is not None and again.min_price <= d.obs.min_price * 1.03
        print(f"  confirmação {d.obs.cabin} {d.obs.outbound}: "
              f"{email_report.brl(again.min_price)} -> {'ok' if ok else 'descartada'}")
        if ok:
            kept.append(d)
        time.sleep(random.uniform(*cfg.pause_seconds))
    return kept


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data", type=Path)
    ap.add_argument("--limit", type=int, default=0, help="só os N primeiros pares de datas")
    ap.add_argument("--no-email", action="store_true")
    args = ap.parse_args()

    cfg = config.load()
    trips = dates.trip_dates(cfg, date.today())
    if args.limit:
        trips = trips[: args.limit]
    jobs = [(t, c) for t in trips for c in cfg.cabins]
    print(f"Varredura: {len(trips)} pares de datas × {len(cfg.cabins)} cabines = {len(jobs)} buscas")

    current: list[store.Observation] = []
    for i, (trip, cabin) in enumerate(jobs, 1):
        obs = search_once(cfg, trip, cabin)
        current.append(obs)
        print(f"[{i}/{len(jobs)}] {obs.outbound}->{obs.inbound} {cabin:8} "
              f"{email_report.brl(obs.min_price):>10} {obs.error or ''}", flush=True)
        time.sleep(random.uniform(*cfg.pause_seconds))

    failed = sum(1 for o in current if o.error)
    empty = sum(1 for o in current if o.min_price is None and not o.error)
    print(f"Concluído: {len(current) - failed - empty} com preço, {empty} sem voos, {failed} com erro")

    history = store.load(args.data_dir, since_days=cfg.alerts.baseline_days + 5)
    store.append(args.data_dir, current)
    state = store.load_state(args.data_dir)

    deals = detect.find_deals(current, history + current, cfg.alerts)
    fresh = detect.filter_already_alerted(deals, state, cfg.alerts)
    print(f"Ofertas abaixo da média: {len(deals)} ({len(fresh)} novas)")
    fresh = confirm(cfg, trips, fresh)
    for d in fresh:
        print(f"  {d.obs.cabin} {d.obs.outbound}->{d.obs.inbound} "
              f"{email_report.brl(d.obs.min_price)} ref={email_report.brl(d.baseline)} ({d.reason})")

    sent = 0
    if cfg.report_mode == "digest" and not args.no_email:
        subj, text, html, csv_bytes = digest.build(current, deals, cfg.origin, cfg.destination, cfg.cabins)
        try:
            notify.send(subj, text, html, [(f"flight-watch-{date.today():%Y-%m-%d}.csv",
                                            csv_bytes, "text/csv")])
            print("E-mail com o relatório enviado.")
        except notify.EmailNotConfigured as e:
            print(f"E-mail não enviado: {e}")
    elif fresh and not args.no_email:
        text, html = email_report.body(fresh, cfg.origin, cfg.destination)
        try:
            notify.send(email_report.subject(fresh, cfg.origin, cfg.destination), text, html)
            detect.mark_alerted(fresh, state)
            sent = len(fresh)
            print("E-mail de alerta enviado.")
        except notify.EmailNotConfigured as e:
            print(f"E-mail não enviado: {e}")

    # Aviso de saúde: se metade das buscas falhou, provável bloqueio do Google.
    today = datetime.now(timezone.utc).date().isoformat()
    if jobs and failed / len(jobs) >= 0.5 and state.get("health_alert") != today and not args.no_email:
        try:
            notify.send("⚠️ flight-watch: muitas buscas falharam",
                        f"{failed} de {len(jobs)} buscas falharam na varredura de {today}. "
                        "Pode ser bloqueio do Google Flights ou mudança no site.")
            state["health_alert"] = today
        except Exception:
            traceback.print_exc()

    state["last_run"] = {"ts": store.now_iso(), "searches": len(jobs), "failed": failed,
                         "empty": empty, "deals": len(deals), "alerted": sent}
    store.save_state(args.data_dir, state)


if __name__ == "__main__":
    main()
