#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ Grok CLI Cloudflare TempMail Engine
=====================================
Engine email disposable khusus berbasis Cloudflare Worker & Email Routing (Custom Domain).
Mendukung auto-extract OTP langsung via REST API (/code?email=xxx atau /api/code?email=xxx).

Panduan deployment worker mandiri tersedia di: cloudflare_worker/README.md
"""

import json
import os
import random
import re
import string
import subprocess
import sys
import time
from pathlib import Path
import requests

# UTF-8 console output for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CONFIG_FILE = Path(__file__).resolve().parent / "config.json"


def load_local_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


class CloudflareWorkerEngine:
    """Cloudflare Worker + Email Routing Catch-All Disposable Mail Engine."""

    def __init__(self, worker_url: str, domains: list[str] = None):
        url = worker_url.strip().rstrip("/")
        if url and not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        self.worker_url = url
        self.domains = [d.strip() for d in domains if d.strip()] if domains else []

    def _http_get(self, url: str, timeout: int = 8) -> tuple[int, str]:
        """HTTP GET tangguh menggunakan curl.exe di Windows (anti-10054) dan fallback ke requests."""
        if sys.platform == "win32":
            cmd = ["curl.exe", "-4", "--retry", "2", "-s", "-m", str(timeout), "-w", "\n%{http_code}", url]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 4)
                if res.returncode == 0 and res.stdout.strip():
                    parts = res.stdout.rsplit("\n", 1)
                    body_str = parts[0].strip() if len(parts) == 2 else res.stdout.strip()
                    code = int(parts[1].strip()) if len(parts) == 2 and parts[1].strip().isdigit() else 200
                    return code, body_str
            except Exception:
                pass

        try:
            r = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                timeout=timeout,
            )
            return r.status_code, r.text
        except Exception:
            return 0, ""

    def get_domains(self) -> list[str]:
        if self.domains:
            return self.domains
        # Coba ambil domain aktif dari worker
        for ep in ["/api/domains", "/domains"]:
            code, text = self._http_get(f"{self.worker_url}{ep}", timeout=6)
            if code == 200 and text:
                try:
                    data = json.loads(text)
                    if isinstance(data, list) and data:
                        doms = [d.get("domain") if isinstance(d, dict) else str(d) for d in data]
                        self.domains = [d for d in doms if d]
                        if self.domains:
                            return self.domains
                    elif isinstance(data, dict) and data.get("domains"):
                        self.domains = data["domains"]
                        return self.domains
                except Exception:
                    pass
        # Fallback host dari worker URL
        host = self.worker_url.split("//")[-1].split("/")[0].split(":")[0]
        return [host]

    def create_inbox(self, prefix: str = "grok", proxies: dict = None) -> tuple[str, str]:
        domains = self.get_domains()
        domain = random.choice(domains) if domains else "worker.local"
        rand_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        email = f"{prefix}_{rand_str}@{domain}".lower()
        return email, email

    def poll_otp(self, email: str, timeout: int = 60, interval: float = 1.5, proxies: dict = None) -> str | None:
        deadline = time.time() + timeout
        email_clean = email.strip().lower()

        while time.time() < deadline:
            # 1. Cek endpoint /code atau /api/code
            for ep in [f"/code?email={email_clean}", f"/api/code?email={email_clean}"]:
                code, text = self._http_get(f"{self.worker_url}{ep}", timeout=6)
                if code == 200 and text:
                    try:
                        data = json.loads(text)
                        if isinstance(data, dict):
                            otp = data.get("code") or data.get("otp")
                            if otp:
                                return str(otp).strip()
                    except Exception:
                        m = re.search(r"\b(\d{6})\b", text)
                        if m:
                            return m.group(1)

            # 2. Cek endpoint /raw atau /api/messages
            for ep in [f"/raw?email={email_clean}", f"/api/messages?email={email_clean}"]:
                code, text = self._http_get(f"{self.worker_url}{ep}", timeout=6)
                if code == 200 and text:
                    m_code = re.search(r"(\d{3}-\d{3})", text)
                    if m_code:
                        return m_code.group(1).replace("-", "")
                    m_six = re.search(r"\b(\d{6})\b", text)
                    if m_six:
                        return m_six.group(1)

            time.sleep(interval)

        return None


class GrokTempMail:
    """Unified TempMail Manager (Eksklusif Cloudflare Worker & Custom Domain)."""

    def __init__(self, worker_url: str = None, domains: list[str] = None):
        cfg = load_local_config()
        self.worker_url = (worker_url or cfg.get("worker_url") or os.environ.get("TEMPMAIL_WORKER_URL") or "").strip()
        self.worker_domains = domains or cfg.get("worker_domains") or []

        if self.worker_url:
            self.engine = CloudflareWorkerEngine(self.worker_url, self.worker_domains)
        else:
            self.engine = None

    def is_configured(self) -> bool:
        return bool(self.worker_url and self.engine)

    def get_info(self) -> str:
        if self.is_configured():
            dom_str = f" [Domain: {', '.join(self.worker_domains)}]" if self.worker_domains else ""
            return f"Cloudflare Worker ({self.worker_url}){dom_str}"
        return "BELUM DIKONFIGURASI (Wajib Cloudflare Worker Sendiri)"

    def create_inbox(
        self,
        prefix: str = "grok",
        preferred_proxy: str = None,
        proxies: dict = None,
    ) -> tuple[str, str, dict]:
        if not self.is_configured():
            raise RuntimeError(
                "Cloudflare Worker URL belum dikonfigurasi!\n"
                "  -> Buka run.bat lalu pilih menu [5] Konfigurasi Worker.\n"
                "  -> Panduan deploy worker mandiri gratis: cloudflare_worker/README.md"
            )

        email, _ = self.engine.create_inbox(prefix=prefix, proxies=proxies)
        return email, "worker", {"email": email, "worker_url": self.worker_url}

    def poll_otp(self, email: str, engine_type: str, ctx: dict, timeout: int = 50) -> str | None:
        if not self.is_configured():
            return None
        return self.engine.poll_otp(email, timeout=timeout)
