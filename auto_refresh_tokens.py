#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ Grok CLI (xAI) OAuth Auto-Refresher & Token Lifecycle Manager
================================================================
Fungsi Utama:
1. Memperbarui (refresh) OAuth Access Token dan Refresh Token sebelum kedaluwarsa (6 jam xAI cycle).
2. Memperbarui langsung ke file grok_credentials.json dan database SQLite 9Router (data.sqlite).
3. Self-Healing Auto-Purge: Jika refresh token sudah 'revoked' (hangus permanen), akun langsung
   dihapus dari 9Router dan grok_credentials.json secara otomatis.
4. Mendukung mode sekali jalan (batch refresh) atau mode loop daemon (jalan di latar belakang tiap 3.5 jam).

Usage:
  python auto_refresh_tokens.py               # Refresh semua akun Grok aktif
  python auto_refresh_tokens.py --workers 20   # Multi-thread 20 workers
  python auto_refresh_tokens.py --loop         # Berjalan otomatis setiap 3.5 jam
"""

import argparse
import concurrent.futures
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

# Setup Windows UTF-8 console output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
TOKEN_URL = "https://auth.x.ai/oauth2/token"


def get_data_dir() -> Path:
    if os.environ.get("DATA_DIR"):
        return Path(os.environ["DATA_DIR"])
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "9router"
    return Path.home() / ".9router"


def refresh_single_token(item: dict) -> dict:
    """Melakukan refresh token ke xAI OAuth API endpoint."""
    email = item.get("email", "")
    refresh_token = item.get("refreshToken") or item.get("refresh_token")
    if not refresh_token:
        return {"email": email, "status": "no_token", "error": "No refresh token"}

    payload = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
    }).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_URL,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "grok-pager/0.2.93",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status == 200:
                res_data = json.loads(resp.read().decode("utf-8"))
                return {
                    "email": email,
                    "status": "success",
                    "access_token": res_data.get("access_token"),
                    "refresh_token": res_data.get("refresh_token", refresh_token),
                    "expires_in": res_data.get("expires_in", 21600),
                }
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
            err_json = json.loads(err_body)
            err_msg = err_json.get("error_description") or err_json.get("error") or str(e)
        except Exception:
            err_msg = str(e)

        is_revoked = e.code in (400, 401) and any(
            k in err_msg.lower() for k in ["revoked", "invalid_grant", "invalid token", "expired"]
        )
        return {
            "email": email,
            "status": "revoked" if is_revoked else "failed",
            "error": f"HTTP {e.code}: {err_msg}",
            "code": e.code
        }
    except Exception as e:
        return {"email": email, "status": "failed", "error": str(e)}


def run_refresh_cycle(workers: int = 15, auto_purge: bool = True):
    base_dir = Path(__file__).resolve().parent
    cred_file = base_dir / "grok_credentials.json"

    if not cred_file.exists():
        print(f"{Colors.RED}[!] File kredensial tidak ditemukan di: {cred_file}{Colors.RESET}")
        return

    try:
        raw_items = json.loads(cred_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"{Colors.RED}[!] Gagal membaca file {cred_file.name}: {e}{Colors.RESET}")
        return

    if not isinstance(raw_items, list) or not raw_items:
        print(f"{Colors.YELLOW}[!] Tidak ada kredensial yang tersimpan di {cred_file.name}.{Colors.RESET}")
        return

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}")
    print("        ⚡ GROK CLI (xAI) TOKEN AUTO-REFRESH & SELF-HEALING        ")
    print(f"{'=' * 70}{Colors.RESET}")
    print(f"[*] Total Akun di File JSON : {Colors.BOLD}{len(raw_items)}{Colors.RESET}")
    print(f"[*] Worker Threads Paralel  : {workers}")
    print(f"[*] Menghubungi xAI OAuth Token Server...\n")

    t0 = time.time()
    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futs = {executor.submit(refresh_single_token, item): item for item in raw_items}
        total = len(futs)
        for idx, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            res = fut.result()
            results[res["email"]] = res
            if idx % 20 == 0 or idx == total:
                success_so_far = sum(1 for r in results.values() if r["status"] == "success")
                revoked_so_far = sum(1 for r in results.values() if r["status"] == "revoked")
                fail_so_far = sum(1 for r in results.values() if r["status"] == "failed")
                pct = (idx / total) * 100
                print(
                    f"\r[{idx}/{total}] ({pct:.0f}%) "
                    f"Segar: {Colors.GREEN}{success_so_far}{Colors.RESET} | "
                    f"Revoked/Dead: {Colors.RED}{revoked_so_far}{Colors.RESET} | "
                    f"NetErr: {Colors.YELLOW}{fail_so_far}{Colors.RESET}",
                    end="",
                    flush=True,
                )

    print()
    elapsed = time.time() - t0

    # Kategorikan hasil
    success_map = {r["email"]: r for r in results.values() if r["status"] == "success"}
    revoked_emails = {r["email"] for r in results.values() if r["status"] == "revoked"}
    failed_emails = {r["email"] for r in results.values() if r["status"] == "failed"}

    # 1. Update ke grok_credentials.json
    now_iso = datetime.now(timezone.utc).isoformat()
    kept_items = []
    for item in raw_items:
        em = item.get("email")
        if em in revoked_emails and auto_purge:
            # Otomatis dibuang karena revoked
            continue
        if em in success_map:
            s_data = success_map[em]
            item["accessToken"] = s_data["access_token"]
            item["refreshToken"] = s_data["refresh_token"]
            item["expiresIn"] = s_data.get("expires_in", 21600)
            item["updatedAt"] = now_iso
        kept_items.append(item)

    # Atomic write to grok_credentials.json
    tmp_f = cred_file.with_suffix('.tmp')
    tmp_f.write_text(json.dumps(kept_items, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        tmp_f.replace(cred_file)
    except Exception:
        cred_file.write_text(json.dumps(kept_items, indent=2, ensure_ascii=False), encoding="utf-8")
        if tmp_f.exists():
            tmp_f.unlink(missing_ok=True)

    # 2. Sinkronisasi ke SQLite Database 9Router
    db_file = get_data_dir() / "db" / "data.sqlite"
    db_updated = 0
    db_deleted = 0

    if db_file.exists():
        try:
            conn = sqlite3.connect(str(db_file), timeout=30.0)
            cur = conn.cursor()
            cur.execute("PRAGMA busy_timeout = 30000")

            # Ambil koneksi grok-cli yang ada
            cur.execute("SELECT id, name, data FROM providerConnections WHERE provider='grok-cli'")
            rows = cur.fetchall()

            for cid, name, data_raw in rows:
                if name in revoked_emails and auto_purge:
                    cur.execute("DELETE FROM providerConnections WHERE id = ?", (cid,))
                    db_deleted += 1
                    continue

                if name in success_map:
                    s_data = success_map[name]
                    try:
                        d = json.loads(data_raw) if data_raw else {}
                    except Exception:
                        d = {}

                    d["accessToken"] = s_data["access_token"]
                    d["refreshToken"] = s_data["refresh_token"]
                    d["testStatus"] = "active"
                    d["lastError"] = None
                    d["errorCode"] = None
                    d["lastErrorAt"] = None
                    d["expiresIn"] = s_data.get("expires_in", 21600)

                    cur.execute(
                        "UPDATE providerConnections SET data = ?, updatedAt = datetime('now') WHERE id = ?",
                        (json.dumps(d), cid)
                    )
                    db_updated += 1

            conn.commit()
            conn.close()
        except Exception as e_db:
            print(f"{Colors.YELLOW}[!] Peringatan saat sync ke 9Router DB: {e_db}{Colors.RESET}")

    # Ringkasan Laporan
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'=' * 70}")
    print("                     LIFECYCLE REFRESH SELESAI                     ")
    print(f"{'=' * 70}{Colors.RESET}")
    print(f"[*] Token Berhasil Diperbarui : {Colors.BOLD}{Colors.GREEN}{len(success_map)}{Colors.RESET} akun (Masa aktif +6 jam)")
    if revoked_emails:
        print(f"[*] Akun Revoked / Hangus     : {Colors.BOLD}{Colors.RED}{len(revoked_emails)}{Colors.RESET} akun (Auto-Purged dari 9Router & JSON)")
    if failed_emails:
        print(f"[*] Gangguan Jaringan (Skip) : {Colors.YELLOW}{len(failed_emails)}{Colors.RESET} akun")
    print(f"[*] Sinkronisasi 9Router      : {db_updated} akun diperbarui | {db_deleted} akun mati dibersihkan")
    print(f"[*] Waktu Eksekusi            : {elapsed:.2f} detik ({len(raw_items) / max(0.01, elapsed):.1f} req/detik)\n")


def main():
    parser = argparse.ArgumentParser(description="Grok CLI Token Auto-Refresher & Lifecycle Manager")
    parser.add_argument("--workers", "-w", type=int, default=20, help="Jumlah thread paralel (default: 20)")
    parser.add_argument("--loop", action="store_true", help="Jalankan terus di latar belakang (refresh tiap 3.5 jam)")
    parser.add_argument("--interval", type=int, default=12600, help="Interval loop dalam detik (default: 12600 = 3.5 jam)")
    parser.add_argument("--no-purge", action="store_true", help="Jangan hapus akun yang revoked secara otomatis")
    args = parser.parse_args()

    if args.loop:
        print(f"{Colors.BOLD}{Colors.CYAN}[*] Mode Daemon Auto-Refresh Aktif (Interval: {args.interval / 3600:.1f} jam){Colors.RESET}")
        print(f"[*] Token akun Grok akan terus disegarkan secara otomatis agar TIDAK PERNAH KEDALUWARSA.")
        print(f"[*] Tekan Ctrl+C untuk menghentikan.\n")
        while True:
            try:
                run_refresh_cycle(workers=args.workers, auto_purge=not args.no_purge)
                print(f"[*] Tidur selama {args.interval / 3600:.1f} jam sebelum refresh berikutnya...")
                time.sleep(args.interval)
            except (KeyboardInterrupt, SystemExit):
                print(f"\n{Colors.YELLOW}[!] Daemon dihentikan oleh pengguna.{Colors.RESET}")
                break
            except Exception as e:
                print(f"\n{Colors.RED}[!] Error pada siklus: {e}{Colors.RESET}")
                time.sleep(60)
    else:
        run_refresh_cycle(workers=args.workers, auto_purge=not args.no_purge)


if __name__ == "__main__":
    main()
