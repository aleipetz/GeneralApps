"""Exploração: resgate com milhas LATAM Pass no site da LATAM.

Não há API pública. Abrimos a busca com "usar milhas" num Chromium headless e
guardamos as respostas JSON que o próprio site recebe, para descobrir o formato.
"""
import json
import os
from pathlib import Path

from .dates import TripDates

CABIN = {"economy": "Economy", "business": "Business"}


def search_url(origin: str, destination: str, trip: TripDates, cabin: str) -> str:
    return (
        "https://www.latamairlines.com/br/pt/oferta-voos"
        f"?origin={origin}&destination={destination}"
        f"&outbound={trip.outbound.isoformat()}T12%3A00%3A00.000Z"
        f"&inbound={trip.inbound.isoformat()}T12%3A00%3A00.000Z"
        f"&adt=1&chd=0&inf=0&trip=RT&cabin={CABIN[cabin]}"
        "&redemption=true&sort=RECOMMENDED"
    )


def probe(origin: str, destination: str, trip: TripDates, cabin: str, outdir: Path) -> dict:
    from playwright.sync_api import sync_playwright

    url = search_url(origin, destination, trip, cabin)
    captured: list[dict] = []
    summary = {"url": url, "cabin": cabin, "responses": [], "error": None}

    def on_response(resp):
        ct = resp.headers.get("content-type", "")
        entry = {"url": resp.url[:200], "status": resp.status}
        if "latam" in resp.url and "json" in ct:
            summary["responses"].append(entry)
            try:
                captured.append({"url": resp.url, "status": resp.status, "body": resp.json()})
            except Exception as e:  # corpo vazio ou não-JSON
                entry["parse_error"] = str(e)[:100]

    with sync_playwright() as pw:
        # LATAM_HEADED=1 abre uma janela visível (menos chance de bloqueio anti-bot).
        browser = pw.chromium.launch(headless=os.environ.get("LATAM_HEADED") != "1")
        page = browser.new_page(locale="pt-BR", user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"))
        page.on("response", on_response)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(25_000)
            summary["title"] = page.title()
            page.screenshot(path=str(outdir / f"latam_{cabin}.png"), full_page=True)
            (outdir / f"latam_{cabin}.html").write_text(page.content())
        except Exception as e:
            summary["error"] = f"{type(e).__name__}: {e}"[:300]
        browser.close()

    (outdir / f"latam_{cabin}_responses.json").write_text(
        json.dumps(captured, ensure_ascii=False, indent=1)[:5_000_000])
    return summary
