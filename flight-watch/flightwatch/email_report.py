"""Monta o e-mail de alerta."""
from datetime import date
from html import escape

from .detect import Deal

CABIN_PT = {"economy": "Econômica", "business": "Executiva"}
WEEKDAY_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def brl(v: float | None) -> str:
    return "—" if v is None else "R$ " + f"{v:,.0f}".replace(",", ".")


def _d(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{WEEKDAY_PT[d.weekday()]} {d:%d/%m/%y}"


def subject(deals: list[Deal], origin: str, dest: str) -> str:
    best = min(deals, key=lambda d: d.obs.min_price)
    cabins = sorted({CABIN_PT[d.obs.cabin] for d in deals})
    return (f"✈️ {origin}⇄{dest}: {len(deals)} oferta(s) abaixo da média "
            f"({', '.join(cabins)}) a partir de {brl(best.obs.min_price)}")


def body(deals: list[Deal], origin: str, dest: str) -> tuple[str, str]:
    lines, rows = [], []
    for d in deals:
        o = d.obs
        top = o.offers[0] if o.offers else {}
        cias = ", ".join(top.get("airlines", []))
        stops = top.get("stops")
        dep = (top.get("outbound_departure") or "")[-5:]
        lines.append(
            f"- {CABIN_PT[o.cabin]} | {_d(o.outbound)} → {_d(o.inbound)} | {brl(o.min_price)} "
            f"(ref. {brl(d.baseline)}; {d.reason}) | {cias}, {stops} escala(s), saída {dep}\n  {o.url}")
        rows.append(
            "<tr>"
            f"<td>{CABIN_PT[o.cabin]}</td><td>{_d(o.outbound)} → {_d(o.inbound)}</td>"
            f"<td><b>{brl(o.min_price)}</b></td><td>{brl(d.baseline)}</td>"
            f"<td>{escape(d.reason)}</td><td>{escape(cias)}<br>{stops} escala(s), saída {dep}</td>"
            f"<td><a href=\"{escape(o.url)}\">ver</a></td></tr>")
    text = (f"Ofertas {origin}⇄{dest} abaixo da média (ida e volta, 1 adulto):\n\n"
            + "\n".join(lines)
            + "\n\nPreços do Google Flights no momento da busca; confira antes de comprar.")
    html = (
        f"<p>Ofertas <b>{origin}⇄{dest}</b> abaixo da média (ida e volta, 1 adulto):</p>"
        "<table border=1 cellpadding=6 cellspacing=0 style='border-collapse:collapse;font-family:sans-serif;font-size:14px'>"
        "<tr><th>Cabine</th><th>Datas</th><th>Preço</th><th>Referência</th><th>Motivo</th><th>Voo de ida</th><th></th></tr>"
        + "".join(rows) + "</table>"
        "<p style='color:#666;font-size:12px'>Preços do Google Flights no momento da busca; "
        "confira antes de comprar. Referência = mediana de preços da mesma cabine com ida em meses próximos.</p>")
    return text, html
