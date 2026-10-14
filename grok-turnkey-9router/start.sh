#!/usr/bin/env bash
# Launcher 1-klik Linux / macOS
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================================================="
echo "   Grok CLI Auto Register & 9Router Submit Bot (Sayembara Edition)"
echo "========================================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[!] python3 tidak ditemukan! Harap install Python 3.9+ terlebih dahulu."
    exit 1
fi

echo "[*] Memeriksa dependensi..."
python3 -m pip install -r requirements.txt --quiet 2>/dev/null || true

echo "[*] Menjalankan bot..."
echo ""
python3 run.py "$@"
