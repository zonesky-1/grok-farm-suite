"""Engine Inbox Sementara Zero-Setup untuk Menerima OTP xAI Grok."""
import json
import random
import re
import string
import time
import urllib.parse
import urllib.request
from typing import Optional

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}

def _http_req(url, data=None, headers=None, timeout=20, method=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode() if isinstance(data, (dict, list)) else data
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode(errors="ignore")

def _rand_str(n=10):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

class TempMailBox:
    """Manajer mailbox sementara (default: Mail.tm, fallback: tempmail.plus)."""

    def __init__(self, backend="mailtm"):
        self.backend = backend
        self.address = None
        self.password = None
        self.token = None

        if backend == "mailtm":
            try:
                self._init_mailtm()
            except Exception as e:
                # Fallback ke tempplus jika mail.tm mengalami kendala
                self.backend = "tempplus"
                self._init_tempplus()
        else:
            self._init_tempplus()

    def _init_mailtm(self):
        st, body = _http_req("https://api.mail.tm/domains")
        doms = json.loads(body).get("hydra:member", [])
        domain = doms[0]["domain"] if doms else "maxxspace.com"
        self.address = f"gk_{_rand_str(8)}@{domain}"
        self.password = f"P@ss_{_rand_str(10)}!"

        # Create account
        for _ in range(3):
            st, res = _http_req("https://api.mail.tm/accounts", {"address": self.address, "password": self.password})
            if st == 429:
                time.sleep(2)
                continue
            break

        # Get JWT token
        st, res = _http_req("https://api.mail.tm/token", {"address": self.address, "password": self.password})
        self.token = json.loads(res).get("token")
        if not self.token:
            raise RuntimeError(f"Gagal login ke mail.tm: {res}")

    def _init_tempplus(self):
        domain = "mailnu.com"
        self.address = f"gk_{_rand_str(8)}@{domain}"
        self.password = None

    def _fetch_messages(self):
        if self.backend == "mailtm":
            st, body = _http_req("https://api.mail.tm/messages?page=1", headers={"Authorization": f"Bearer {self.token}"})
            if st != 200:
                return []
            member = json.loads(body).get("hydra:member", [])
            out = []
            for m in member:
                mid = m.get("id")
                st2, b2 = _http_req(f"https://api.mail.tm/messages/{mid}", headers={"Authorization": f"Bearer {self.token}"})
                if st2 == 200:
                    d = json.loads(b2)
                    out.append({
                        "subject": d.get("subject", ""),
                        "from": d.get("from", {}).get("address", ""),
                        "text": d.get("text", "") or d.get("html", "")
                    })
            return out
        else:
            user = self.address.split("@")[0]
            st, body = _http_req(f"https://tempmail.plus/api/mails?email={user}&limit=10")
            if st != 200:
                return []
            d = json.loads(body)
            out = []
            for m in d.get("mail_list", []):
                mid = m.get("mail_id")
                body_txt = ""
                if mid:
                    try:
                        st2, b2 = _http_req(f"https://tempmail.plus/api/mails/{mid}?email={user}")
                        if st2 == 200:
                            d2 = json.loads(b2)
                            body_txt = d2.get("text", "") or d2.get("html", "")
                    except Exception:
                        pass
                out.append({"subject": m.get("subject", ""), "from": m.get("from", ""), "text": body_txt})
            return out

    def wait_for_otp(self, timeout=75, poll=3) -> Optional[str]:
        """Menunggu email masuk dari xAI dan mengekstrak 6-digit kode OTP."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            msgs = self._fetch_messages()
            for m in msgs:
                subject = m.get("subject", "")
                text = m.get("text", "")
                content = f"{subject}\n{text}"

                # Ekstrak pattern xAI OTP (biasanya 6 digit: "123456" atau "123-456")
                match = re.search(r'code[^0-9]{0,25}(\d{3}[-\s]?\d{3})', content, re.IGNORECASE)
                if match:
                    return re.sub(r'\D', '', match.group(1))

                match2 = re.search(r'(?<![#\w])(\d{6})(?![\w])', content)
                if match2:
                    return match2.group(1)

            time.sleep(poll)
        return None
