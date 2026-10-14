import time
import random
import string
import imaplib
import email as emailmod
import re

_OTP_RE = re.compile(r'code[^0-9]{0,25}(\d{3}[-\s]?\d{3})', re.I)

DOMAIN = 'arxpays.my.id'  # catch-all Cloudflare Email Routing -> GMAIL


def extract_otp(subject, body):
    match = _OTP_RE.search(subject or '')
    if not match:
        match = re.search(r'(?<![#\w])(\d{3}[-\s]?\d{3})(?![\w])',
                          f"{subject or ''}\n{body or ''}")
    return re.sub(r'\D', '', match.group(1)) if match else ''


class Tempik:
    GMAIL = 'arxdubai496@gmail.com'
    _PW = 'umxlkmcozmqrbpzw'

    def __init__(self, api_url, domain):
        self.api_url = api_url
        self.domain = DOMAIN or domain

    def create_inbox(self):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12)) \
            + '@' + self.domain

    def wait_otp(self, addr, timeout=90, since=None):
        """Ultra-fast search spesifik per recipient di Spam & Inbox."""
        user_part = addr.split('@')[0]
        start = time.time()
        boxes = ['[Gmail]/Spam', 'INBOX']
        
        while time.time() - start < timeout:
            M = None
            try:
                M = imaplib.IMAP4_SSL('imap.gmail.com', 993)
                M.login(self.GMAIL, self._PW)
                for box in boxes:
                    M.select(box)
                    # Search langsung spesifik email recipient (1.5 detik)
                    _, data = M.search(None, f'(TO "{user_part}")')
                    nums = (data[0] or b'').split()
                    if not nums:
                        # Fallback search text
                        _, data = M.search(None, f'(TEXT "{user_part}")')
                        nums = (data[0] or b'').split()
                    
                    if nums:
                        # Ambil email terbaru yang cocok
                        _, msg = M.fetch(nums[-1], '(RFC822)')
                        m = emailmod.message_from_bytes(msg[0][1])
                        body = ''
                        for part in m.walk():
                            if part.get_content_type() in ('text/plain', 'text/html'):
                                body += part.get_payload(decode=True).decode('utf-8', 'replace')
                        code = extract_otp(m.get('Subject'), body)
                        if code:
                            return code
            except Exception:
                pass
            finally:
                if M:
                    try:
                        M.logout()
                    except Exception:
                        pass
            time.sleep(3)
        return None

    def delete_inbox(self, addr):
        return None


if __name__ == '__main__':
    assert extract_otp('code: 699-696', '') == '699696'
    m = Tempik('', '')
    print('Testing ultra-fast search...')
    otp = m.wait_otp('yq0r0ad0zh4n@arxpays.my.id', timeout=10)
    print('Resolved OTP instantly:', otp)
