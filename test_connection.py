#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ Grok CLI 9Router Direct Connection Tester
============================================
Menguji inferensi model Grok via endpoint 9Router lokal:
http://127.0.0.1:20128/v1/chat/completions
"""

import sys
import requests

# Fix Windows console UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROUTER_URL = "http://127.0.0.1:20128/v1/chat/completions"
MODELS_TO_TEST = ["gcli/grok-4.7", "gcli/grok-4.6", "gcli/grok-4.5"]


def test_inference(model: str):
    print(f"[*] Menguji model: {model} ...", end=" ", flush=True)
    try:
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Hai Grok! Balas dalam 1 kalimat singkat saja."}
            ],
            "max_tokens": 50
        }
        headers = {
            "Authorization": "Bearer 9router",
            "Content-Type": "application/json"
        }
        res = requests.post(ROUTER_URL, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            data = res.json()
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            print("SUKSES (200 OK) ✓")
            print(f"    Respon: \"{reply}\"\n")
            return True
        else:
            print(f"GAGAL ({res.status_code})")
            print(f"    Error: {res.text[:150]}\n")
            return False
    except requests.exceptions.ConnectionError:
        print("GAGAL - 9Router tidak aktif pada port 20128.")
        print("    Pastikan 9Router berjalan di background (http://127.0.0.1:20128).\n")
        return False
    except Exception as e:
        print(f"ERROR: {e}\n")
        return False


def main():
    print("=" * 65)
    print("   ⚡ GROK CLI -> 9ROUTER INFERENCE HEALTH CHECK   ")
    print("=" * 65)
    print(f"[*] Target Endpoint: {ROUTER_URL}\n")

    success = False
    for m in MODELS_TO_TEST:
        if test_inference(m):
            success = True
            break

    if success:
        print("🎉 Koneksi 9Router untuk Grok CLI berfungsi normal!")
    else:
        print("[-] Cek kembali apakah akun sudah diinjeksi via 'python inject_to_9router.py'")


if __name__ == "__main__":
    main()
