@echo off
chcp 65001 >nul
title 9Router Grok Auto-Adder (Multi-Worker Parallel Engine)
color 0A
cd /d "%~dp0"

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"

echo =======================================================
echo     9ROUTER GROK CLI 100%% AUTO-ADDER ^& OAUTH ENGINE
echo          (HIGH-SPEED MULTI-WORKER PARALEL)
echo =======================================================
echo.
echo Tool ini akan:
echo 1. Membuat akun Grok resmi secara hands-free
echo 2. Menangkap kode OTP verifikasi secara instan
echo 3. Mengotorisasi OAuth token resmi xAI via protokol cepat
echo 4. Menginjeksi langsung token aktif ke database 9Router SQLite
echo.

if not exist "%VENV_PYTHON%" (
    echo [!] Dependensi belum terinstal. Menjalankan 1_Setup_Install.bat...
    echo.
    call "%SCRIPT_DIR%1_Setup_Install.bat"
)

set /p JUMLAH="Berapa banyak total akun yang ingin dibuat? (Default: 5): "
if "%JUMLAH%"=="" set JUMLAH=5

echo.
echo -------------------------------------------------------
echo  PILIH KECEPATAN EKSEKUSI PARALEL (MULTI-WORKER):
echo -------------------------------------------------------
echo  [1] 1 Worker   (Serial - 1 akun per waktu)
echo  [2] 3 Worker   (Paralel Cepat) [Rekomendasi]
echo  [3] 5 Worker   (Paralel Super Kilat)
echo  [4] 10 Worker  (Paralel Extreme)
echo.
set /p PILIH_MODE="Pilih mode paralel (1/2/3/4 atau ketik jumlah worker, Default: 3): "

set WORKERS=3
if "%PILIH_MODE%"=="1" set WORKERS=1
if "%PILIH_MODE%"=="2" set WORKERS=3
if "%PILIH_MODE%"=="3" set WORKERS=5
if "%PILIH_MODE%"=="4" set WORKERS=10
if "%PILIH_MODE%"=="" set WORKERS=3
if "%PILIH_MODE%" GTR "4" set WORKERS=%PILIH_MODE%

echo.
echo [*] Menjalankan pembuatan %JUMLAH% akun dengan %WORKERS% Worker Paralel...
echo.

"%VENV_PYTHON%" "%SCRIPT_DIR%grok_full_auto.py" %JUMLAH% %WORKERS%

echo.
echo =======================================================
echo  [V] Selesai! Semua akun telah diproses ke 9Router.
echo =======================================================
pause
