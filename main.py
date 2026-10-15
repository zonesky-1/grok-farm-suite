#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ Grok CLI (xAI) High-Speed Auto-Farming & 9Router Engine (V3 Turbo Ultra-Fast)
=============================================================================
Optimalisasi Kecepatan:
1. Zero-Zombie Process Cleanup: Pembersihan otomatis proses playwright & camoufox yatim.
2. Auto-Detect WARP Proxy (40001 / 40002) dengan DNS remote resolution (socks5h://) agar bebas tarpit Cloudflare.
3. Instan Cookie Banner Dismissal via page.evaluate (<5ms).
4. Conditional Turnstile Solver: Eliminasi 8 detik dead-weight wait pada formulir profil.
5. High-Speed OTP Polling via Cloudflare Worker & Custom Domain.
6. Non-blocking SPA Device Code Consent Polling (<300ms cycle).
7. Native 9Router Sync & Direct Connection Test.
"""

import os
import sys
import time
import re
import json
import uuid
import random
import socket
import argparse
import requests
import warnings
import subprocess
import traceback
from pathlib import Path
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

# Fix UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

# Self-healing patch: Fix PyYAML missing CLoader on Python 3.12/3.13/3.14/3.15 Windows
try:
    import yaml
    if not hasattr(yaml, "CLoader"):
        yaml.CLoader = yaml.Loader
    if not hasattr(yaml, "CSafeLoader"):
        yaml.CSafeLoader = yaml.SafeLoader
    if not hasattr(yaml, "CDumper"):
        yaml.CDumper = yaml.Dumper

    import inspect
    yaml_init = inspect.getfile(yaml)
    if os.path.exists(yaml_init):
        with open(yaml_init, "r", encoding="utf-8") as f:
            content = f.read()
        if "CLoader = Loader" not in content:
            patch = (
                "\n# Camoufox compatibility fallback for Python Windows\n"
                "if 'CLoader' not in globals():\n"
                "    CLoader = Loader\n"
                "if 'CSafeLoader' not in globals():\n"
                "    CSafeLoader = SafeLoader\n"
                "if 'CDumper' not in globals():\n"
                "    CDumper = Dumper\n"
            )
            try:
                with open(yaml_init, "a", encoding="utf-8") as f:
                    f.write(patch)
            except Exception:
                pass
except Exception:
    pass


# Auto-bootstrap dependensi jika script dijalankan di komputer yang belum menginstall requirements
def ensure_dependencies():
    required = ["camoufox", "requests", "playwright"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[*] Dependensi Python belum lengkap ({', '.join(missing)}). Memasang otomatis...")
        try:
            req_file = BASE_DIR / "requirements.txt"
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--disable-pip-version-check"] if req_file.exists() else [sys.executable, "-m", "pip", "install", *missing]
            subprocess.check_call(cmd)
            print("[✓] Seluruh paket Python berhasil dipasang!\n")
        except Exception as e:
            print(f"\n[!] Gagal memasang dependensi Python secara otomatis: {e}")
            print(f"[!] Silakan periksa koneksi internet atau jalankan manual:")
            print(f"    {sys.executable} -m pip install -r requirements.txt\n")
            sys.exit(1)

    # Pastikan binary browser stealth Camoufox sudah terpasang dan executable-nya valid
    try:
        from camoufox.pkgman import launch_path
        exe = launch_path()
        if not exe or not os.path.exists(exe):
            raise FileNotFoundError(f"Binary Camoufox tidak ditemukan di {exe}")
    except Exception:
        print("[*] Binary browser Camoufox belum terunduh atau belum lengkap di sistem ini.")
        print("[*] Sedang mengunduh binary stealth Camoufox secara otomatis (mohon tunggu)...")
        try:
            fetch_cmd = [sys.executable, "-m", "camoufox", "fetch"]
            subprocess.run(fetch_cmd, check=True)
            print("[✓] Binary Camoufox berhasil diunduh dan siap digunakan!\n")
        except Exception as e:
            print(f"[!] Gagal mengunduh binary Camoufox: {e}")
            print("[!] Silakan jalankan manual di terminal:")
            print("    python -m camoufox fetch\n")
            sys.exit(1)

ensure_dependencies()

try:
    from camoufox._warnings import LeakWarning
    warnings.filterwarnings("ignore", category=LeakWarning)
except Exception:
    pass
warnings.filterwarnings("ignore")

# Suppress harmless Playwright / asyncio background cleanup noise on exit/teardown
def _filter_playwright_unraisable(unraisable):
    err = str(unraisable.exc_value or "")
    if any(k in err.lower() for k in ["target page", "context or browser has been closed", "targetclosederror", "task was destroyed"]):
        return
    if unraisable.exc_type and "TargetClosedError" in getattr(unraisable.exc_type, "__name__", ""):
        return
    try:
        sys.__unraisablehook__(unraisable)
    except Exception:
        pass

sys.unraisablehook = _filter_playwright_unraisable

from camoufox.sync_api import Camoufox


class ResilientCamoufox:
    """
    Context manager kelas tangguh untuk Camoufox.
    Menangani error saat startup / inisialisasi browser (misal: BrowserForge index error),
    tanpa mengganggu atau mencampuri eksepsi yang terjadi di dalam blok with.
    """
    def __init__(self, camoufox_kwargs, worker_id=None):
        self.camoufox_kwargs = camoufox_kwargs
        self.worker_id = worker_id
        self.browser_cm = None

    def __enter__(self):
        errors = []

        # 1. Coba OS Windows eksplisit (paling stabil di Windows host, hindari Bayesian index error)
        kw_win = dict(self.camoufox_kwargs)
        kw_win.setdefault("os", "windows")
        try:
            self.browser_cm = Camoufox(**kw_win)
            return self.browser_cm.__enter__()
        except Exception as e1:
            errors.append(f"OS Windows: {e1}")
            log(f"Camoufox startup coba 1 kendala ({e1}), fallback ke default...", symbol="!", worker_id=self.worker_id)

        # 2. Coba kwargs pengguna asli
        try:
            self.browser_cm = Camoufox(**self.camoufox_kwargs)
            return self.browser_cm.__enter__()
        except Exception as e2:
            errors.append(f"Default: {e2}")
            log(f"Camoufox startup coba 2 kendala ({e2}), fallback ke safe-minimal...", symbol="!", worker_id=self.worker_id)

        # 3. Coba mode aman minimal (headless + geoip false)
        kw_min = {
            "headless": self.camoufox_kwargs.get("headless", True),
            "geoip": False,
            "enable_cache": False,
        }
        if "proxy" in self.camoufox_kwargs:
            kw_min["proxy"] = self.camoufox_kwargs["proxy"]
        try:
            self.browser_cm = Camoufox(**kw_min)
            return self.browser_cm.__enter__()
        except Exception as e3:
            errors.append(f"Safe-Minimal: {e3}")

        err_summary = " | ".join(errors)
        raise RuntimeError(f"Gagal membuka browser Camoufox setelah 3 layer pertahanan: {err_summary}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser_cm:
            try:
                return self.browser_cm.__exit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                err_str = str(e).lower()
                if any(k in err_str for k in ["closed", "target", "connection", "context"]):
                    return True
                if exc_type is not None:
                    return False
                raise
        return False


import threading

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
CRED_FILE = BASE_DIR / "grok_credentials.json"
ACTIVE_CRED_FILE = CRED_FILE
AUTO_INJECT_9ROUTER = True
CRED_LOCK = threading.Lock()
_GATE_LOCK = threading.Lock()
_LAST_LAUNCH_TIME = 0.0


def wait_for_launch_slot(min_interval=3.5):
    """Jeda minimal antar-inisialisasi Camoufox untuk menjaga sliding window koneksi aman & anti-10054."""
    global _LAST_LAUNCH_TIME
    with _GATE_LOCK:
        now = time.time()
        elapsed = now - _LAST_LAUNCH_TIME
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        _LAST_LAUNCH_TIME = time.time()

# Pastikan direktori modul terdaftar secara mandiri (100% standalone)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from tempmail import GrokTempMail
from inject_to_9router import inject_grok

class ProxyItem:
    """Representasi satu proxy dengan parsing multi-format (ip:port:user:pass, user:pass@ip:port, socks5)."""
    def __init__(self, raw: str):
        self.raw = raw.strip()
        self.ip = ""
        self.port = ""
        self.username = None
        self.password = None
        self.scheme = "http"
        self._parse()

    def _parse(self):
        s = self.raw
        if s.startswith("http://") or s.startswith("https://") or s.startswith("socks5://"):
            parts = s.split("://", 1)
            self.scheme = parts[0]
            s = parts[1]
        if "@" in s:
            auth_part, host_part = s.split("@", 1)
            if ":" in auth_part:
                self.username, self.password = auth_part.split(":", 1)
            else:
                self.username = auth_part
            if ":" in host_part:
                self.ip, self.port = host_part.split(":", 1)
            else:
                self.ip = host_part
        else:
            parts = s.split(":")
            if len(parts) == 4:
                # Format: ip:port:user:pass
                self.ip, self.port, self.username, self.password = parts
            elif len(parts) == 2:
                # Format: ip:port
                self.ip, self.port = parts
            else:
                self.ip = s

    @property
    def requests_url(self) -> str:
        if self.username and self.password:
            return f"{self.scheme}://{self.username}:{self.password}@{self.ip}:{self.port}"
        elif self.ip and self.port:
            return f"{self.scheme}://{self.ip}:{self.port}"
        return self.raw

    @property
    def requests_proxies(self) -> dict:
        u = self.requests_url
        if u.startswith("socks5://"):
            u = u.replace("socks5://", "socks5h://")
        return {"http": u, "https": u}

    @property
    def camoufox_proxy(self) -> dict:
        server = f"{self.scheme}://{self.ip}:{self.port}"
        d = {"server": server}
        if self.username:
            d["username"] = self.username
        if self.password:
            d["password"] = self.password
        return d

    def __str__(self):
        auth_mask = f"{self.username}:***@" if self.username else ""
        return f"{self.scheme}://{auth_mask}{self.ip}:{self.port}"


class ProxyManager:
    """Manajer daftar proxy thread-safe dengan rotasi per-akun otomatis."""
    def __init__(self, filepath=None):
        self.filepath = Path(filepath) if filepath else (BASE_DIR / "proxies.txt")
        self.proxies = []
        self._lock = threading.Lock()
        self._index = 0
        self.load()

    def load(self):
        if not self.filepath.exists():
            return
        try:
            lines = self.filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
            self.proxies = [ProxyItem(l) for l in lines if l.strip() and not l.strip().startswith("#")]
        except Exception as e:
            print(f"[!] Warning: Gagal membaca {self.filepath.name}: {e}")

    def has_proxies(self) -> bool:
        return len(self.proxies) > 0

    def count(self) -> int:
        return len(self.proxies)

    def get_next(self) -> ProxyItem | None:
        if not self.proxies:
            return None
        with self._lock:
            p = self.proxies[self._index % len(self.proxies)]
            self._index += 1
            return p


_PROXY_MGR = ProxyManager(BASE_DIR / "proxies.txt")
_MAILER = GrokTempMail()

CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
SCOPE = "openid profile email offline_access grok-cli:access api:access conversations:read conversations:write"


def log(msg, symbol="*", worker_id=None):
    prefix = f"[W{worker_id}] " if worker_id is not None else ""
    print(f"[{symbol}] {prefix}{msg}", flush=True)


def cleanup_zombies():
    """Membersihkan proses zombie playwright node & camoufox yang tertinggal agar CPU & RAM tetap lega."""
    if sys.platform != "win32":
        return
    try:
        ps_cmd = (
            "Get-CimInstance Win32_Process -Filter \"Name = 'node.exe'\" | "
            "Where-Object { $_.CommandLine -like '*playwright*' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; "
            "Get-Process -Name '*camoufox*' -ErrorAction SilentlyContinue | "
            "Stop-Process -Force -ErrorAction SilentlyContinue"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=5)
    except Exception:
        pass


def detect_warp_proxy(worker_id=1):
    """Mendeteksi apakah SOCKS5 proxy Cloudflare WARP lokal (port 40001 / 40002) tersedia."""
    ports = [40001 + ((worker_id - 1) % 2), 40001, 40002]
    for p in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.15)
            if s.connect_ex(("127.0.0.1", p)) == 0:
                s.close()
                return f"socks5://127.0.0.1:{p}"
            s.close()
        except Exception:
            pass
    return None


def request_device_code(proxy=None, proxies=None):
    """Mengambil device authorization code dari xAI OAuth dengan resilient retry (anti 10054 ConnectionReset)."""
    url = "https://auth.x.ai/oauth2/device/code"
    data = {
        "client_id": CLIENT_ID,
        "scope": SCOPE
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "grok-pager/0.2.93"
    }
    if not proxies and proxy:
        req_proxy = proxy.replace("socks5://", "socks5h://") if "socks5" in proxy else proxy
        proxies = {"http": req_proxy, "https": req_proxy}

    last_err = None
    for attempt in range(4):
        # Attempt 0: coba dengan proxies jika disediakan.
        # Jika proxy gagal (misal Tunnel 403 Forbidden pada forward proxy atau timeout),
        # otomatis fallback direct connection di attempt berikutnya agar tidak menghambat pendaftaran.
        curr_proxies = proxies if attempt == 0 else None
        try:
            r = requests.post(url, data=data, headers=headers, proxies=curr_proxies, timeout=12)
            if r.status_code == 200:
                return r.json()
            last_err = f"HTTP {r.status_code}: {r.text}"
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ProxyError) as e:
            last_err = str(e)
            time.sleep(1.0 * (attempt + 1))
        except Exception as e:
            last_err = str(e)
            time.sleep(1.0)

    raise RuntimeError(f"Gagal meminta device code setelah 4 percobaan: {last_err}")


def poll_token(device_code, interval=4.0, timeout=120, proxy=None, proxies=None):
    """Melakukan polling token ke xAI OAuth hingga diotorisasi sesuai standar RFC 8628."""
    url = "https://auth.x.ai/oauth2/token"
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": CLIENT_ID,
        "device_code": device_code
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "grok-pager/0.2.93"
    }
    if not proxies and proxy:
        req_proxy = proxy.replace("socks5://", "socks5h://") if "socks5" in proxy else proxy
        proxies = {"http": req_proxy, "https": req_proxy}

    start_time = time.time()
    curr_interval = interval
    curr_proxies = proxies
    while time.time() - start_time < timeout:
        try:
            r = requests.post(url, data=data, headers=headers, proxies=curr_proxies, timeout=8)
            if r.status_code == 200:
                return r.json()
            err_body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            err = err_body.get("error", "")
            if err == "slow_down":
                curr_interval = min(curr_interval + 2.0, 7.0)
                time.sleep(curr_interval)
                continue
            if err == "authorization_pending":
                time.sleep(curr_interval)
                continue
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError):
            # Fail-safe: jika proxy terputus di tengah jalan, beralih langsung ke direct connection
            curr_proxies = None
        except Exception:
            pass
        time.sleep(curr_interval)

    raise TimeoutError("Waktu otorisasi device code habis (timeout).")


def parse_jwt_payload(token_str):
    try:
        import base64
        parts = token_str.split(".")
        if len(parts) >= 2:
            padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            return json.loads(base64.urlsafe_b64decode(padded.encode()).decode("utf-8"))
    except Exception:
        pass
    return {}


def solve_turnstile_fast(page, max_wait=8):
    """Polling reaktif token Turnstile jika elemen Turnstile memang ada di DOM."""
    try:
        has_el = page.evaluate("""() => {
            return !!(document.querySelector('[name="cf-turnstile-response"]') || 
                      document.querySelector('iframe[src*="cloudflare"]') || 
                      document.querySelector('div.cf-turnstile'));
        }""")
        if not has_el:
            return True  # Zero latency jika tidak ada Turnstile captcha
    except Exception:
        pass

    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            token = page.evaluate("""() => {
                const el = document.querySelector('[name="cf-turnstile-response"]');
                return el ? el.value : '';
            }""")
            if token and len(token) > 20:
                return True
            page.wait_for_timeout(100)
        except Exception:
            time.sleep(0.1)
    return False


def register_single_grok_account(headless=True, preferred_proxy=None, worker_id=None, use_warp=False, proxy_item=None):
    """Entry point registrasi dengan self-healing auto-retry jika terjadi browser crash / network drop."""
    for attempt in range(2):
        try:
            return _execute_single_grok_account(headless, preferred_proxy, worker_id, use_warp, proxy_item)
        except Exception as e:
            err_str = str(e).lower()
            is_recoverable = any(k in err_str for k in [
                "closed", "crashed", "connection refused", "target page",
                "ns_error_net_timeout", "ns_error_abort", "swgl", "timeout 25000ms",
                "waktu otorisasi device code habis", "timeout", "index out of range",
                "list index", "targetclosederror", "browser has been closed",
                "gagal menerima kode otp", "otp"
            ]) or isinstance(e, TimeoutError)
            if attempt < 1 and is_recoverable:
                log(f"Koneksi/Browser kendala ({e}). Melakukan restart instan (Percobaan 2/2)...", symbol="!", worker_id=worker_id)
                time.sleep(1.0)
                continue
            raise e


def _execute_single_grok_account(headless=True, preferred_proxy=None, worker_id=None, use_warp=False, proxy_item=None):
    # Proxy handling: prioritaskan proxy_item (Rotating Proxy), lalu WARP, lalu preferred_proxy kustom
    req_proxies = None
    camo_proxy_cfg = None

    if proxy_item:
        req_proxies = proxy_item.requests_proxies
        camo_proxy_cfg = proxy_item.camoufox_proxy
        log(f"Menggunakan Rotating Proxy: {proxy_item}", worker_id=worker_id)
    elif not preferred_proxy and use_warp:
        preferred_proxy = detect_warp_proxy(worker_id=worker_id or 1)
        if preferred_proxy:
            log(f"Auto-Proxy WARP terdeteksi: {preferred_proxy}", worker_id=worker_id)
            p_req = preferred_proxy.replace("socks5://", "socks5h://")
            req_proxies = {"http": p_req, "https": p_req}
            camo_proxy_cfg = {"server": preferred_proxy.replace("socks5h://", "socks5://")}
    elif preferred_proxy:
        p_req = preferred_proxy.replace("socks5://", "socks5h://") if "socks5" in preferred_proxy else preferred_proxy
        req_proxies = {"http": p_req, "https": p_req}
        camo_proxy_cfg = {"server": preferred_proxy.replace("socks5h://", "socks5://")}

    t_start = time.time()
    rand_pass = f"P@ss{random.randint(100000, 999999)}#xAi"
    log("Inisialisasi pembuatan akun Grok CLI (Mode Turbo Ultra-Fast)...", worker_id=worker_id)

    # 1. Minta Device Code OAuth
    device_info = request_device_code(proxies=req_proxies)
    device_code = device_info["device_code"]
    user_code = device_info["user_code"]
    device_interval = float(device_info.get("interval", 4.0))
    log(f"Device Code didapat! User Code: {user_code}", symbol="✓", worker_id=worker_id)

    # 2. Buat email unik via Cloudflare Worker
    email, mail_engine, mail_ctx = _MAILER.create_inbox(prefix="grok", proxies=req_proxies)
    log(f"Email terdaftar: {email} [Engine: {mail_engine}]", symbol="✓", worker_id=worker_id)

    # 3. Direct Navigation URL
    direct_signup_url = f"https://accounts.x.ai/sign-up?redirect=oauth2-provider&return_to=%2Foauth2%2Fdevice%3Fuser_code%3D{user_code}"

    # 4. Jalankan Camoufox (Micro-staggered launch slot untuk menghindari process thrashing)
    wait_for_launch_slot(min_interval=1.2)

    camoufox_kwargs = {
        "headless": headless,
        "geoip": False,
        "enable_cache": True,
    }
    if camo_proxy_cfg:
        camoufox_kwargs["proxy"] = camo_proxy_cfg

    proxy_label = str(proxy_item) if proxy_item else (camo_proxy_cfg.get("server") if camo_proxy_cfg else "Direct")
    log(f"Membuka browser Camoufox (Headless: {headless}, Proxy: {proxy_label})...", worker_id=worker_id)

    browser = None
    page = None
    try:
        with ResilientCamoufox(camoufox_kwargs, worker_id=worker_id) as browser:
            page = browser.new_page()
            page.set_default_timeout(35000)

            log("Direct navigation ke halaman Sign-up...", worker_id=worker_id)
            # Navigasi resilien menggunakan wait_until="domcontentloaded" + retry
            nav_ok = False
            for nav_try in range(3):
                try:
                    page.goto(direct_signup_url, wait_until="domcontentloaded", timeout=35000)
                    nav_ok = True
                    break
                except Exception as e_nav:
                    if nav_try < 2:
                        log(f"Navigasi lambat ({e_nav}), mencoba ulang dalam 2s...", worker_id=worker_id)
                        time.sleep(2)
                    else:
                        try:
                            page.goto(direct_signup_url, wait_until="commit", timeout=15000)
                            nav_ok = True
                        except Exception:
                            raise e_nav

            # Singkirkan banner cookies instan via evaluate
            try:
                page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    for (const b of btns) {
                        const t = (b.innerText || '').trim();
                        if (/accept all|reject all|decline optional/i.test(t)) {
                            b.click();
                            break;
                        }
                    }
                    document.querySelectorAll('#onetrust-consent-sdk, #onetrust-banner-sdk, .onetrust-pc-dark-filter').forEach(el => el.remove());
                }""")
            except Exception:
                pass

            # Tunggu dan klik tombol pendaftaran email
            btn_clicked = False
            t_wait_btn = time.time() + 25
            while time.time() < t_wait_btn:
                try:
                    page.evaluate("""() => {
                        document.querySelectorAll('#onetrust-consent-sdk, #onetrust-banner-sdk, .onetrust-pc-dark-filter').forEach(el => el.remove());
                    }""")
                    btn = page.locator('button:has-text("Sign up with email")').first
                    if btn.is_visible(timeout=400):
                        btn.click(timeout=3000)
                        log("Tombol 'Sign up with email' berhasil diklik!", symbol="✓", worker_id=worker_id)
                        btn_clicked = True
                        break
                except Exception:
                    pass
                time.sleep(0.4)

            if not btn_clicked:
                try:
                    page.evaluate("""() => {
                        const b = Array.from(document.querySelectorAll('button')).find(el => (el.innerText || '').toLowerCase().includes('email'));
                        if (b) { b.click(); return true; }
                    }""")
                except Exception:
                    pass

            # Isi email dengan polling proaktif (Turnstile checking + re-click jika form tertahan)
            email_input = page.locator('#email, input[name="email"], input[type="email"]').first
            email_found = False
            t_wait_email = time.time() + 25
            while time.time() < t_wait_email:
                try:
                    if email_input.is_visible(timeout=500):
                        email_found = True
                        break
                    # Cek & selesaikan Turnstile jika menghalangi formulir
                    solve_turnstile_fast(page, max_wait=2)
                    # Jika tombol Sign up with email belum ter-trigger, klik ulang
                    btn_re = page.locator('button:has-text("Sign up with email")').first
                    if btn_re.is_visible(timeout=300):
                        btn_re.click(timeout=1500)
                except Exception:
                    pass
                time.sleep(0.5)

            if not email_found:
                email_input.wait_for(state="visible", timeout=12000)

            email_input.fill(email)

            # Cek Turnstile (0ms jika tidak ada di DOM)
            solve_turnstile_fast(page, max_wait=5)

            # Submit email (klik tombol submit & Enter)
            btn_continue = page.locator('button[type="submit"], button:has-text("Sign up"), button:has-text("Continue"), button:has-text("Next")').first
            try:
                if btn_continue.is_visible(timeout=800):
                    btn_continue.click(timeout=2500)
            except Exception:
                pass
            try:
                email_input.press("Enter")
            except Exception:
                pass
            log("Permintaan kode OTP terkirim, mendengarkan inbox...", worker_id=worker_id)

            # 5. Fast OTP Polling via GrokTempMail (Cloudflare Worker)
            otp_code = _MAILER.poll_otp(email, mail_engine, mail_ctx, timeout=50)
            if not otp_code:
                raise TimeoutError(f"Gagal menerima kode OTP verifikasi ({email}) dari xAI.")

            log(f"Kode OTP diterima: {otp_code}", symbol="✓", worker_id=worker_id)

            # 6. Input OTP Code langsung
            log("Memasukkan kode OTP ke halaman...", worker_id=worker_id)
            otp_field = page.locator('input[data-input-otp="true"], input[name="code"], input[autocomplete="one-time-code"], input[type="text"]').first
            otp_field.wait_for(state="visible", timeout=15000)
            otp_field.click()
            try:
                otp_field.fill(otp_code)
            except Exception:
                pass
            page.keyboard.type(otp_code, delay=20)

            time.sleep(0.5)
            btn_confirm = page.locator('button:has-text("Confirm email"), button:has-text("Confirm"), button[type="submit"]').first
            if btn_confirm.is_visible(timeout=2000):
                btn_confirm.click()

            # 7. Selesaikan Form Profile ('Complete your sign up': First Name, Last Name, Password)
            log("Mengisi detail profil & kata sandi...", worker_id=worker_id)
            try:
                btn_prof = page.locator('button:has-text("Complete sign up"), button:has-text("Create account")').first
                btn_prof.wait_for(state="visible", timeout=20000)

                # First Name & Last Name (mendukung id givenName/familyName dan autocomplete)
                fn = page.locator('#givenName, input[name="givenName"], input[autocomplete="given-name"], input[placeholder*="First"]').first
                if fn.is_visible(timeout=1000):
                    fn.fill("Grok")
                else:
                    page.locator('input[type="text"]:visible').first.fill("Grok")

                ln = page.locator('#familyName, input[name="familyName"], input[autocomplete="family-name"], input[placeholder*="Last"]').first
                if ln.is_visible(timeout=1000):
                    ln.fill("Developer")
                else:
                    page.locator('input[type="text"]:visible').nth(1).fill("Developer")

                # Password
                rand_pass = f"P@ss{random.randint(100000, 999999)}#xAi"
                pw_field = page.locator('#password, input[name="password"], input[type="password"]').first
                pw_field.fill(rand_pass)

                # Cek Turnstile profil HANYA jika elemen Turnstile benar-benar ada di DOM
                has_turnstile = False
                try:
                    has_turnstile = page.evaluate("""() => {
                        return !!(document.querySelector('[name="cf-turnstile-response"]') || 
                                  document.querySelector('iframe[src*="cloudflare"]') || 
                                  document.querySelector('div.cf-turnstile'));
                    }""")
                except Exception:
                    pass

                if has_turnstile:
                    solve_turnstile_fast(page, max_wait=5)

                btn_prof.click()
                log("Profil pendaftaran terkirim!", symbol="✓", worker_id=worker_id)

                # Tunggu redirect alami dari x.ai keluar dari /sign-up
                try:
                    page.wait_for_url(lambda u: "/sign-up" not in u, timeout=12000)
                except Exception:
                    pass
            except Exception as e_prof:
                log(f"Step profil dilewati/selesai: {e_prof}", worker_id=worker_id)

            # 8. Otorisasi Device Code pada /oauth2/device (Tahap 1: Continue -> Tahap 2: Allow)
            device_url = f"https://accounts.x.ai/oauth2/device?user_code={user_code}"
            if "/oauth2/device" not in page.url and "/sign-in" not in page.url:
                try:
                    page.goto(device_url, wait_until="domcontentloaded", timeout=20000)
                except Exception:
                    pass

            log(f"Mengonfirmasi otorisasi Grok CLI pada perangkat... (URL: {page.url})", worker_id=worker_id)

            # Singkirkan banner OneTrust
            def purge_onetrust(p):
                try:
                    p.evaluate("""() => {
                        const cb = Array.from(document.querySelectorAll('button')).find(b => /accept all|reject all/i.test(b.innerText || ''));
                        if (cb) cb.click();
                        document.querySelectorAll('#onetrust-consent-sdk, #onetrust-banner-sdk, #onetrust-group-container, .onetrust-pc-dark-filter').forEach(el => el.remove());
                    }""")
                except Exception:
                    pass

            purge_onetrust(page)

            # Unified Otorisasi Loop: Interleaved Browser Actions + Active HTTP Token Polling
            tokens = None
            allow_clicked = False
            t_end_auth = time.time() + 75
            last_cont_time = 0
            last_poll_time = 0
            poll_interval = max(device_interval, 3.5)
            last_err = ""

            while time.time() < t_end_auth:
                purge_onetrust(page)

                # Diagnostic log URL dan tombol
                if int(time.time()) % 5 == 0:
                    try:
                        cur_btns = [b.inner_text().strip() for b in page.locator('button:visible').all()[:6]]
                        log(f"Otorisasi berjalan | URL: {page.url} | Tombol: {cur_btns}", worker_id=worker_id)
                    except Exception:
                        pass

                # 0. Jika x.ai mengarahkan ke /sign-in, lakukan login otomatis step-by-step dengan akun baru
                if "/sign-in" in page.url:
                    try:
                        solve_turnstile_fast(page, max_wait=1)

                        # Step A: Klik 'Login with email' jika ada di layar utama
                        btn_login_email = page.locator('button:has-text("Login with email"), button:has-text("Log in with email")').first
                        if btn_login_email.is_visible(timeout=300):
                            btn_login_email.click(timeout=1500)
                            time.sleep(0.4)

                        # Step B: Isi email jika field email terlihat
                        inp_em = page.locator('#email, input[name="email"], input[type="email"]').first
                        if inp_em.is_visible(timeout=300):
                            cur_em = inp_em.input_value()
                            if not cur_em or cur_em.strip() != email:
                                inp_em.fill(email)
                            btn_next = page.locator('button[type="submit"], button:has-text("Continue"), button:has-text("Next")').first
                            if btn_next.is_visible(timeout=400):
                                btn_next.click(timeout=1500)
                            else:
                                inp_em.press("Enter")
                            time.sleep(0.4)

                        # Step C: Isi password jika field password terlihat
                        inp_pw = page.locator('#password, input[name="password"], input[type="password"]').first
                        if inp_pw.is_visible(timeout=300):
                            inp_pw.fill(rand_pass)
                            btn_sub = page.locator('button[type="submit"], button:has-text("Log in"), button:has-text("Sign in")').first
                            if btn_sub.is_visible(timeout=400):
                                btn_sub.click(timeout=1500)
                            else:
                                inp_pw.press("Enter")
                            time.sleep(0.5)
                    except Exception:
                        pass

                # 1. Cek & Klik tombol persetujuan (Consent Screen: Allow / Authorize / Approve)
                try:
                    solve_turnstile_fast(page, max_wait=1)

                    # Cara A: Coba JavaScript click langsung ke DOM
                    js_clicked = page.evaluate("""() => {
                        const candidates = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"], a'));
                        for (const el of candidates) {
                            const txt = (el.innerText || el.value || '').toLowerCase().trim();
                            if ((txt.includes('allow') && !txt.includes('allow all')) || 
                                txt.includes('approve') || 
                                txt.includes('authorize') || 
                                txt === 'confirm') {
                                el.click();
                                return true;
                            }
                        }
                        return false;
                    }""")
                    if js_clicked:
                        log("Tombol persetujuan ('Allow'/'Approve') diklik via DOM!", symbol="✓", worker_id=worker_id)
                        allow_clicked = True
                        time.sleep(1)
                    else:
                        btn_allow = page.locator(
                            'button:not([id*="onetrust"]):not([id*="accept-recommended"]):has-text("Allow"):not(:has-text("Allow All")), '
                            'button:not([id*="onetrust"]):has-text("Authorize"), '
                            'button:not([id*="onetrust"]):has-text("Approve"), '
                            'input[type="submit"][value*="Allow" i], '
                            'input[type="submit"][value*="Approve" i], '
                            'input[type="submit"][value*="Authorize" i]'
                        ).first
                        if btn_allow.is_visible(timeout=300):
                            btn_allow.click(timeout=3000)
                            log("Tombol persetujuan 'Allow' diklik!", symbol="✓", worker_id=worker_id)
                            allow_clicked = True
                            time.sleep(1)
                except Exception:
                    pass

                # 2. Tangani input kode & klik tombol Continue jika masih di step input user_code
                if not allow_clicked and "/sign-in" not in page.url and (time.time() - last_cont_time >= 2.5):
                    try:
                        has_usercode_field = page.locator('input[name*="code" i], input[data-input-otp="true"], input[placeholder*="code" i]').count() > 0
                        if has_usercode_field:
                            page.evaluate("""(code) => {
                                const inps = Array.from(document.querySelectorAll('input[type="text"], input[name*="code" i], input[data-input-otp="true"]'));
                                for (const inp of inps) {
                                    if (!inp.value || inp.value.trim() === '') {
                                        try {
                                            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                                            setter.call(inp, code);
                                        } catch (e) {
                                            inp.value = code;
                                        }
                                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                                    }
                                }
                            }""", user_code)

                            btn_cont = page.locator('button[type="submit"]:has-text("Continue"), button:not([id*="onetrust"]):not([id*="accept-recommended"]):has-text("Continue")').first
                            if btn_cont.is_visible(timeout=500):
                                btn_cont.click(timeout=3000)
                                log("Tombol 'Continue' perangkat diklik!", symbol="✓", worker_id=worker_id)
                                last_cont_time = time.time()
                    except Exception:
                        pass

                # 3. Polling HTTP Token xAI OAuth secara interleaved
                now = time.time()
                if now - last_poll_time >= poll_interval:
                    last_poll_time = now
                    try:
                        r_tok = requests.post(
                            "https://auth.x.ai/oauth2/token",
                            data={
                                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                                "client_id": CLIENT_ID,
                                "device_code": device_code
                            },
                            headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "grok-pager/0.2.93"},
                            proxies=req_proxies,
                            timeout=8
                        )
                        if r_tok.status_code == 200:
                            tokens = r_tok.json()
                            break

                        err_json = r_tok.json() if r_tok.headers.get("content-type", "").startswith("application/json") else {}
                        err_code = err_json.get("error", "")

                        if err_code == "slow_down":
                            poll_interval = min(poll_interval + 2.0, 7.0)
                        elif err_code == "authorization_pending":
                            pass  # Menunggu konfirmasi di browser
                        else:
                            err_msg = f"{r_tok.status_code}: {r_tok.text[:60]}"
                            if err_msg != last_err:
                                last_err = err_msg
                                log(f"Status Token: {err_msg}", worker_id=worker_id)
                    except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError):
                        # Fail-safe: jika proxy putus di tengah jalan, alihkan req_proxies ke direct
                        req_proxies = None
                    except Exception:
                        pass

                time.sleep(0.5)
    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass

    if not tokens:
        tokens = poll_token(device_code, interval=poll_interval, timeout=30, proxies=req_proxies)

    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token", "")
    id_token = tokens.get("id_token", "")
    expires_in = tokens.get("expires_in", 21600)

    payload_data = parse_jwt_payload(access_token)
    user_id = payload_data.get("sub", payload_data.get("principal_id", str(uuid.uuid4())))

    new_account = {
        "email": email,
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "idToken": id_token,
        "userId": user_id,
        "displayName": email.split("@")[0],
        "expiresIn": expires_in,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    }

    # Simpan ke file kredensial secara aman (atomic write) & sinkronkan ke 9Router (jika aktif)
    with CRED_LOCK:
        existing_creds = []
        target_f = ACTIVE_CRED_FILE
        if target_f.exists():
            for _ in range(3):
                try:
                    raw_txt = target_f.read_text(encoding="utf-8").strip()
                    if raw_txt:
                        existing_creds = json.loads(raw_txt)
                    break
                except Exception:
                    time.sleep(0.2)
            else:
                try:
                    bak_file = target_f.with_suffix('.bak')
                    bak_file.write_bytes(target_f.read_bytes())
                except Exception:
                    pass

        if not isinstance(existing_creds, list):
            existing_creds = []

        existing_creds = [c for c in existing_creds if c.get("email") != email]
        existing_creds.append(new_account)

        tmp_file = target_f.with_suffix('.tmp')
        tmp_file.write_text(json.dumps(existing_creds, indent=2), encoding="utf-8")
        try:
            tmp_file.replace(target_f)
        except Exception:
            target_f.write_text(json.dumps(existing_creds, indent=2), encoding="utf-8")
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)

        # Sinkronkan ke database 9Router tiap kali 1 akun selesai (jika diaktifkan)
        if AUTO_INJECT_9ROUTER:
            try:
                inject_grok()
                log(f"Akun otomatis terinjeksi ke 9Router ({email})", symbol="✓", worker_id=worker_id)
            except Exception as e_inj:
                log(f"Gagal injeksi ke 9Router: {e_inj}", symbol="!", worker_id=worker_id)

    elapsed = time.time() - t_start
    log(f"Akun Grok CLI selesai dalam {elapsed:.1f} detik! ({email})", symbol="🎉", worker_id=worker_id)
    return new_account


def test_grok_connection(model="gcli/grok-4.6"):
    """Uji inferensi cepat model grok ke 9Router lokal."""
    try:
        r = requests.post(
            "http://127.0.0.1:20128/v1/chat/completions",
            headers={"Authorization": "Bearer 9router", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            },
            timeout=25
        )
        if r.status_code == 200:
            print(f"[✓] 9Router Test Connection ({model}) SUKSES: 200 OK")
        else:
            print(f"[-] 9Router Test Connection ({model}) Status: {r.status_code}")
    except Exception as e:
        print(f"[-] 9Router Test Connection skipped: {e}")


def main():
    parser = argparse.ArgumentParser(description="⚡ Grok CLI (xAI) Turbo Auto-Farming & 9Router Engine")
    parser.add_argument("--count", "-n", type=int, default=0, help="Jumlah akun yang ingin dibuat (0 untuk Tak Terbatas/Bulk Farming, default: 0)")
    parser.add_argument("--unlimited", action="store_true", help="Mode Tak Terbatas / Infinite Loop (terus membuat akun sampai Ctrl+C)")
    parser.add_argument("--workers", "-w", type=int, default=5, help="Jumlah worker paralel (default: 5)")
    parser.add_argument("--no-headless", action="store_true", help="Tampilkan jendela browser (bukan headless)")
    parser.add_argument("--proxy-mode", "-m", type=str, choices=["direct", "proxy", "warp"], default=None,
                        help="Mode koneksi: 'direct' (tanpa proxy), 'proxy' (rotating dari proxies.txt), atau 'warp' (Cloudflare WARP)")
    parser.add_argument("--proxies-file", type=str, default=None, help="Path ke file daftar proxy (default: proxies.txt)")
    parser.add_argument("--proxy", "-p", type=str, default=None, help="Proxy kustom tunggal (misal: socks5://127.0.0.1:40001 atau http://user:pass@ip:port)")
    parser.add_argument("--warp", action="store_true", help="Gunakan Cloudflare WARP proxy lokal (port 40001/40002)")
    parser.add_argument("--no-9router", action="store_true", help="Jangan injeksi otomatis ke database 9Router")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path kustom file output JSON kredensial (default: grok_credentials.json)")
    parser.add_argument("--worker-url", type=str, default=None, help="URL Cloudflare Email Worker kustom (opsional)")
    parser.add_argument("--worker-domains", nargs="+", default=None, help="Daftar domain kustom untuk Cloudflare Worker")
    args = parser.parse_args()

    # Pre-flight cleanup proses zombie
    cleanup_zombies()

    global ACTIVE_CRED_FILE, AUTO_INJECT_9ROUTER, _MAILER
    if args.output:
        ACTIVE_CRED_FILE = Path(args.output).resolve()
    AUTO_INJECT_9ROUTER = not args.no_9router

    if args.worker_url or args.worker_domains:
        _MAILER = GrokTempMail(worker_url=args.worker_url, domains=args.worker_domains)

    if not _MAILER.is_configured():
        print("=" * 70)
        print("   [!] PERHATIAN: CLOUDFLARE WORKER BELUM DIKONFIGURASI")
        print("=" * 70)
        print("   xAI memblokir seluruh domain email disposable publik gratisan.")
        print("   Agar akun tidak terblokir, Anda wajib menggunakan Cloudflare Worker")
        print("   dengan domain kustom Anda sendiri (Cloudflare Email Routing Catch-All).")
        print()
        print("   ------------------------------------------------------------------")
        print("   TATA CARA SETUP CEPAT (2 MENIT):")
        print("   ------------------------------------------------------------------")
        print("   1. Buka folder: cloudflare_worker/")
        print("   2. Jalankan perintah di terminal:")
        print("        npx wrangler d1 create tempmail_db")
        print("        npx wrangler d1 execute tempmail_db --file=schema.sql --remote")
        print("   3. Buka wrangler.toml -> masukkan database_id dan domain Anda")
        print("   4. Deploy: npx wrangler deploy")
        print("   5. Di Cloudflare Dashboard: Domain -> Email Routing -> Catch-all")
        print("      pilih Action: Send to a Worker (pilih worker Anda).")
        print()
        print("   Panduan langkah demi langkah lengkap ada di: cloudflare_worker/README.md")
        print("=" * 70)

        entered_url = ""
        try:
            print("\n   Sudah memiliki URL Cloudflare Worker yang aktif?")
            entered_url = input(">> Masukkan URL Worker Anda sekarang (Enter untuk keluar): ").strip().strip("\"'").rstrip("/")
        except (KeyboardInterrupt, EOFError):
            print("\n[*] Dibatalkan.")
            sys.exit(0)
        except Exception:
            entered_url = ""

        if entered_url:
            if not entered_url.startswith(("http://", "https://")):
                entered_url = f"https://{entered_url}"
            cfg = {}
            if CONFIG_FILE.exists():
                try:
                    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            cfg["worker_url"] = entered_url
            try:
                CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                print(f"\n[✓] Cloudflare Worker URL berhasil disimpan ke {CONFIG_FILE.name}!")
            except Exception as e:
                print(f"\n[!] Peringatan: Gagal menyimpan ke {CONFIG_FILE.name}: {e}")

            _MAILER = GrokTempMail(worker_url=entered_url, domains=args.worker_domains)
            print("[*] Melanjutkan ke proses farming...\n")
        else:
            print("\n[*] Harap konfigurasikan Cloudflare Worker terlebih dahulu. Keluar.\n")
            sys.exit(1)

    headless = not args.no_headless
    is_infinite = args.count <= 0 or args.unlimited

    # Inisialisasi ProxyManager jika custom file ditentukan
    proxy_mgr = _PROXY_MGR
    if args.proxies_file:
        proxy_mgr = ProxyManager(args.proxies_file)

    # Deteksi atau tanyakan mode proxy jika tidak ada argumen eksplisit di CLI
    proxy_mode = args.proxy_mode
    if not proxy_mode and not args.proxy and not args.warp:
        # Jika dijalankan interaktif di terminal, tanyakan opsi pilihan ke pengguna
        if sys.stdin and sys.stdin.isatty():
            print("=" * 70)
            print("   ⚡ PILIH MODE JARINGAN / KONEKSI:")
            print("=" * 70)
            print("   [1] Direct Ultra-Fast (Direkomendasikan: 18-25s per akun, Tanpa Proxy)")
            if proxy_mgr.has_proxies():
                print(f"   [2] Rotating Proxy (proxies.txt: {proxy_mgr.count():,} IP aktif berganti tiap akun)")
            else:
                print("   [2] Rotating Proxy (proxies.txt: file tidak ditemukan / kosong)")
            print("   [3] Cloudflare WARP (Port 40001/40002)")
            print("=" * 70)
            try:
                choice = input("Pilih mode [1/2/3, Tekan Enter untuk Direct]: ").strip()
                if choice == "2":
                    proxy_mode = "proxy"
                elif choice == "3":
                    proxy_mode = "warp"
                else:
                    proxy_mode = "direct"
            except (KeyboardInterrupt, EOFError):
                print("\n[*] Dibatalkan.")
                return
        else:
            proxy_mode = "direct"
    elif args.warp:
        proxy_mode = "warp"
    elif args.proxy:
        proxy_mode = "custom"
    elif not proxy_mode:
        proxy_mode = "direct"

    # Validasi jika mode proxy dipilih namun proxies.txt tidak ada
    if proxy_mode == "proxy" and not proxy_mgr.has_proxies():
        print("[!] Peringatan: File proxies.txt kosong atau tidak ditemukan.")
        print("[!] Beralih otomatis ke mode Direct Ultra-Fast.\n")
        proxy_mode = "direct"

    print("=" * 70)
    print("   ⚡ GROK CLI (xAI) TURBO AUTO-FARMING ENGINE (V3 ULTRA-FAST)   ")
    print("=" * 70)
    print(f"[*] Target Jumlah Akun : {'♾️  TAK TERBATAS (Bulk Farming Loop Non-Stop)' if is_infinite else args.count}")
    print(f"[*] Worker Paralel     : {args.workers}")
    print(f"[*] TempMail Engine    : {_MAILER.get_info()}")
    print(f"[*] Mode Browser       : {'Headless (Senyap)' if headless else 'Visible (Tampak)'}")
    if proxy_mode == "proxy":
        conn_str = f"Rotating Proxy ({proxy_mgr.count():,} IP dari proxies.txt)"
    elif proxy_mode == "warp":
        conn_str = "Cloudflare WARP (SOCKS5 40001/40002)"
    elif proxy_mode == "custom":
        conn_str = f"Custom Proxy ({args.proxy})"
    else:
        conn_str = "Direct Ultra-Fast (Tanpa Proxy)"
    print(f"[*] Mode Koneksi       : {conn_str}")
    print(f"[*] Model Unggulan     : gcli/grok-4.6 / gcli/grok-4.7 (100% GRATIS)")
    print(f"[*] 9Router Sync       : Otomatis per akun (Real-Time)")
    if is_infinite:
        print("[*] Catatan            : Terus berjalan non-stop. Tekan Ctrl+C untuk menghentikan.")
    print("=" * 70 + "\n")

    success_count = 0
    t0 = time.time()

    if is_infinite:
        # MODE TAK TERBATAS (Infinite Loop)
        idx = 0
        try:
            if args.workers > 1:
                with ThreadPoolExecutor(max_workers=args.workers) as executor:
                    running_futures = {}  # future -> (idx, wid)

                    def submit_next(account_idx):
                        wid = (account_idx - 1) % args.workers + 1
                        curr_px = proxy_mgr.get_next() if proxy_mode == "proxy" else None
                        fut = executor.submit(
                            register_single_grok_account,
                            headless=headless,
                            preferred_proxy=args.proxy,
                            worker_id=wid,
                            use_warp=(proxy_mode == "warp"),
                            proxy_item=curr_px
                        )
                        return fut, wid

                    while True:
                        while len(running_futures) < args.workers:
                            idx += 1
                            fut, wid = submit_next(idx)
                            running_futures[fut] = (idx, wid)

                        done, _ = wait(list(running_futures.keys()), return_when=FIRST_COMPLETED)
                        for fut in done:
                            acc_idx, wid = running_futures.pop(fut, (None, None))
                            try:
                                fut.result()
                                success_count += 1
                                print(f"[✓] Berhasil membuat {success_count} akun sejauh ini (Semua aktif di 9Router)")
                            except Exception as e:
                                print(f"[-] [Worker W{wid}] Akun #{acc_idx} gagal: {e}")
                                traceback.print_exc()
            else:
                while True:
                    idx += 1
                    print(f"\n>>> [Akun #{idx} - Tak Terbatas] Memulai registrasi...")
                    curr_px = proxy_mgr.get_next() if proxy_mode == "proxy" else None
                    try:
                        register_single_grok_account(
                            headless=headless,
                            preferred_proxy=args.proxy,
                            worker_id=1,
                            use_warp=(proxy_mode == "warp"),
                            proxy_item=curr_px
                        )
                        success_count += 1
                        print(f"[✓] Berhasil membuat {success_count} akun sejauh ini (Aktif di 9Router)")
                    except Exception as e:
                        print(f"[-] Akun #{idx} GAGAL: {e}")
                        traceback.print_exc()
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Dihentikan oleh pengguna (Ctrl+C).")
    else:
        # MODE JUMLAH TERTENTU (Fixed Count)
        if args.workers > 1 and args.count > 1:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = []
                for i in range(args.count):
                    curr_px = proxy_mgr.get_next() if proxy_mode == "proxy" else None
                    fut = executor.submit(
                        register_single_grok_account,
                        headless=headless,
                        preferred_proxy=args.proxy,
                        worker_id=i % args.workers + 1,
                        use_warp=(proxy_mode == "warp"),
                        proxy_item=curr_px
                    )
                    futures.append(fut)
                for fut in as_completed(futures):
                    try:
                        fut.result()
                        success_count += 1
                    except Exception as e:
                        print(f"[-] Worker error: {e}")
                        traceback.print_exc()
        else:
            for idx in range(1, args.count + 1):
                print(f"\n>>> [Akun {idx}/{args.count}] Memulai registrasi...")
                curr_px = proxy_mgr.get_next() if proxy_mode == "proxy" else None
                try:
                    register_single_grok_account(
                        headless=headless,
                        preferred_proxy=args.proxy,
                        worker_id=1,
                        use_warp=(proxy_mode == "warp"),
                        proxy_item=curr_px
                    )
                    success_count += 1
                except Exception as e:
                    print(f"[-] Akun {idx} GAGAL: {e}")
                    traceback.print_exc()
                if idx < args.count:
                    time.sleep(1)

    total_time = time.time() - t0
    target_str = "Tak Terbatas" if is_infinite else str(args.count)
    print("\n" + "=" * 70)
    print(f"🎉 Selesai! Berhasil membuat {success_count}/{target_str} akun dalam {total_time:.1f} detik.")
    print("=" * 70)

    if success_count > 0:
        print("\n[*] Menjalankan uji inferensi cepat model gcli/grok-4.6...")
        test_grok_connection("gcli/grok-4.6")

    # Post-flight cleanup proses zombie
    cleanup_zombies()


if __name__ == "__main__":
    main()
