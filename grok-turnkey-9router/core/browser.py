"""Browser Automation Engine untuk Registrasi Grok xAI & Otorisasi OAuth."""
import json
import os
import random
import re
import string
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .mail import TempMailBox
from .oauth import poll_device_token, request_device_code
from .router_sync import submit_to_9router_api, submit_to_9router_sqlite

BASE_DIR = Path(__file__).resolve().parent.parent
TURNSTILE_PATCH_DIR = BASE_DIR / "turnstilePatch"
ACCOUNTS_TXT = BASE_DIR / "accounts.txt"
ACCOUNTS_JSON = BASE_DIR / "accounts.json"

FILE_LOCK = threading.Lock()
PRINT_LOCK = threading.Lock()

def safe_log(msg: str):
    with PRINT_LOCK:
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)

FIRST_NAMES = ["James", "Michael", "David", "Alexander", "Daniel", "Emma", "Sophia", "Olivia", "Lucas", "Liam"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Taylor", "Anderson"]

def parse_proxy_dict(proxy_str: Optional[str]) -> Optional[dict]:
    if not proxy_str or not proxy_str.strip():
        return None
    try:
        u = urllib.parse.urlparse(proxy_str.strip())
        if not u.hostname:
            return None
        scheme = "http" if u.scheme in ("http", "https") else "socks5"
        d = {"server": f"{scheme}://{u.hostname}:{u.port or 80}"}
        if u.username:
            d["username"] = u.username
        if u.password:
            d["password"] = u.password
        return d
    except Exception:
        return None

def save_account_record(rec: dict):
    with FILE_LOCK:
        with open(ACCOUNTS_TXT, "a", encoding="utf-8") as f:
            f.write(f"{rec['email']}|{rec['password']}|{rec.get('refresh_token', '')}\n")

        all_recs = []
        if ACCOUNTS_JSON.exists():
            try:
                all_recs = json.load(open(ACCOUNTS_JSON, "r", encoding="utf-8"))
            except Exception:
                all_recs = []
        all_recs.append(rec)
        with open(ACCOUNTS_JSON, "w", encoding="utf-8") as f:
            json.dump(all_recs, f, indent=2, ensure_ascii=False)

def run_single_registration(
    worker_id: int,
    acc_idx: int,
    total_target: int,
    headless: bool = True,
    proxy_str: Optional[str] = None,
    router_db_path: Optional[str] = None,
    auto_submit_router: bool = True,
    mail_backend: str = "mailtm"
) -> bool:
    """Melakukan proses lengkap pendaftaran 1 akun xAI Grok dan integrasi ke 9Router."""
    tag = f"[W{worker_id}][#{acc_idx}/{total_target}]"
    safe_log(f"{tag} 🚀 Memulai pembuatan akun Grok CLI...")

    # 1. Request Device Code resmi
    try:
        dev = request_device_code()
    except Exception as e:
        safe_log(f"{tag} ❌ Gagal inisiasi OAuth Device Code: {e}")
        return False

    user_code = dev.get("user_code")
    device_code = dev.get("device_code")
    safe_log(f"{tag} 🔑 Device Code didapat: {user_code}")

    # Poller thread
    token_box = {}
    stop_event = threading.Event()

    def _poll_thread():
        tok = poll_device_token(device_code, interval=2, timeout=240)
        if tok and tok.get("access_token"):
            token_box["token"] = tok
        stop_event.set()

    poller = threading.Thread(target=_poll_thread, daemon=True)
    poller.start()

    # 2. Buat Inbox Sementara
    safe_log(f"{tag} 📧 Menyiapkan email sementara...")
    try:
        mailbox = TempMailBox(backend=mail_backend)
        email = mailbox.address
        safe_log(f"{tag} 📨 Target Email: {email}")
    except Exception as e:
        safe_log(f"{tag} ❌ Gagal membuat email: {e}")
        return False

    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    password = "Gk!" + "".join(random.choices(string.ascii_letters + string.digits, k=10)) + "8#"

    # 3. Jalankan Browser Automation (Camoufox / Playwright)
    try:
        from camoufox.sync_api import Camoufox
        use_camoufox = True
    except ImportError:
        use_camoufox = False

    browser_kwargs = {
        "headless": headless,
    }
    proxy_dict = parse_proxy_dict(proxy_str)
    if proxy_dict:
        browser_kwargs["proxy"] = proxy_dict
        safe_log(f"{tag} 🌐 Menggunakan proxy: {proxy_dict['server']}")

    if use_camoufox:
        browser_kwargs["geoip"] = False
        browser_kwargs["humanize"] = True
        if TURNSTILE_PATCH_DIR.exists():
            browser_kwargs["addons"] = [str(TURNSTILE_PATCH_DIR)]

    success = False
    try:
        if use_camoufox:
            from camoufox.sync_api import Camoufox
            browser_ctx_mgr = Camoufox(**browser_kwargs)
        else:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser_ctx_mgr = pw.chromium.launch(
                headless=headless,
                proxy=proxy_dict,
                args=[f"--disable-extensions-except={TURNSTILE_PATCH_DIR}", f"--load-extension={TURNSTILE_PATCH_DIR}"]
                if TURNSTILE_PATCH_DIR.exists() else []
            )

        with browser_ctx_mgr as browser:
            page = browser.new_page()
            page.set_default_timeout(35000)

            # Buka Halaman Registrasi xAI dengan redirect OAuth Device
            signup_url = f"https://accounts.x.ai/sign-up?redirect=oauth2-provider&return_to=%2Foauth2%2Fdevice%3Fuser_code%3D{user_code}"
            safe_log(f"{tag} 🌐 Membuka portal pendaftaran xAI...")
            try:
                page.goto(signup_url, wait_until="domcontentloaded", timeout=25000)
            except Exception:
                pass
            time.sleep(2)

            # Klik opsi "Sign up with email"
            for sel in ("button:has-text('Sign up with email')", "button:has-text('email')", "[role='button']:has-text('email')", "text=Continue with email"):
                try:
                    btn = page.locator(sel).first
                    if btn.count() > 0 and btn.is_visible():
                        btn.click(timeout=3000)
                        break
                except Exception:
                    pass
            time.sleep(1)

            # Isi Email
            safe_log(f"{tag} ✍️ Mengisi form email...")
            try:
                inp_email = page.locator("input[type='email'], input[name='email'], input").first
                inp_email.wait_for(state="visible", timeout=12000)
                inp_email.fill(email)
                time.sleep(0.5)
                btn_next = page.locator("button[type='submit'], button:has-text('Next'), button:has-text('Continue')").first
                btn_next.click(timeout=3000)
            except Exception as e:
                safe_log(f"{tag} ❌ Gagal submit email: {e}")
                return False

            # Tunggu dan Ambil Kode OTP
            safe_log(f"{tag} ⏳ Menunggu kode OTP dari inbox...")
            otp = mailbox.wait_for_otp(timeout=80, poll=3)
            if not otp:
                safe_log(f"{tag} ⚠️ Timeout: OTP tidak diterima untuk {email}")
                return False

            safe_log(f"{tag} ✅ OTP Diterima: {otp}")

            # Masukkan Kode OTP
            inputs = page.locator("input[type='text'], input[inputmode='numeric']")
            try:
                if inputs.count() >= 6:
                    for i_d, dgt in enumerate(otp[:6]):
                        inputs.nth(i_d).fill(dgt)
                        time.sleep(0.05)
                else:
                    page.locator("input").first.fill(otp)
            except Exception as e:
                safe_log(f"{tag} ⚠️ Error input OTP: {e}")
            time.sleep(2)

            # Isi Data Diri & Password
            safe_log(f"{tag} 👤 Mengisi profil ({first_name} {last_name}) & password...")
            try:
                if page.locator("input[name='givenName']").count() > 0:
                    page.locator("input[name='givenName']").fill(first_name)
                if page.locator("input[name='familyName']").count() > 0:
                    page.locator("input[name='familyName']").fill(last_name)
                if page.locator("input[name='password']").count() > 0:
                    page.locator("input[name='password']").fill(password)
                time.sleep(0.5)

                btn_finish = page.locator("button[type='submit']:has-text('Complete sign up'), button[type='submit']").first
                if btn_finish.count() > 0:
                    btn_finish.click(timeout=3000)
            except Exception as e:
                safe_log(f"{tag} ⚠️ Error profil: {e}")
            time.sleep(3)

            # Halaman Otorisasi Device Code xAI
            safe_log(f"{tag} 🔐 Memproses konfirmasi otorisasi...")
            try:
                if "user_code=" not in page.url:
                    page.goto(f"https://accounts.x.ai/oauth2/device?user_code={user_code}", wait_until="domcontentloaded", timeout=15000)
            except Exception:
                pass

            deadline_auth = time.time() + 30
            while time.time() < deadline_auth and not stop_event.is_set():
                # Tutup dialog cookie onetrust jika ada
                try:
                    page.evaluate("() => document.querySelectorAll('#onetrust-consent-sdk, [id*=\"onetrust\"]').forEach(e => e.remove())")
                except Exception:
                    pass

                for sel in ("button:has-text('Continue')", "button:has-text('Allow')", "button:has-text('Authorize')", "button:has-text('Approve')"):
                    try:
                        b = page.locator(sel).first
                        if b.count() > 0 and b.is_visible():
                            b.click(force=True, timeout=1000)
                            time.sleep(1)
                    except Exception:
                        pass
                time.sleep(1)

            # Tunggu Poller mendapatkan Token OAuth
            safe_log(f"{tag} ⏳ Mengambil Access Token & Refresh Token...")
            for _ in range(25):
                if "token" in token_box or stop_event.is_set():
                    break
                time.sleep(1)

            if "token" in token_box:
                tok = token_box["token"]
                access_token = tok.get("access_token", "")
                refresh_token = tok.get("refresh_token", "")

                safe_log(f"{tag} 🎉 SUKSES! Token OAuth Berhasil Didapatkan!")
                rec = {
                    "email": email,
                    "password": password,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                save_account_record(rec)

                # Submit & Aktivasi ke 9Router
                if auto_submit_router:
                    safe_log(f"{tag} 🔄 Mengintegrasikan akun ke 9Router...")
                    ok_db, msg_db = submit_to_9router_sqlite(email, tok, db_path=router_db_path)
                    if ok_db:
                        safe_log(f"{tag} ✅ [9Router SQLite] {msg_db}")
                    else:
                        safe_log(f"{tag} ⚠️ [9Router SQLite] {msg_db}")
                        # Fallback ke REST API jika SQLite belum terdeteksi
                        ok_api, msg_api = submit_to_9router_api(email, tok)
                        if ok_api:
                            safe_log(f"{tag} ✅ [9Router API] {msg_api}")

                success = True
            else:
                safe_log(f"{tag} ❌ Gagal menangkap token OAuth xAI.")

    except Exception as e:
        safe_log(f"{tag} ❌ Exception selama eksekusi: {e}")

    return success
