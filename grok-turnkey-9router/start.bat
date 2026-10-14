@echo off
title Grok CLI Auto Register & 9Router Submit Bot
chcp 65001 >nul
cls

echo =========================================================================
echo    Grok CLI Auto Register & 9Router Submit Bot (Sayembara Edition)
echo =========================================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python tidak ditemukan! Silakan install Python 3.9+ terlebih dahulu.
    pause
    exit /b
)

echo [*] Memeriksa & memasang dependensi yang dibutuhkan...
python -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [!] Gagal memasang dependensi. Mencoba melanjutkan...
)

echo.
echo [*] Menjalankan Bot...
echo.
python run.py

pause
