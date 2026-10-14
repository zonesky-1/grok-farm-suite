"""Shim mail.tm utk grok.py (Tempik API-nya 400/mati).
Cocok: create_inbox() / wait_otp(addr, timeout, since) / delete_inbox()."""
import sys
sys.path.insert(0, "/home/agentuser/.hermes/profiles/syadagentic/farm/captcha-tools")
from tempmail import TempBox


class TempikMail:
    def __init__(self):
        self._b = None

    def create_inbox(self):
        self._b = TempBox("tempplus")
        return self._b.address

    def wait_otp(self, addr, timeout=90, since=None, **kw):
        try:
            return self._b.wait_otp(seconds=timeout, poll=4) or ""
        except Exception:
            return ""

    def delete_inbox(self, addr):
        return None
