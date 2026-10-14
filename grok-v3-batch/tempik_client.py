import time
import json
import urllib.request
import urllib.parse
import re

_OTP_RE = re.compile(
    r'code[^0-9]{0,25}(\d{3}[-\s]?\d{3})', re.I)


def extract_otp(subject, body):
    """xAkun: 'SpaceXAI confirmation code: 699-696'. Regex 6-angka polos
    tertipu oleh hex color CSS '#333333' di body email — karenanya subject
    lebih dulu, dan body menolak angka yang didahului '#'."""
    match = _OTP_RE.search(subject or '')
    if not match:
        match = re.search(r'(?<![#\w])(\d{3}[-\s]?\d{3})(?![\w])',
                          f"{subject or ''}\n{body or ''}")
    return re.sub(r'\D', '', match.group(1)) if match else ''


class Tempik:
    def __init__(self, api_url, domain):
        self.api_url = api_url.rstrip('/')
        self.domain = domain
        self.session_id = None
        self._ensure_session()

    def _headers(self):
        h = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/json'
        }
        if self.session_id:
            h['x-session-id'] = self.session_id
        return h

    def _ensure_session(self):
        req = urllib.request.Request(
            f"{self.api_url}/api/session",
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode('utf-8'))
                self.session_id = data.get('sessionId')
        except Exception:
            pass

    def create_inbox(self):
        """Buat inbox disposable baru lewat /api/inboxes"""
        if not self.session_id:
            self._ensure_session()

        payload = json.dumps({'domain': self.domain}).encode('utf-8')
        req = urllib.request.Request(
            f"{self.api_url}/api/inboxes",
            data=payload,
            headers=self._headers(),
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode('utf-8'))
            return data.get('address')

    def wait_otp(self, addr, timeout=90, since=None):
        """Poll pesan di inbox dan ambil OTP 6 digit.

        xAI mengirim kode sebagai '699-696' (pakai strip), dan body email
        berisi CSS hex color seperti #333333 yang ikut cocok dengan \\d{6}.
        Karena itu: subject didahulukan, dan hex color di-exclude.
        """
        start = time.time()
        encoded_addr = urllib.parse.quote(addr)
        url = f"{self.api_url}/api/inboxes/{encoded_addr}/messages"

        while time.time() - start < timeout:
            try:
                req = urllib.request.Request(url, headers=self._headers())
                with urllib.request.urlopen(req, timeout=10) as r:
                    msgs = json.loads(r.read().decode('utf-8'))
                    if isinstance(msgs, list):
                        for m in msgs:
                            code = extract_otp(m.get('subject'), m.get('body'))
                            if code:
                                return code
            except Exception:
                pass
            time.sleep(2)
        return None

    def delete_inbox(self, addr):
        """Hapus inbox dari server"""
        encoded_addr = urllib.parse.quote(addr)
        req = urllib.request.Request(
            f"{self.api_url}/api/inboxes/{encoded_addr}",
            headers=self._headers(),
            method='DELETE'
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                pass
        except Exception:
            pass
