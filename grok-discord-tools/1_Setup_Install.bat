@echo off
title 9Router Grok CLI Tools - Setup & Dependencies Installer
cd /d "%~dp0"

echo ================================================================
echo   9ROUTER GROK CLI TOOLS - INSTALLER
echo ================================================================
echo.

echo [*] Memeriksa Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python tidak ditemukan di sistem Anda!
    echo     Silakan instal Python 3.10+ dari https://www.python.org/
    echo     Pastikan centang 'Add Python to PATH' saat menginstal.
    echo.
    pause
    exit /b
)

echo [1] Membuat virtual environment (.venv)...
if not exist ".venv" (
    python -m venv .venv
)

echo [2] Menginstal dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ================================================================
echo   [V] INSTALLASI SELESAI & TOOLS SIAP DIGUNAKAN!
echo   Pilih opsi:
echo   - Jalankan '2_Connect_Grok_Browser.bat' untuk login via browser.
echo   - Atau isi 'accounts.txt' lalu jalankan '3_Import_To_9Router.bat'.
echo ================================================================
echo.
pause
