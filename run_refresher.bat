@echo off
title ⚡ Grok CLI Token Auto-Refresher
chcp 65001 >nul 2>&1
cd /d "%~dp0"

set "PY=python"

echo ======================================================================
echo   GROK CLI OAUTH TOKEN AUTO-REFRESHER ^& LIFECYCLE MANAGER
echo ======================================================================
echo   [1] Refresh Sekali Sekarang (Instant Multi-Threaded Sync)
echo   [2] Nyalakan Daemon 24/7 di Background (Auto-Refresh tiap 3.5 Jam)
echo   [0] Batal / Keluar
echo ======================================================================
set "rf_choice="
set /p rf_choice="Pilih mode [1-2 / default 1]: "
if "%rf_choice%"=="0" exit /b
if "%rf_choice%"=="2" (
    echo [*] Menjalankan Grok Auto-Refresher Daemon 24/7 (tiap 3.5 jam)...
    "%PY%" auto_refresh_tokens.py --loop --workers 20
    goto end
)

echo [*] Menjalankan Grok Token Refresh Instan...
"%PY%" auto_refresh_tokens.py --workers 20

:end
echo.
pause
