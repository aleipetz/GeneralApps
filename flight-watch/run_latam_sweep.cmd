@echo off
rem Varredura LATAM Pass para o Agendador de Tarefas do Windows.
rem Uso: run_latam_sweep.cmd [N]   faz N pares de datas (padrão 10), em rodízio,
rem      com ~3 min entre buscas, e faz push dos dados.
rem Log em flight-watch\logs\latam_sweep_AAAA-MM-DD_HHMM.log
cd /d "%~dp0"
set PYTHONUTF8=1
set BATCH=%~1
if "%BATCH%"=="" set BATCH=10
if not exist logs mkdir logs
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set TS=%%i
".venv\Scripts\python.exe" -m flightwatch.latam_sweep --batch %BATCH% --push >> "logs\latam_sweep_%TS%.log" 2>&1
exit /b %ERRORLEVEL%
