# flight-watch

Monitor de preços de passagens GRU ⇄ BER (dinheiro e milhas LATAM Pass) que
avisa por e-mail quando aparece preço abaixo da média.

**Status: fase 0** — testando fontes de dados grátis.

- `config.toml` — rota, padrões de data (15 dias, sex-noite/sáb-manhã → sáb-noite/dom-manhã), cabines e valor do milheiro.
- `flightwatch/google_flights.py` — preço em dinheiro via Google Flights (biblioteca `fast-flights`, sem chave).
- `flightwatch/latam.py` — exploração do resgate com milhas no site da LATAM (Chromium headless).
- `flightwatch/probe.py` — roda uma amostra de buscas e gera `probe-out/report.json`.

Rodar localmente:

```bash
pip install -r requirements.txt && python -m playwright install chromium
python -m flightwatch.probe probe-out
```

No GitHub, o workflow `flight-watch probe` roda a cada push em `claude/**` que mexa nesta pasta.
