"""协调浏览器授权、OAuth 轮询和 CPA 凭证导出流程。"""

import time

import requests as _rq

from .browser_confirm import mint_with_browser
from .oauth_device import poll_device_token, request_device_code
from .schema import DEFAULT_BASE_URL, build_cpa_xai_auth
from .writer import write_cpa_xai_auth

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def mint_via_http(sso, log=lambda m: None, cancel=None, request_timeout_sec=15.0):
    """Pure-HTTP device flow: verify -> approve -> poll. No browser.

    Works because the device/consent pages are plain HTML forms; for a
    personal account principal_id is legitimately the empty string and
    action is set client-side on click.
    """
    s = _rq.Session()
    for dom in ('.x.ai', 'accounts.x.ai', 'auth.x.ai', '.grok.com', 'grok.com'):
        for c in ('sso', 'sso-rw'):
            s.cookies.set(c, sso, domain=dom)
    s.headers['User-Agent'] = _UA

    t0 = time.time()
    sess = request_device_code(timeout=float(request_timeout_sec), cancel=cancel)
    log("[mint-http] user_code=%s" % sess.user_code)
    r = s.post('https://auth.x.ai/oauth2/device/verify', data={'user_code': sess.user_code},
               headers={'Referer': 'https://accounts.x.ai/oauth2/device?user_code=' + sess.user_code},
               allow_redirects=True, timeout=float(request_timeout_sec))
    if r.status_code != 200:
        raise RuntimeError('verify HTTP %s' % r.status_code)
    r2 = s.post('https://auth.x.ai/oauth2/device/approve',
                data={'user_code': sess.user_code, 'action': 'allow',
                      'principal_type': 'User', 'principal_id': ''},
                headers={'Referer': r.url}, allow_redirects=True,
                timeout=float(request_timeout_sec))
    if r2.status_code != 200 or 'Authorized' not in r2.text:
        raise RuntimeError('approve HTTP %s' % r2.status_code)
    res = poll_device_token(sess.device_code, token_endpoint=sess.token_endpoint,
                            interval=5, expires_in=1700, cancel=cancel)
    log("[mint-http] token in %.1fs (0 browser)" % (time.time() - t0))
    return {
        "access_token": res.access_token,
        "refresh_token": res.refresh_token,
        "id_token": res.id_token,
        "token_type": res.token_type,
        "expires_in": res.expires_in,
        "user_code": sess.user_code,
        "token_endpoint": sess.token_endpoint,
    }


def mint_and_export(
    email,
    password,
    auth_dir,
    page=None,
    proxy=None,
    headless=False,
    base_url=DEFAULT_BASE_URL,
    browser_timeout_sec=240.0,
    force_standalone=True,
    cookies=None,
    reuse_browser=True,
    recycle_every=15,
    log=None,
    cancel=None,
    request_timeout_sec=15.0,
    poll_timeout_sec=15.0,
    sso=None,
):
    logger = log or (lambda message: None)
    email = str(email or "").strip()
    password = str(password or "")
    sso_value = str(sso or "").strip()
    if not email or not password:
        return {"ok": False, "email": email, "error": "missing email/password"}

    tokens = None
    # fast path: pure HTTP, only needs the sso cookie (accounts file has it)
    if sso_value:
        try:
            tokens = mint_via_http(sso_value, log=logger, cancel=cancel,
                                   request_timeout_sec=request_timeout_sec)
        except Exception as exc:
            logger("[mint-http] fallback to browser: %s" % exc)

    if tokens is None:
        tokens = mint_with_browser(
            email=email,
            password=password,
            page=None if force_standalone else page,
            proxy=proxy,
            headless=headless,
            browser_timeout_sec=float(browser_timeout_sec),
            poll_log=logger,
            cancel=cancel,
            force_standalone=bool(force_standalone),
            cookies=cookies,
            reuse_browser=bool(reuse_browser),
            recycle_every=int(recycle_every or 0),
            request_timeout_sec=float(request_timeout_sec),
            poll_timeout_sec=float(poll_timeout_sec),
        )

    payload = build_cpa_xai_auth(
        email=email,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        id_token=tokens.get("id_token"),
        expires_in=tokens.get("expires_in"),
        base_url=base_url,
        token_endpoint=tokens.get("token_endpoint") or "",
    )
    path = write_cpa_xai_auth(auth_dir, payload)
    logger("wrote %s" % path)
    return {
        "ok": True,
        "email": email,
        "path": str(path),
        "user_code": tokens.get("user_code"),
        "base_url": str(base_url or DEFAULT_BASE_URL),
    }
