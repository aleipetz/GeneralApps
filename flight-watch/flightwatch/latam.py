"""Resgate com milhas LATAM Pass, lido do próprio site da LATAM.

Não há API pública. O site (com login no LATAM Pass) chama
    GET https://www.latamairlines.com/bff/air-offers/v2/offers/search/redemption
com tokens de sessão e de reCAPTCHA gerados pela página, então não chamamos a
API diretamente: abrimos a página de busca num Chrome comum já logado
(ver latam_browser.py) e lemos a resposta JSON que a própria página recebe.

Formato da resposta (resumo): {"content": [{"summary": {...}, "itinerary": [...]}]}
  summary.origin/destination.departure|arrival  ISO local, ex. "2027-01-22T23:35:00"
  summary.stopOvers                              número de escalas
  summary.flightOperators                        ["LATAM Airlines Brasil", "Iberia"]
  summary.brands[]                               tarifas (KM/SL/KD econômica, EV/EJ executiva)
      .cabin.label        "Economy" | "Business" (| "Premium Economy")
      .price.amount       milhas (currency LOYALTY_POINTS)
      .taxes.amount       taxas em R$
      .seatsRemaining.count
  itinerary[]                                    trechos (voo, operadora, horários)

Fluxo ida e volta (como no site), duas respostas por par de datas:
  1. abrir a busca RT → resposta com os voos de IDA (outOfferId=null)
  2. abrir um voo de ida e clicar "Escolher" numa tarifa → resposta com os
     voos de VOLTA (outOfferId=<oferta escolhida>)
Os preços são por trecho: a volta vem com as mesmas milhas e taxas qualquer que
seja a ida escolhida (conferido em 13/11/2026), então total = ida + volta.
Atenção: buscar cada trecho como "só ida" (trip=OW) sai ~35-50% mais caro.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

from .config import Config, DatePattern
from .dates import TripDates

CABIN = {"economy": "Economy", "business": "Business"}
OFFERS_API = "/bff/air-offers/v2/offers/search/redemption"


class LoginRequired(RuntimeError):
    """O site mandou para a tela de login: a sessão do LATAM Pass expirou."""


# ---------------------------------------------------------------- URLs

def _iso(d: date) -> str:
    return f"{d.isoformat()}T12%3A00%3A00.000Z"


def search_url(origin: str, destination: str, trip: TripDates, cabin: str) -> str:
    """Link da busca ida e volta com milhas (para mostrar no alerta)."""
    return (
        "https://www.latamairlines.com/br/pt/oferta-voos"
        f"?origin={origin}&destination={destination}"
        f"&outbound={_iso(trip.outbound)}&inbound={_iso(trip.inbound)}"
        f"&adt=1&chd=0&inf=0&trip=RT&cabin={CABIN[cabin]}"
        "&redemption=true&sort=RECOMMENDED"
    )


def oneway_url(origin: str, destination: str, day: date, cabin: str = "economy") -> str:
    """Busca só ida com milhas. A resposta traz todas as cabines disponíveis."""
    return (
        "https://www.latamairlines.com/br/pt/oferta-voos"
        f"?origin={origin}&destination={destination}&outbound={_iso(day)}"
        f"&adt=1&chd=0&inf=0&trip=OW&cabin={CABIN[cabin]}"
        "&redemption=true&sort=RECOMMENDED"
    )


# ---------------------------------------------------------------- parser

@dataclass(frozen=True)
class Leg:
    """Um trecho (ida ou volta) com a tarifa mais barata de uma cabine."""
    origin: str
    destination: str
    departure: str          # ISO local "2027-01-22T23:35:00"
    arrival: str
    stops: int
    flights: tuple[str, ...]        # ("LA8070", "LA1540")
    airlines: tuple[str, ...]       # operadoras, ex. ("LATAM Airlines Brasil", "Iberia")
    cabin: str                      # "economy" | "business"
    brand: str                      # ex. "KM", "EV"
    miles: int
    taxes_brl: float
    seats: int | None

    @property
    def dep(self) -> datetime:
        return datetime.fromisoformat(self.departure)


def _cabin_key(label: str | None) -> str | None:
    label = (label or "").lower()
    if label == "economy":
        return "economy"
    if label == "business":
        return "business"
    return None  # premium economy etc. ficam de fora


def parse_offers(body: dict) -> list[Leg]:
    """Converte a resposta da API em trechos, um por (itinerário, cabine).

    Para cada itinerário fica só a tarifa mais barata de cada cabine.
    Itinerários repetidos (mesmo voo e horários) são unificados.
    """
    seen: dict[tuple, Leg] = {}
    for item in body.get("content") or []:
        s = item.get("summary") or {}
        itin = item.get("itinerary") or []
        flights = tuple(
            f"{seg['flight']['airlineCode']}{seg['flight']['flightNumber']}" for seg in itin
        ) or (s.get("flightCode", ""),)
        airlines = tuple(s.get("flightOperators") or ())
        best: dict[str, dict] = {}
        for b in s.get("brands") or []:
            cab = _cabin_key((b.get("cabin") or {}).get("label"))
            price = b.get("price") or {}
            if not cab or price.get("currency") != "LOYALTY_POINTS":
                continue
            if cab not in best or price["amount"] < best[cab]["price"]["amount"]:
                best[cab] = b
        for cab, b in best.items():
            leg = Leg(
                origin=s["origin"]["iataCode"],
                destination=s["destination"]["iataCode"],
                departure=s["origin"]["departure"],
                arrival=s["destination"]["arrival"],
                stops=int(s.get("stopOvers") or 0),
                flights=flights,
                airlines=airlines,
                cabin=cab,
                brand=b.get("id", ""),
                miles=int(b["price"]["amount"]),
                taxes_brl=float((b.get("taxes") or {}).get("amount") or 0.0),
                seats=(b.get("seatsRemaining") or {}).get("count"),
            )
            key = (leg.flights, leg.departure, leg.arrival, cab)
            if key not in seen or leg.miles < seen[key].miles:
                seen[key] = leg
    return sorted(seen.values(), key=lambda l: (l.cabin, l.miles, l.taxes_brl))


# ---------------------------------------------------------------- regras de horário

def _minutes(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def outbound_ok(leg: Leg, p: DatePattern) -> bool:
    t = _minutes(leg.dep)
    if p.outbound_min_hour is not None and t < p.outbound_min_hour * 60:
        return False
    if p.outbound_max_hour is not None and t > p.outbound_max_hour * 60:
        return False
    return True


def return_ok(leg: Leg, p: DatePattern) -> bool:
    t = _minutes(leg.dep)
    if p.return_min_hour is not None and t < p.return_min_hour * 60:
        return False
    if p.return_max_hour is not None and t > p.return_max_hour * 60:
        return False
    return True


# ---------------------------------------------------------------- ofertas ida e volta

@dataclass(frozen=True)
class MilesOffer:
    source: str
    cabin: str
    pattern: str
    outbound_date: str
    inbound_date: str
    outbound_departure: str
    outbound_arrival: str
    inbound_departure: str
    inbound_arrival: str
    outbound_flights: list[str]
    inbound_flights: list[str]
    airlines: list[str]
    outbound_stops: int
    inbound_stops: int
    stops: int                  # máximo de escalas entre ida e volta
    miles: int
    taxes_brl: float
    value_per_thousand_brl: float
    equivalent_brl: float       # milhas/1000 × milheiro + taxas
    seats: int | None
    link: str

    def to_dict(self) -> dict:
        return asdict(self)


def combine(out_legs: list[Leg], in_legs: list[Leg], trip: TripDates, cabin: str,
            cfg: Config, top: int = 3) -> list[MilesOffer]:
    """Junta ida e volta dentro das janelas de horário; devolve as `top` mais baratas."""
    v = cfg.miles_value_per_thousand_brl
    outs = [l for l in out_legs if l.cabin == cabin and outbound_ok(l, trip.pattern)]
    ins = [l for l in in_legs if l.cabin == cabin and return_ok(l, trip.pattern)]

    def cost(l: Leg) -> float:
        return l.miles / 1000 * v + l.taxes_brl

    outs = sorted(outs, key=cost)[:top]
    ins = sorted(ins, key=cost)[:top]
    link = search_url(cfg.origin, cfg.destination, trip, cabin)
    offers = []
    for o in outs:
        for i in ins:
            miles = o.miles + i.miles
            taxes = round(o.taxes_brl + i.taxes_brl, 2)
            seats = [s for s in (o.seats, i.seats) if s is not None]
            offers.append(MilesOffer(
                source="latam_pass", cabin=cabin, pattern=trip.pattern.name,
                outbound_date=trip.outbound.isoformat(), inbound_date=trip.inbound.isoformat(),
                outbound_departure=o.departure, outbound_arrival=o.arrival,
                inbound_departure=i.departure, inbound_arrival=i.arrival,
                outbound_flights=list(o.flights), inbound_flights=list(i.flights),
                airlines=sorted(set(o.airlines) | set(i.airlines)),
                outbound_stops=o.stops, inbound_stops=i.stops, stops=max(o.stops, i.stops),
                miles=miles, taxes_brl=taxes, value_per_thousand_brl=v,
                equivalent_brl=round(miles / 1000 * v + taxes, 2),
                seats=min(seats) if seats else None, link=link,
            ))
    return sorted(offers, key=lambda x: x.equivalent_brl)[:top]


# ---------------------------------------------------------------- busca no navegador

def _is_outbound(r) -> bool:
    return OFFERS_API in r.url and r.request.method == "GET" and "outOfferId=null" in r.url


def _is_inbound(r) -> bool:
    return OFFERS_API in r.url and r.request.method == "GET" and "outOfferId=null" not in r.url


def _check_login(page) -> None:
    if "/login" in page.url or "auth.latamairlines.com" in page.url:
        raise LoginRequired(page.url[:120])


def _dismiss_cookies(page) -> None:
    """Recusa cookies opcionais se o aviso aparecer (ele bloqueia os cliques)."""
    btn = page.locator("[data-testid=cookies-politics-reject-button--button]")
    try:
        if btn.is_visible():
            btn.click(timeout=5_000)
    except Exception:
        pass


def _candidates(out_body: dict, max_tries: int) -> list[int]:
    """Índices de voos de ida para clicar: os de econômica mais barata primeiro."""
    scored = []
    for i, item in enumerate(out_body.get("content") or []):
        brands = (item.get("summary") or {}).get("brands") or []
        if brands and _cabin_key((brands[0].get("cabin") or {}).get("label")) == "economy":
            scored.append((brands[0]["price"]["amount"], i))
    return [i for _, i in sorted(scored)][:max_tries]


def fetch_roundtrip(page, origin: str, destination: str, trip: TripDates,
                    timeout_ms: int = 60_000, max_tries: int = 3) -> tuple[dict, dict | None]:
    """Faz o fluxo ida e volta no Chrome logado. Devolve (JSON da ida, JSON da volta).

    `page` é uma página Playwright conectada ao Chrome do projeto
    (latam_browser.connect()). A volta é None se nenhuma ida tentada deu certo.
    """
    url = search_url(origin, destination, trip, "economy")
    out_body: dict | None = None
    tries: list[int] | None = None
    for attempt in range(max_tries):
        try:
            with page.expect_response(_is_outbound, timeout=timeout_ms) as info:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception:
            _check_login(page)
            raise
        resp = info.value
        if resp.status != 200:
            raise RuntimeError(f"LATAM respondeu {resp.status} na ida ({url})")
        body = resp.json()
        out_body = out_body or body
        if tries is None:
            tries = _candidates(body, max_tries)
        if attempt >= len(tries):
            break
        idx = tries[attempt]
        _dismiss_cookies(page)
        try:
            page.locator(f"[data-testid=wrapper-card-flight-{idx}]").click(timeout=15_000)
            with page.expect_response(_is_inbound, timeout=timeout_ms) as info:
                page.locator(f"[data-testid=brand-selection-card-{idx}-0-select]").click(
                    timeout=15_000)
        except Exception:
            _check_login(page)
            continue
        if info.value.status == 200:
            return out_body, info.value.json()
    return out_body or {}, None


def search(cfg: Config, trip: TripDates, cabin: str, page) -> list[MilesOffer]:
    """Ofertas ida e volta de um par de datas e uma cabine."""
    out_body, in_body = fetch_roundtrip(page, cfg.origin, cfg.destination, trip)
    if in_body is None:
        return []
    return combine(parse_offers(out_body), parse_offers(in_body), trip, cabin, cfg)


# ---------------------------------------------------------------- probe (fase 0)

def probe(origin: str, destination: str, trip: TripDates, cabin: str, outdir: Path) -> dict:
    """Usado por `python -m flightwatch.probe`: tenta uma busca e resume o resultado.

    Usa o Chrome do projeto (logado à mão uma vez no LATAM Pass).
    """
    from playwright.sync_api import sync_playwright

    from . import latam_browser

    summary = {"url": search_url(origin, destination, trip, cabin), "cabin": cabin,
               "responses": [], "error": None}
    try:
        latam_browser.ensure_running()
        with sync_playwright() as pw:
            page = latam_browser.connect(pw)
            out_body, in_body = fetch_roundtrip(page, origin, destination, trip)
            summary["title"] = page.title()
            summary["n_outbound"] = len([l for l in parse_offers(out_body) if l.cabin == cabin])
            summary["n_inbound"] = len([l for l in parse_offers(in_body or {}) if l.cabin == cabin])
            (outdir / f"latam_{cabin}_responses.json").write_text(
                json.dumps({"outbound": out_body, "inbound": in_body}, ensure_ascii=False,
                           indent=1), encoding="utf-8")
    except Exception as e:
        summary["error"] = f"{type(e).__name__}: {e}"[:300]
    return summary
