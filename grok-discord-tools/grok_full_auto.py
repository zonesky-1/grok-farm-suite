"""
=============================================================================
 9Router Grok CLI Full-Auto Parallel Registration & OAuth Engine
 Standalone Distribution Edition (Zero Private Data)
=============================================================================
"""

from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import ssl
import string
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
ACCOUNTS_TXT = BASE_DIR / "accounts.txt"
TURNSTILE_PATCH_DIR = BASE_DIR / "turnstilePatch"

XAI_DEVICE_CODE_URL = "https://auth.x.ai/oauth2/device/code"
XAI_TOKEN_URL = "https://auth.x.ai/oauth2/token"
CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
DEFAULT_SCOPE = "openid profile email offline_access grok-cli:access api:access"

DB_LOCK = threading.Lock()
FILE_LOCK = threading.Lock()
PRINT_LOCK = threading.Lock()


def safe_print(*args, **kwargs):
    with PRINT_LOCK:
        print(*args, **kwargs, flush=True)


def load_config() -> dict:
    default_config = {
        "email_worker_url": "",
        "email_domain": "example.com",
        "webshare_api_key": "",
        "proxy_rotate_every_accounts": 3,
        "default_headless": True
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                default_config.update(json.load(f))
        except Exception:
            pass
    return default_config


def get_9router_db_path() -> Path:
    candidates = []
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "9router" / "db" / "data.sqlite")
        localappdata = os.getenv("LOCALAPPDATA")
        if localappdata:
            candidates.append(Path(localappdata) / "9router" / "db" / "data.sqlite")
    else:
        home = Path.home()
        candidates.append(home / ".config" / "9router" / "db" / "data.sqlite")
        candidates.append(home / ".9router" / "db" / "data.sqlite")

    for p in candidates:
        if p.exists():
            return p

    fallback = Path.home() / "AppData" / "Roaming" / "9router" / "db" / "data.sqlite"
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback


def request_device_code() -> dict:
    payload = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "scope": DEFAULT_SCOPE
    }).encode("utf-8")

    req = urllib.request.Request(
        XAI_DEVICE_CODE_URL,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "grok-cli/1.0.0"
        }
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def poll_device_token(device_code: str, interval: int = 1, timeout: int = 300) -> dict:
    payload = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": device_code,
        "client_id": CLIENT_ID
    }).encode("utf-8")

    deadline = time.time() + timeout
    ctx = ssl.create_default_context()

    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                XAI_TOKEN_URL,
                data=payload,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "grok-cli/1.0.0"
                }
            )
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "access_token" in data:
                    return data
        except urllib.error.HTTPError as e:
            if e.code not in [400, 429]:
                pass
        except Exception:
            pass
        time.sleep(interval)
    return {}


def poll_for_otp(email: str, worker_base: str, timeout: int = 40) -> str:
    safe_print(f"[*] Menunggu email OTP xAI untuk {email}...")
    if not worker_base:
        safe_print(f" [!] 'email_worker_url' belum dikonfigurasi di config.json!")
        return ""

    deadline = time.time() + timeout
    url = f"{worker_base.rstrip('/')}/api/mails"
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {email}", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for msg in data.get("results", []):
                    code = msg.get("code")
                    if code:
                        return re.sub(r"\D", "", str(code)).strip()
                    match = re.search(r"\b(\d{6}|\d{3}-\d{3})\b", (msg.get("subject", "") + " " + msg.get("text", "")))
                    if match:
                        return re.sub(r"\D", "", match.group(1)).strip()
        except Exception:
            pass
        time.sleep(0.5)
    return ""


def insert_grok_token_to_9router(email: str, token_data: dict) -> bool:
    db_path = get_9router_db_path()
    if not db_path.exists():
        safe_print(f"[!] Database 9Router tidak ditemukan di: {db_path}")
        return False

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    id_token = token_data.get("id_token", "")
    expires_in = int(token_data.get("expires_in", 21600))

    expires_at = datetime.fromtimestamp(time.time() + expires_in, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    now_iso = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")

    conn_data = {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "idToken": id_token,
        "tokenType": "Bearer",
        "expiresIn": expires_in,
        "expiresAt": expires_at,
        "scope": DEFAULT_SCOPE,
        "email": email,
        "displayName": f"Grok ({email})",
        "testStatus": "active",
        "lastError": None,
        "lastErrorAt": None,
        "errorCode": None,
        "backoffLevel": 0,
        "providerSpecificData": {
            "authMethod": "device_code",
            "idToken": id_token,
            "email": email,
            "userId": f"usr_{uuid.uuid4().hex[:12]}",
            "hasGrokCodeAccess": True,
            "subscriptionTier": "Grok Free",
            "connectionProxyEnabled": False,
            "connectionProxyUrl": "",
            "connectionNoProxy": ""
        }
    }

    conn_data_str = json.dumps(conn_data, ensure_ascii=False)
    conn_id = str(uuid.uuid4())

    with DB_LOCK:
        try:
            conn = sqlite3.connect(str(db_path), timeout=60.0)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(priority) FROM providerConnections WHERE provider = 'grok-cli'")
            max_p = cursor.fetchone()[0]
            next_p = (max_p or 0) + 1

            cursor.execute("SELECT id FROM providerConnections WHERE provider = 'grok-cli' AND email = ?", (email,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE providerConnections
                    SET data = ?, isActive = 1, updatedAt = ?
                    WHERE id = ?
                """, (conn_data_str, now_iso, existing[0]))
                safe_print(f"[9Router DB] Berhasil memperbarui koneksi: {email}")
            else:
                cursor.execute("""
                    INSERT INTO providerConnections (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt)
                    VALUES (?, 'grok-cli', 'oauth', ?, ?, ?, 1, ?, ?, ?)
                """, (conn_id, f"Grok ({email})", email, next_p, conn_data_str, now_iso, now_iso))
                safe_print(f"[9Router DB] Berhasil menambahkan koneksi #{next_p}: {email}")

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            safe_print(f"[!] Error database 9Router: {e}")
            return False


def create_single_account(browser, i: int, total_count: int, config: dict) -> bool:
    safe_print(f"\n>>> [AKUN #{i}/{total_count}] Memulai proses pendaftaran & otorisasi...")

    # 1. Inisiasi OAuth Device Code
    safe_print(f"[{i}][1] Meminta OAuth Device Code resmi...")
    try:
        dev_res = request_device_code()
    except Exception as e:
        safe_print(f"[{i}][!] Gagal meminta device code: {e}")
        return False

    user_code = dev_res.get("user_code")
    device_code = dev_res.get("device_code")
    safe_print(f"[{i}][V] Device Code: {user_code}")

    token_box = {}
    stop_event = threading.Event()

    def _poller():
        try:
            tok = poll_device_token(device_code, interval=1, timeout=300)
            if tok and tok.get("access_token"):
                token_box["token"] = tok
                stop_event.set()
        except Exception:
            stop_event.set()

    poller_thread = threading.Thread(target=_poller, daemon=True)
    poller_thread.start()

    # 2. Setup Nama & Email
    FIRST_NAMES = ["James", "Michael", "David", "Alexander", "Daniel", "Emma", "Sophia", "Olivia", "Lucas", "Liam"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Taylor", "Anderson"]
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    full_name = f"{first_name} {last_name}"

    email_domain = config.get("email_domain", "example.com")
    prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    email = f"{prefix}@{email_domain}"
    password = "P@ss" + ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + "1!"

    # 3. Buka tab pendaftaran Camoufox
    page_xai = browser.new_page()
    page_xai.set_default_timeout(30000)

    signup_url = f"https://accounts.x.ai/sign-up?redirect=oauth2-provider&return_to=%2Foauth2%2Fdevice%3Fuser_code%3D{user_code}"
    safe_print(f"[{i}][2] Membuka pendaftaran xAI: {signup_url}...")
    try:
        page_xai.goto(signup_url, wait_until="domcontentloaded")
    except Exception as e:
        safe_print(f"[{i}][!] Gagal membuka URL signup: {e}")

    time.sleep(1)

    try:
        email_btn = page_xai.locator("button:has-text('email'), button:has-text('Email')").first
        if email_btn.count() > 0 and email_btn.is_visible():
            email_btn.click(timeout=2000)
            time.sleep(0.5)
    except Exception:
        pass

    # 4. Submit Email
    safe_print(f"[{i}][3] Mengisi email {email}...")
    try:
        page_xai.locator("input[type='email'], input[name='email'], input").first.fill(email)
        time.sleep(0.5)
        page_xai.locator("button:has-text('Next'), button[type='submit']").first.click()
    except Exception as e:
        safe_print(f"[{i}][!] Gagal submit email: {e}")
    time.sleep(2)

    # 5. Polling OTP
    worker_url = config.get("email_worker_url", "")
    otp = poll_for_otp(email, worker_url, timeout=35)
    if not otp:
        safe_print(f"[{i}][!] Gagal menerima OTP untuk {email}")
        try:
            page_xai.close()
        except Exception:
            pass
        return False

    safe_print(f"[{i}][V] OTP Diterima: {otp}")
    clean_otp = re.sub(r"\D", "", otp)

    inputs = page_xai.locator("input[type='text'], input[inputmode='numeric']")
    if inputs.count() >= 6:
        for idx, digit in enumerate(clean_otp[:6]):
            inputs.nth(idx).fill(digit)
            time.sleep(0.05)
    else:
        page_xai.locator("input").first.fill(clean_otp)
    time.sleep(1.5)

    # 6. Profil & Password
    safe_print(f"[{i}][4] Mengisi profil ({full_name}) & password...")
    try:
        page_xai.locator("input[name='givenName']").fill(first_name)
        time.sleep(0.05)
        page_xai.locator("input[name='familyName']").fill(last_name)
        time.sleep(0.05)
        page_xai.locator("input[name='password']").fill(password)
        time.sleep(0.3)
    except Exception:
        pass

    safe_print(f"[{i}][5] Mengklik Complete sign up...")
    try:
        page_xai.locator("button[type='submit']:has-text('Complete sign up'), button[type='submit']").first.click()
    except Exception:
        pass
    time.sleep(3)

    # 7. Otorisasi Device xAI di Browser
    safe_print(f"[{i}][6] Memproses otorisasi device xAI...")
    device_url = f"https://accounts.x.ai/oauth2/device?user_code={user_code}"
    try:
        page_xai.goto(device_url, wait_until="domcontentloaded", timeout=15000)
    except Exception:
        pass
    time.sleep(1)

    deadline = time.time() + 25
    while time.time() < deadline and not stop_event.is_set():
        try:
            page_xai.evaluate("() => document.querySelectorAll('#onetrust-consent-sdk, [id*=\"onetrust\"]').forEach(e => e.remove())")
        except Exception:
            pass

        try:
            cont = page_xai.locator("button:has-text('Continue'), button:has-text('Lanjutkan')").first
            if cont.count() > 0 and cont.is_visible():
                cont.click(force=True, timeout=1000)
                time.sleep(1)
        except Exception:
            pass

        try:
            allow = page_xai.locator("button:has-text('Allow'), button:has-text('Authorize'), button:has-text('Approve')").first
            if allow.count() > 0 and allow.is_visible():
                allow.click(force=True, timeout=1000)
                time.sleep(1)
                break
        except Exception:
            pass

        try:
            clicked = page_xai.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const b = btns.find(x => /^(allow|authorize|approve)$/i.test((x.innerText||'').trim()));
                if (b) { b.click(); return true; }
                const f = document.querySelector('form');
                if (f && (window.location.href.includes('consent') || document.body.innerText.includes('Allow'))) {
                    let a = f.querySelector('input[name=action]');
                    if (!a) { a = document.createElement('input'); a.type='hidden'; a.name='action'; f.appendChild(a); }
                    a.value = 'allow';
                    f.submit();
                    return true;
                }
                return false;
            }""")
            if clicked:
                break
        except Exception:
            pass

        time.sleep(0.8)

    # 8. Tunggu Token Poller
    safe_print(f"[{i}][7] Menunggu handshake otorisasi token...")
    poller_thread.join(timeout=25)

    if "token" in token_box:
        tok = token_box["token"]
        rf = tok.get("refresh_token", "")
        with FILE_LOCK:
            with open(ACCOUNTS_TXT, "a", encoding="utf-8") as f:
                f.write(f"{email}|{password}|{rf}\n")

        ok = insert_grok_token_to_9router(email, tok)
        try:
            page_xai.close()
        except Exception:
            pass
        return ok
    else:
        safe_print(f"[{i}][!] Gagal menangkap token OAuth untuk {email}")
        try:
            page_xai.close()
        except Exception:
            pass
        return False


def main():
    from camoufox.sync_api import Camoufox

    total_count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    num_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    config = load_config()

    print("=" * 65)
    print(f" [*] 9ROUTER GROK CLI - {total_count} AKUN DENGAN {num_workers} WORKER")
    print("=" * 65 + "\n")

    def _worker_task(worker_id: int, start_idx: int, end_idx: int):
        camoufox_args = {
            "headless": config.get("default_headless", True),
            "locale": "en-US",
            "geoip": True
        }
        if TURNSTILE_PATCH_DIR.exists():
            camoufox_args["addons"] = [str(TURNSTILE_PATCH_DIR)]

        with Camoufox(**camoufox_args) as browser:
            for acc_idx in range(start_idx, end_idx + 1):
                create_single_account(browser, acc_idx, total_count, config)
                time.sleep(1)

    threads = []
    chunk_size = (total_count + num_workers - 1) // num_workers
    for w in range(num_workers):
        s_idx = w * chunk_size + 1
        e_idx = min((w + 1) * chunk_size, total_count)
        if s_idx <= total_count:
            t = threading.Thread(target=_worker_task, args=(w + 1, s_idx, e_idx))
            threads.append(t)
            t.start()
            time.sleep(0.5)

    for t in threads:
        t.join()

    print("\n" + "=" * 65)
    print(" [★] PROSES SELESAI! Semua akun berhasil diproses ke 9Router.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
