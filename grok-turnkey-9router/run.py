#!/usr/bin/env python3
"""
=============================================================================
 GROK CLI AUTO REGISTER & 9ROUTER AUTO SUBMIT BOT (EDISI SAYEMBARA)
 Full Turnkey Edition — Multi-Thread, Headless/Headed, Proxy/Direct
=============================================================================
"""

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Setup path agar modul internal terbaca otomatis
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.browser import run_single_registration
from core.router_sync import get_default_9router_db

BANNER = """
=============================================================================
   🤖 GROK CLI AUTO-REGISTER & 9ROUTER SUBMIT BOT (SAYEMBARA EDITION)
   🚀 By SyadAgentic | Zero-Setup Turnkey Bot for @schneizellyx
=============================================================================
  Fitur Utama:
  - Multi-threaded Concurrency (Bebas atur worker, misal 5 akun barengan)
  - Target Akun & Otomatis Stop jika kuota terpenuhi
  - Zero-Config Temp Mail (Mail.tm + Tempmail.plus bawaan tanpa API key)
  - Auto Turnstile Cloudflare Bypass Patch
  - Otomatis Mendapatkan Token Grok CLI (OAuth Device Flow Resmi)
  - Otomatis Submit & AKTIVASI ke database / API 9Router
  - Dukungan Headless (Background) maupun Headed (Buka Jendela Browser)
  - Dukungan Direct IP maupun Proxy Pool Rotation
=============================================================================
"""

def load_proxy_list(proxy_arg: str):
    """Membaca daftar proxy dari file atau string tunggal."""
    if not proxy_arg:
        return []
    p = Path(proxy_arg)
    if p.exists() and p.is_file():
        proxies = []
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
        return proxies
    return [proxy_arg.strip()]

def interactive_menu():
    """Menu konfigurasi interaktif jika bot dijalankan tanpa argumen CLI."""
    print(BANNER)
    print("Tekan ENTER untuk memilih nilai default [dalam kurung siku]:\n")

    try:
        t_in = input(">> Masukkan Target Jumlah Akun [Default: 5]: ").strip()
        target = int(t_in) if t_in else 5

        w_in = input(">> Masukkan Jumlah Worker/Thread Simultan [Default: 3]: ").strip()
        workers = int(w_in) if w_in else 3

        h_in = input(">> Jalankan Mode Headless / Tanpa Jendela? (y/n) [Default: y]: ").strip().lower()
        headless = False if h_in == "n" else True

        p_in = input(">> Masukkan File Proxy atau URL Proxy (kosongkan jika tanpa proxy) [Default: Direct]: ").strip()
        proxy = p_in if p_in else None

        r_in = input(">> Otomatis Submit & Aktivasi ke 9Router? (y/n) [Default: y]: ").strip().lower()
        auto_router = False if r_in == "n" else True

        return target, workers, headless, proxy, auto_router
    except (KeyboardInterrupt, EOFError):
        print("\n[!] Dibatalkan oleh pengguna.")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Grok CLI Auto Register & 9Router Auto Submit Bot")
    parser.add_argument("-t", "--target", type=int, default=None, help="Target jumlah akun yang ingin dibuat (contoh: 5)")
    parser.add_argument("-w", "--workers", type=int, default=None, help="Jumlah worker simultan / threads (contoh: 3 atau 5)")
    parser.add_argument("--headless", action="store_true", default=None, help="Jalankan browser dalam mode headless (default)")
    parser.add_argument("--headed", action="store_true", help="Jalankan browser dengan jendela GUI terlihat")
    parser.add_argument("-p", "--proxy", type=str, default=None, help="Path ke file proxy list (txt) atau single proxy URL")
    parser.add_argument("--no-router", action="store_true", help="Jangan submit otomatis ke 9Router")
    parser.add_argument("--router-db", type=str, default=None, help="Custom path ke SQLite data.sqlite 9Router")
    parser.add_argument("--mail-backend", type=str, default="mailtm", choices=["mailtm", "tempplus"], help="Backend tempmail (default: mailtm)")

    args = parser.parse_args()

    # Cek apakah dijalankan interaktif atau via argumen CLI
    if args.target is None and args.workers is None and not args.headed:
        target, workers, headless, proxy_arg, auto_router = interactive_menu()
    else:
        target = args.target if args.target is not None else 5
        workers = args.workers if args.workers is not None else 3
        headless = False if args.headed else True
        proxy_arg = args.proxy
        auto_router = not args.no_router
        print(BANNER)

    # Lokasi 9Router Database
    db_path = args.router_db or (str(get_default_9router_db()) if auto_router else None)

    proxy_list = load_proxy_list(proxy_arg)

    print("📋 KONFIGURASI SESI:")
    print(f"   • Target Akun   : {target}")
    print(f"   • Concurrency   : {workers} Worker Thread")
    print(f"   • Mode Browser  : {'Headless (Background)' if headless else 'Headed (Jendela Aktif)'}")
    print(f"   • Proxy Pool    : {f'{len(proxy_list)} proxy terdeteksi' if proxy_list else 'Direct Connection (Tanpa Proxy)'}")
    print(f"   • 9Router Sync  : {'AKTIF (' + str(db_path) + ')' if auto_router else 'NONAKTIF'}")
    print(f"   • Output File   : accounts.txt & accounts.json")
    print("=" * 77 + "\n")

    t_start = time.time()
    success_count = 0
    fail_count = 0

    def _worker_job(worker_num, acc_idx):
        px = proxy_list[(acc_idx - 1) % len(proxy_list)] if proxy_list else None
        return run_single_registration(
            worker_id=worker_num,
            acc_idx=acc_idx,
            total_target=target,
            headless=headless,
            proxy_str=px,
            router_db_path=db_path,
            auto_submit_router=auto_router,
            mail_backend=args.mail_backend
        )

    # Eksekusi dengan ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for i in range(1, target + 1):
            w_id = ((i - 1) % workers) + 1
            f = executor.submit(_worker_job, w_id, i)
            futures.append(f)
            time.sleep(0.5)  # Stagger sedikit agar request tidak bertabrakan persis di milidetik sama

        for f in as_completed(futures):
            try:
                res = f.result()
                if res:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                print(f"[!] Worker Error: {e}")
                fail_count += 1

    elapsed = time.time() - t_start
    print("\n" + "=" * 77)
    print("🎉 RINGKASAN EKSEKUSI:")
    print(f"   • Berhasil Terdaftar & Terintegrasi : {success_count} Akun")
    print(f"   • Gagal                            : {fail_count} Akun")
    print(f"   • Waktu Total                      : {elapsed:.1f} Detik")
    print(f"   • Data Akun Tersimpan di           : {BASE_DIR / 'accounts.txt'}")
    if auto_router:
        print(f"   • Status 9Router                   : Otomatis AKTIF di tabel providerConnections")
    print("=" * 77)

if __name__ == "__main__":
    main()
