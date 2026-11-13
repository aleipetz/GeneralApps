# Coletor LATAM Pass (roda no computador de casa)

O site da LATAM bloqueia os servidores do GitHub ("Access Denied"), e a busca com
milhas exige login no LATAM Pass. Por isso esta parte roda no computador de casa,
num Chrome comum já logado, e grava os resultados em `data/latam/` para o GitHub
Actions ler depois.

## Como funciona

- `flightwatch/latam_browser.py` abre o Chrome instalado com um perfil só do projeto
  (`flight-watch/.latam-profile`, fora do git) e uma porta local de depuração (9333).
  Não é modo de automação: o login é feito à mão nessa janela e fica salvo no perfil.
- `flightwatch/latam.py` conecta nessa janela (Playwright via CDP) e faz o fluxo do site:
  1. abre a busca ida e volta com milhas e lê a resposta de
     `GET /bff/air-offers/v2/offers/search/redemption` (voos de ida);
  2. abre um voo de ida e clica "Escolher" → nova resposta da mesma API, agora com
     `outOfferId=...` (voos de volta).
  Os preços vêm por trecho (`brands[].price.amount` em milhas, `brands[].taxes.amount`
  em R$). A volta não depende da ida escolhida, então total = ida + volta.
  Não use busca "só ida" para somar: sai 35–50% mais caro que no ida e volta.
- Filtra pelas janelas de horário do `config.toml` e calcula
  `equivalent_brl = milhas/1000 × value_per_thousand_brl + taxas`.
- `flightwatch/latam_sweep.py` percorre todos os pares de datas e grava
  `data/latam/AAAA-MM-DD.jsonl` (formato no topo do arquivo).

## Uso

```bat
cd flight-watch
.venv\Scripts\python -m flightwatch.latam_browser          :: abre o Chrome do projeto; faça login
.venv\Scripts\python -m flightwatch.latam_sweep --limit 3  :: teste rápido
.venv\Scripts\python -m flightwatch.latam_sweep --part 1/2 --push
.venv\Scripts\python -m pytest tests
```

Instalação (uma vez): `python -m venv .venv`, `.venv\Scripts\pip install -r requirements.txt pytest`.
Não precisa do Chromium do Playwright: usa o Chrome instalado.

## Agendamento (Windows)

`run_latam_sweep.cmd 1/2` e `run_latam_sweep.cmd 2/2` rodam cada metade e fazem push.
Duas tarefas no Agendador, uma de manhã e outra à noite, cobrem todas as datas uma vez por dia.
O log fica em `flight-watch\logs\`.

## Quando a sessão expira

A varredura sai com código 2 e o log mostra `SESSÃO EXPIRADA`. Rode
`python -m flightwatch.latam_browser`, faça login de novo na janela e pronto.
