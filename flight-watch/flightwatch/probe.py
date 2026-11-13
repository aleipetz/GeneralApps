"""Fase 0: testa as fontes grátis com poucas buscas e imprime um resumo.

Uso: python -m flightwatch.probe [saida/] [--latam-only]
"""
import json
import sys
import time
import traceback
from datetime import date
from pathlib import Path

from . import config, dates, google_flights, latam


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    latam_only = "--latam-only" in sys.argv
    outdir = Path(args[0] if args else "probe-out")
    outdir.mkdir(parents=True, exist_ok=True)
    cfg = config.load()
    trips = dates.trip_dates(cfg, date.today())
    print(f"{len(trips)} pares de datas na janela; "
          f"{len(trips) * len(cfg.cabins)} buscas por varredura completa")

    # Amostra: ~1, 3 e 6 meses à frente, um de cada padrão.
    sample = [trips[i] for i in (2, 3, 16, 17, 46) if i < len(trips)]
    report = {"google_flights": [], "latam": []}

    for t in ([] if latam_only else sample):
        for cabin in cfg.cabins:
            t0 = time.time()
            try:
                offers = google_flights.search(cfg.origin, cfg.destination, t, cabin)
                err = None
            except Exception as e:
                offers, err = [], f"{type(e).__name__}: {e}"[:300]
                traceback.print_exc()
            row = {"outbound": str(t.outbound), "inbound": str(t.inbound),
                   "pattern": t.pattern.name, "cabin": cabin, "n": len(offers),
                   "seconds": round(time.time() - t0, 1), "error": err,
                   "top3": [o.to_dict() for o in offers[:3]]}
            report["google_flights"].append(row)
            best = offers[0] if offers else None
            print(f"[GF] {t.outbound}->{t.inbound} {cabin:8} n={len(offers):3} "
                  f"min=R${best.price_brl if best else '-'} "
                  f"{(best.airlines, best.stops, best.outbound_departure) if best else err}")
            time.sleep(2)

    for cabin in cfg.cabins:
        try:
            s = latam.probe(cfg.origin, cfg.destination, sample[2], cabin, outdir)
        except Exception as e:
            s = {"cabin": cabin, "error": f"{type(e).__name__}: {e}"[:300]}
            traceback.print_exc()
        report["latam"].append(s)
        print(f"[LATAM] {cabin}: title={s.get('title')!r} error={s.get('error')}")
        for r in s.get("responses", [])[:40]:
            print("   ", r)

    (outdir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
