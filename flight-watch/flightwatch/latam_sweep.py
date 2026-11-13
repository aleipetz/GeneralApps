"""Varredura LATAM Pass: todos os pares de datas do config, nas duas cabines.

Uso (de dentro de flight-watch/):
    python -m flightwatch.latam_sweep [--part 1/2] [--limit N] [--push]

  --part K/N  faz só a fatia K de N dos pares de datas (ex.: 1/2 de manhã, 2/2 à noite)
  --limit N   só os N primeiros pares (teste rápido)
  --push      faz commit e push do arquivo de dados na branch claude/latam-local

Precisa do Chrome do projeto logado no LATAM Pass (python -m flightwatch.latam_browser).
Cada par de datas = uma busca ida e volta no site (lista de ida + lista de volta,
ambas com econômica e executiva), com pausas de alguns segundos entre buscas.

Saída: flight-watch/data/latam/AAAA-MM-DD.jsonl, uma linha por registro:
  {"kind": "offer", ...MilesOffer, "searched_at": ...}
  {"kind": "empty", "outbound_date", "inbound_date", "cabin", "pattern", "searched_at"}
  {"kind": "error", "outbound_date", "inbound_date", "error", "searched_at"}
Códigos de saída: 0 ok, 2 sessão do LATAM Pass expirada (refaça o login), 1 outro erro.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

from . import config, dates, latam, latam_browser

ROOT = Path(__file__).resolve().parent.parent          # flight-watch/
DATA = ROOT / "data" / "latam"
BRANCH = "claude/latam-local"


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def select(trips: list, part: str | None, limit: int | None) -> list:
    if part:
        k, n = (int(x) for x in part.split("/"))
        size = -(-len(trips) // n)
        trips = trips[(k - 1) * size: k * size]
    return trips[:limit] if limit else trips


def push(path: Path) -> None:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True,
                              capture_output=True).stdout.strip()

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != BRANCH:
        log(f"--push ignorado: branch atual é {branch}, não {BRANCH}")
        return
    git("add", str(path.relative_to(ROOT)))
    if not git("diff", "--cached", "--name-only"):
        log("nada novo para enviar")
        return
    git("commit", "-m", f"flight-watch: dados LATAM Pass {path.stem}")
    git("pull", "--rebase", "--autostash", "origin", BRANCH)
    git("push", "origin", BRANCH)
    log(f"push feito: {path.relative_to(ROOT)}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="latam_sweep")
    ap.add_argument("--part")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--pause", type=float, default=5.0, help="pausa média entre buscas (s)")
    a = ap.parse_args(argv)

    cfg = config.load()
    trips = select(dates.trip_dates(cfg, date.today()), a.part, a.limit)
    DATA.mkdir(parents=True, exist_ok=True)
    out_path = DATA / f"{date.today().isoformat()}.jsonl"
    log(f"{len(trips)} pares de datas -> {out_path.relative_to(ROOT)}")

    from playwright.sync_api import sync_playwright

    t0 = time.time()
    n_offers = n_errors = 0
    code = 0

    def error(fh, trip, msg: str) -> None:
        nonlocal n_errors
        n_errors += 1
        log(f"erro {trip.outbound}->{trip.inbound}: {msg}"[:200])
        fh.write(json.dumps({"kind": "error", "outbound_date": trip.outbound.isoformat(),
                             "inbound_date": trip.inbound.isoformat(), "error": msg[:300],
                             "searched_at": datetime.now().isoformat(timespec="seconds")},
                            ensure_ascii=False) + "\n")

    latam_browser.ensure_running(minimized=True)
    with sync_playwright() as pw, out_path.open("a", encoding="utf-8") as fh:
        page = latam_browser.connect(pw)
        try:
            for i, trip in enumerate(trips, 1):
                if i > 1:
                    time.sleep(a.pause + random.uniform(-0.4, 0.8) * a.pause)
                try:
                    out_body, in_body = latam.fetch_roundtrip(page, cfg.origin,
                                                              cfg.destination, trip)
                except latam.LoginRequired:
                    raise
                except Exception as e:
                    error(fh, trip, f"{type(e).__name__}: {e}")
                    continue
                out_l = latam.parse_offers(out_body)
                in_l = latam.parse_offers(in_body) if in_body is not None else []
                if out_l and in_body is None:
                    error(fh, trip, "não consegui abrir a lista de volta")
                    continue
                now = datetime.now().isoformat(timespec="seconds")
                summary = []
                for cabin in cfg.cabins:
                    offers = latam.combine(out_l, in_l, trip, cabin, cfg)
                    for o in offers:
                        fh.write(json.dumps({"kind": "offer", **o.to_dict(), "searched_at": now},
                                            ensure_ascii=False) + "\n")
                    if not offers:
                        fh.write(json.dumps({"kind": "empty", "cabin": cabin,
                                             "pattern": trip.pattern.name,
                                             "outbound_date": trip.outbound.isoformat(),
                                             "inbound_date": trip.inbound.isoformat(),
                                             "searched_at": now}) + "\n")
                    n_offers += len(offers)
                    summary.append(f"{cabin}={offers[0].miles:,} mi + R${offers[0].taxes_brl:.0f}"
                                   if offers else f"{cabin}=-")
                fh.flush()
                log(f"{i}/{len(trips)} {trip.outbound}->{trip.inbound} " + " ".join(summary))
        except latam.LoginRequired:
            log("SESSÃO EXPIRADA: rode `python -m flightwatch.latam_browser` e faça login no LATAM Pass")
            code = 2

    mins = (time.time() - t0) / 60
    log(f"fim: {len(trips)} pares, {n_offers} ofertas, {n_errors} erros, {mins:.1f} min")
    if a.push and n_offers:
        try:
            push(out_path)
        except subprocess.CalledProcessError as e:
            log(f"push falhou: {e.stderr.strip()[:300]}")
            code = code or 1
    return code


if __name__ == "__main__":
    sys.exit(main())
