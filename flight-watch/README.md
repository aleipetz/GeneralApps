# flight-watch

Monitor de preços de passagens GRU ⇄ BER que avisa por e-mail quando aparece
preço abaixo da média. Fase atual: **preço em dinheiro** (Google Flights).
Milhas LATAM Pass estão em teste à parte (o site da LATAM bloqueia servidores
de nuvem, então essa coleta vai rodar num computador pessoal).

## Como funciona

1. **Varredura** (`flightwatch/sweep.py`), 2x por dia no GitHub Actions
   (`.github/workflows/flight-watch.yml`): para cada par de datas do
   `config.toml` (viagens de 15 dias, sex-noite→sáb-noite e sáb-manhã→dom-manhã,
   de 2 semanas a ~11 meses à frente) e cada cabine (econômica e executiva),
   busca o menor preço de ida e volta no Google Flights respeitando as janelas
   de horário. São 174 buscas, que levam ~15 min.
2. **Histórico**: cada busca vira uma linha em `data/cash/AAAA-MM.jsonl`, guardada
   na branch `flight-watch-data` (separada do código).
3. **Detecção** (`flightwatch/detect.py`): referência = mediana dos menores preços
   da mesma cabine, com ida no mesmo mês ±1, coletados nos últimos 30 dias.
   Alerta se o preço está ≥20% abaixo da referência ou abaixo de um teto fixo
   (econômica R$ 4.500, executiva R$ 13.000). Cada oferta é confirmada com uma
   segunda busca, e a mesma data só gera alerta de novo se cair mais 5%.
4. **E-mail** (`flightwatch/notify.py`) pelo Gmail, com os secrets
   `GMAIL_APP_PASSWORD` e `ALERT_EMAIL`. Se metade das buscas falhar, chega um
   e-mail de aviso.

Os limites ficam em `config.toml`, seção `[alerts]`.

## Rodar localmente

```bash
pip install -r requirements.txt
python -m flightwatch.sweep --data-dir data --limit 3 --no-email
```

Outros comandos: `python -m flightwatch.notify` (e-mail de teste),
`python -m flightwatch.probe` (teste das fontes, inclusive LATAM).
