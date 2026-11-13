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

O site limita a frequência: em 13/11/2026, umas 6 buscas seguidas, com 10 a 40 s de
intervalo, bastaram para receber 403 ("A busca está demorando mais que o normal") em todas
as seguintes. Por isso:

- `run_latam_sweep.cmd [N]` faz só N pares (padrão 10) com ~3 min entre buscas,
  continuando de onde a execução anterior parou (cursor em `.latam-state.json`), e faz push.
- Após 2 falhas seguidas a varredura para (código 3) e a próxima recomeça do mesmo par.
- 4 tarefas por dia (07:00, 12:00, 17:00, 22:00) × 10 pares = 40 pares/dia, ou seja,
  todas as ~87 datas a cada ~2 dias. Cada execução leva ~35 min.

Tarefas: `flight-watch LATAM 07h`, `12h`, `17h`, `22h` (Agendador de Tarefas → Biblioteca).
Para conferir: `schtasks /Query /TN "flight-watch LATAM 07h" /V /FO LIST` (campo
"Último resultado": 0 = ok, 2 = refazer login, 3 = bloqueio) e os logs em `flight-watch\logs\`.
O computador precisa estar ligado e com seu usuário logado no horário.

## Quando a sessão expira

A varredura sai com código 2 e o log mostra `SESSÃO EXPIRADA`. Rode
`python -m flightwatch.latam_browser`, faça login de novo na janela e pronto.
