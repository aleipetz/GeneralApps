@echo off
rem Varredura LATAM Pass para o Agendador de Tarefas do Windows.
rem Uso: run_latam_sweep.cmd 1/2   (ou 2/2; sem argumento = varredura completa)
rem Log em flight-watch\logs\latam_sweep_AAAA-MM-DD_HHMM.log
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist logs mkdir logs
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set TS=%%i
if "%~1"=="" (
  ".venv\Scripts\python.exe" -m flightwatch.latam_sweep --push >> "logs\latam_sweep_%TS%.log" 2>&1
) else (
  ".venv\Scripts\python.exe" -m flightwatch.latam_sweep --part %1 --push >> "logs\latam_sweep_%TS%.log" 2>&1
)
exit /b %ERRORLEVEL%
