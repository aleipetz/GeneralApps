"""Relatório completo de uma varredura: tabela por data + CSV com todas as ofertas."""
import csv
import io
from collections import defaultdict
from datetime import date, timedelta, timezone
from html import escape
from statistics import median

from .detect import Deal
from .email_report import CABIN_PT, WEEKDAY_PT, brl
from .store import Observation

MONTH_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _d(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{WEEKDAY_PT[d.weekday()]} {d:%d/%m}"


def _flight(o: Observation) -> str:
    if not o.offers:
        return ""
    t = o.offers[0]
    stops = t.get("stops")
    esc = "direto" if stops == 0 else f"{stops} esc."
    return f"{', '.join(t.get('airlines', []))} · {esc} · sai {(t.get('outbound_departure') or '')[-5:]}"


def build(obs: list[Observation], deals: list[Deal], origin: str, dest: str,
          cabins: list[str]) -> tuple[str, str, str, bytes]:
    """Devolve (assunto, texto, html, csv)."""
    deal_keys = {d.obs.key: d for d in deals}
    by_pair: dict[tuple[str, str], dict[str, Observation]] = defaultdict(dict)
    for o in obs:
        by_pair[(o.outbound, o.inbound)][o.cabin] = o

    # menor preço de cada mês por cabine (destacado em verde)
    month_min: dict[tuple[str, str], int] = {}
    for o in obs:
        if o.min_price is not None:
            k = (o.outbound[:7], o.cabin)
            month_min[k] = min(month_min.get(k, o.min_price), o.min_price)

    priced = {c: [o for o in obs if o.cabin == c and o.min_price is not None] for c in cabins}
    best = {c: min(priced[c], key=lambda o: o.min_price) if priced[c] else None for c in cabins}
    failed = sum(1 for o in obs if o.error)
    empty = sum(1 for o in obs if o.min_price is None and not o.error)
    collected = ""
    if obs:  # horário de Brasília (UTC-3, sem horário de verão)
        brt = obs[0].collected.astimezone(timezone(timedelta(hours=-3)))
        collected = f"{brt:%d/%m/%Y %H:%M} (Brasília)"

    # ---------- resumo ----------
    summary_rows, summary_txt = [], []
    for c in cabins:
        b = best[c]
        prices = [o.min_price for o in priced[c]]
        med = median(prices) if prices else None
        line = (f"{CABIN_PT[c]}: mais barato {brl(b.min_price) if b else '—'}"
                + (f" ({_d(b.outbound)} → {_d(b.inbound)}, {_flight(b)})" if b else "")
                + f" · mediana {brl(med)} · {len(prices)} datas com preço")
        summary_txt.append(line)
        summary_rows.append(
            f"<tr><td><b>{CABIN_PT[c]}</b></td>"
            f"<td><b>{brl(b.min_price) if b else '—'}</b><br><small>"
            + (f"{_d(b.outbound)} → {_d(b.inbound)}<br>{escape(_flight(b))}" if b else "")
            + f"</small></td><td>{brl(med)}</td><td>{len(prices)}</td></tr>")

    # ---------- tabela por data ----------
    rows, txt_rows, current_month = [], [], None
    for (out, inb) in sorted(by_pair):
        month = out[:7]
        if month != current_month:
            current_month = month
            y, m = month.split("-")
            rows.append(f"<tr><td colspan={2 + len(cabins)} style='background:#eef;font-weight:bold'>"
                        f"{MONTH_PT[int(m) - 1]}/{y}</td></tr>")
            txt_rows.append(f"\n{MONTH_PT[int(m) - 1]}/{y}")
        cells, txt_cells = [], []
        for c in cabins:
            o = by_pair[(out, inb)].get(c)
            if o is None or o.min_price is None:
                msg = "erro" if (o and o.error) else "sem voos"
                cells.append(f"<td style='color:#999'>{msg}</td>")
                txt_cells.append(f"{CABIN_PT[c]}: {msg}")
                continue
            star = "★ " if o.key in deal_keys else ""
            green = month_min.get((month, c)) == o.min_price
            style = "background:#e6f6e6;" if green else ""
            note = f"<br><small style='color:#b60'>★ {escape(deal_keys[o.key].reason)}</small>" if star else ""
            cells.append(
                f"<td style='{style}'><a href=\"{escape(o.url)}\" style='color:inherit'>"
                f"<b>{star}{brl(o.min_price)}</b></a><br><small>{escape(_flight(o))}</small>{note}</td>")
            txt_cells.append(f"{CABIN_PT[c]}: {star}{brl(o.min_price)} ({_flight(o)})")
        pattern = next(iter(by_pair[(out, inb)].values())).pattern
        rows.append(f"<tr><td>{_d(out)} → {_d(inb)}<br><small style='color:#666'>{escape(pattern)}</small></td>"
                    + "".join(cells) + "</tr>")
        txt_rows.append(f"  {_d(out)} → {_d(inb)} | " + " | ".join(txt_cells))

    head = "".join(f"<th>{CABIN_PT[c]}</th>" for c in cabins)
    star_note = (f"<p>★ = abaixo da média ({len(deals)} encontrada(s)).</p>" if deals else
                 "<p>Nenhuma data abaixo da média nesta varredura (o histórico ainda está se formando).</p>")
    html = (
        "<div style='font-family:sans-serif;font-size:14px'>"
        f"<p>Varredura <b>{origin}⇄{dest}</b> · ida e volta · 1 adulto · coletado {collected}<br>"
        f"{len(obs)} buscas: {len(obs) - failed - empty} com preço, {empty} sem voos na janela, {failed} com erro.</p>"
        "<table border=1 cellpadding=6 cellspacing=0 style='border-collapse:collapse'>"
        "<tr><th>Cabine</th><th>Mais barato</th><th>Mediana</th><th>Datas</th></tr>"
        + "".join(summary_rows) + "</table>" + star_note +
        "<table border=1 cellpadding=6 cellspacing=0 style='border-collapse:collapse'>"
        f"<tr><th>Ida → Volta</th>{head}</tr>" + "".join(rows) + "</table>"
        "<p style='color:#666;font-size:12px'>Fundo verde = mais barato do mês na cabine. Clique no preço "
        "para abrir a busca no Google Flights. Preços no momento da coleta; o voo mostrado é o de ida "
        "(a volta respeita a janela de horário). Detalhes das 3 melhores opções por data no CSV anexo.</p></div>")
    text = (f"Varredura {origin}⇄{dest} · coletado {collected}\n"
            f"{len(obs)} buscas: {len(obs) - failed - empty} com preço, {empty} sem voos, {failed} com erro\n\n"
            + "\n".join(summary_txt) + "\n" + "\n".join(txt_rows) + "\n")

    cheapest = " · ".join(f"{CABIN_PT[c]} {brl(best[c].min_price)}" for c in cabins if best[c])
    subject = f"✈️ {origin}⇄{dest}: {cheapest}" + (f" · ★ {len(deals)} abaixo da média" if deals else "")
    return subject, text, html, to_csv(obs, deal_keys)


def to_csv(obs: list[Observation], deal_keys: dict) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["coletado_em", "cabine", "ida", "volta", "padrao", "opcao", "preco_brl",
                "companhias", "escalas", "saida_ida", "chegada_ida", "duracao_ida_min",
                "abaixo_da_media", "erro", "link"])
    for o in sorted(obs, key=lambda o: (o.outbound, o.cabin)):
        star = "sim" if o.key in deal_keys else ""
        if not o.offers:
            w.writerow([o.ts, CABIN_PT[o.cabin], o.outbound, o.inbound, o.pattern, "", "", "", "",
                        "", "", "", star, o.error or "sem voos", o.url])
        for i, of in enumerate(o.offers, 1):
            w.writerow([o.ts, CABIN_PT[o.cabin], o.outbound, o.inbound, o.pattern, i,
                        of.get("price_brl"), ", ".join(of.get("airlines", [])), of.get("stops"),
                        of.get("outbound_departure"), of.get("outbound_arrival"),
                        of.get("duration_min"), star if i == 1 else "", o.error or "", o.url])
    # BOM para o Excel reconhecer acentos
    return ("﻿" + buf.getvalue()).encode("utf-8")
