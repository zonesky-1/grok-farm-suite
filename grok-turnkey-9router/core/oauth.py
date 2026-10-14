"""OAuth 2.0 Device Code Engine untuk xAI (Grok CLI)."""
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Optional

XAI_DEVICE_CODE_URL = "https://auth.x.ai/oauth2/device/code"
XAI_TOKEN_URL = "https://auth.x.ai/oauth2/token"
CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
DEFAULT_SCOPE = "openid profile email offline_access grok-cli:access api:access"

class OAuthDeviceError(RuntimeError):
    pass

def request_device_code(client_id: str = CLIENT_ID, scope: str = DEFAULT_SCOPE, timeout: int = 20) -> dict:
    """Meminta device code resmi dari auth.x.ai."""
    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "scope": scope
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
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "device_code" not in data or "user_code" not in data:
                raise OAuthDeviceError(f"Format respon tidak sesuai: {data}")
            return data
    except Exception as e:
        raise OAuthDeviceError(f"Gagal request device code: {e}")

def poll_device_token(device_code: str, client_id: str = CLIENT_ID, interval: int = 2, timeout: int = 300) -> Optional[dict]:
    """Polling token endpoint sampai user authorize di browser."""
    payload = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": device_code,
        "client_id": client_id
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
            with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "access_token" in data:
                    return data
        except urllib.error.HTTPError as e:
            # 400 authorization_pending adalah status normal saat menunggu konfirmasi
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                err = err_body.get("error", "")
                if err in ("expired_token", "access_denied"):
                    return None
            except Exception:
                pass
        except Exception:
            pass
        time.sleep(interval)
    return None
