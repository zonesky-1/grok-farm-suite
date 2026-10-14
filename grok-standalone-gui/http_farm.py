# http_farm.py - full-HTTP grok account farm, PRODUCER/CONSUMER
# one browser farms turnstile tokens and pushes each into a queue as it lands;
# N worker threads drain the queue and do the registration over plain HTTP.
# No cold-start stall: worker 1 starts the moment token 1 exists.
# usage: python http_farm.py <n_accounts> [workers]
import sys, json, random, string, time, re, os
import threading, queue

sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests as stdlib

# ponytail: stdlib-only .env loader (no python-dotenv dep). run_forever spawns
# this as a subprocess; env vars exported in the parent shell do NOT survive
# into a fresh chunk on Windows, so the mail domain has to come off disk.
_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_ENV):
    for _line in open(_ENV, encoding='utf-8'):
        _line = _line.strip()
        if _line and not _line.startswith('#') and '=' in _line:
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# --- import repo helpers (bind runtime first) ---
import grok_register_ttk as ttk
NS = dict(ttk.__dict__)
create_account_mail = NS['create_account']      # duckmail create (routes via pool)
get_mail_token = NS['get_token']
get_mail_msgs = NS['get_messages']
get_mail_detail = NS['get_message_detail']
from cpa_xai.mint import mint_and_export

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
      'Origin': 'https://accounts.x.ai', 'Referer': 'https://accounts.x.ai/sign-up?redirect=grok-com'}
SITEKEY = '0x4AAAAAAAhr9JGVDZbrZOo0'
SIGNUP_URL = 'https://accounts.x.ai/sign-up?redirect=grok-com'
MAIL_PWD = 'TestPass123!'
# set GROK_MAIL_DOMAIN to a duckmail-verified domain YOU control. Fail loud, not silently.
DOMAIN = os.environ.get('GROK_MAIL_DOMAIN', '').strip()
if not DOMAIN:
    raise SystemExit(
        'GROK_MAIL_DOMAIN is not set.\n'
        '  bash:  export GROK_MAIL_DOMAIN=yourdomain.tld\n'
        '  cmd:   set GROK_MAIL_DOMAIN=yourdomain.tld\n'
        'It must be a domain verified in your own duckmail account.'
    )
GIVEN = ['Mason', 'Leo', 'Ryan', 'Kai', 'Evan', 'Nolan', 'Owen', 'Adam']
FAMILY = ['Chen', 'Lin', 'Wang', 'Yang', 'Liu', 'Zhao', 'Wu', 'Xu']
TOKENS_FILE = 'turnstile_tokens.json'
# per-account timing sidecar -> tg_notify.py attaches "lama terbuatnya" to the push.
# lives in a subdir so the xai-*.json glob in tg_notify never picks it up.
TIMING_DIR = os.path.join('cpa_auths', '.timing')


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


# ---------- token farm ----------
# batched harvest lives in token_farm.py (ceiling: batch 6-8 -> ~1.8s/token;
# batch 12 degrades, batch 24 = 0/24). One browser, N widgets per batch.
from token_farm import harvest as _harvest


# ---------- HTTP registration ----------
def reg_one(turnstile_token):
    """Full HTTP registration for one account. Returns dict or raises."""
    t_start = time.time()
    addr = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '@' + DOMAIN
    pwd = 'Xq9#' + ''.join(random.choices(string.ascii_letters + string.digits, k=14))
    # ponytail: per-phase marks. The lifetime is a FIXED cost, not a tail --
    # p25 19.5 / median 20.1 / p75 21.1 over 2932 accounts. So the only lever
    # is which phase owns the seconds. Cheap when unread, decisive when read.
    ph = []

    def mark(k):
        ph.append(f'{k}={round(time.time() - t_start, 1)}')

    # 1. mailbox
    create_account_mail(addr, MAIL_PWD, expires_in=0)
    mark('mail')

    # 2. send code (stdlib fingerprint passes the edge)
    r = stdlib.post('https://accounts.x.ai/api/auth/send-verification-code',
                    json={'email': addr}, headers=UA, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f'send-code {r.status_code}')
    mark('send')

    # 3. poll mail for code
    # ponytail: adaptive poll, 0.4s -> 6s, and CHECK BEFORE SLEEPING so a mail
    # that already landed costs ~0 wait. Fixed sleep(6) meant every account sat
    # blind while its code was sitting in the inbox (mail lands 2-10s).
    # The mail token is fetched in parallel with send-code: duckmail authenticates
    # by cookie-less JWT per mailbox, so this is a separate connection and the two
    # no longer serialise (was 1.7s of dead time between 'send' and 'code').
    _mt = {}
    _th = threading.Thread(target=lambda: _mt.__setitem__('t', get_mail_token(addr, MAIL_PWD)), daemon=True)
    _th.start()
    _th.join(timeout=30)
    mtok = _mt.get('t')
    if not mtok:
        raise RuntimeError('no mail token')
    code = None
    t0 = time.time()
    delay = 0.4
    while time.time() - t0 < 240:
        msgs = get_mail_msgs(mtok)
        if msgs:
            mid = msgs[0]['id'].split('/messages/')[-1]
            det = get_mail_detail(mtok, mid)
            m = re.search(r'\b(\d{3})-(\d{3})\b', det.get('text', ''))
            if m:
                code = m.group(1) + m.group(2)
                break
        time.sleep(delay)
        delay = min(delay * 1.5, 6.0)
    if not code:
        raise RuntimeError('no code in 240s')
    mail_wait = round(time.time() - t0)
    mark('code')

    # 4. create account (session keeps cookies)
    s = stdlib.Session()
    payload = {'email': addr, 'password': pwd,
               'givenName': random.choice(GIVEN), 'familyName': random.choice(FAMILY),
               'emailValidationCode': code, 'turnstileToken': turnstile_token}
    r = s.post('https://accounts.x.ai/api/auth/sign-up/create-account', json=payload, headers=UA, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f'create {r.status_code}: {r.text[:120]}')
    redirect = r.json().get('redirectUrl', '')
    mark('create')

    # 5. sso
    s.get(redirect, headers={'User-Agent': UA['User-Agent']}, timeout=30, allow_redirects=True)
    sso = None
    for c in s.cookies:
        if c.name == 'sso':
            sso = c.value
            if 'grok.com' in (c.domain or ''):
                break
    if not sso:
        raise RuntimeError('no sso cookie')
    mark('sso')

    # 6. mint CPA (pure HTTP, ~3s)
    res = mint_and_export(addr, pwd, auth_dir='cpa_auths', sso=sso)
    if not (res or {}).get('ok'):
        raise RuntimeError(f'mint failed: {res}')
    mark('mint')

    elapsed = round(time.time() - t_start, 1)
    os.makedirs(TIMING_DIR, exist_ok=True)
    json.dump({'email': addr, 'elapsed': elapsed, 'mail_wait': mail_wait, 'phases': ph,
               'started_at': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(t_start)),
               'finished_at': time.strftime('%Y-%m-%dT%H:%M:%S')},
              open(os.path.join(TIMING_DIR, addr + '.json'), 'w'))

    return {'addr': addr, 'mail_wait': mail_wait, 'elapsed': elapsed, 'phases': ph}


def run_pipeline(n, workers, produce, work):
    """produce(sink, n) pushes tokens into sink as they land; work(tok) processes one.
    Workers exit on sentinel. Returns {'ok','fail','durs'}."""
    q = queue.Queue()

    def _producer():
        try:
            produce(q.put, n)
        except Exception as e:
            log(f'FARM FAIL: {e}')
        finally:
            for _ in range(workers):
                q.put(None)

    res = {'ok': 0, 'fail': 0, 'durs': []}
    lock = threading.Lock()

    def _worker():
        while True:
            tok = q.get()
            if tok is None:
                return
            try:
                r = work(tok)
                with lock:
                    res['ok'] += 1
                    res['durs'].append(r['elapsed'])
                log(f"OK {r['addr']} total {r['elapsed']}s | {' '.join(r.get('phases') or [])}")
            except Exception as e:
                with lock:
                    res['fail'] += 1
                log(f'FAIL: {e}')

    pt = threading.Thread(target=_producer, daemon=True)
    pt.start()
    ths = [threading.Thread(target=_worker) for _ in range(workers)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    pt.join()
    return res


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    # harvest overshoots by +2 to fill the last batch, but EVERY sunk token
    # becomes an account — so the sink is capped at n. (Without this, n=5 made 7.)
    sent = {'n': 0}
    lock = threading.Lock()

    def produce(sink, k):
        def capped(tok):
            with lock:
                if sent['n'] >= n:
                    return
                sent['n'] += 1
            sink(tok)
        # ponytail: N browsers in parallel. Scaling test proved workers are
        # saturated by token supply -- 8/16/24 workers all give ~3.6s/acct
        # wall, while 2 browsers cut token cost 3.15 -> 2.15s (1.47x). So the
        # browser count is the throughput lever, not the worker count.
        nb = max(1, int(os.environ.get('GROK_FARM_BROWSERS', '2')))
        per = (n + 2 + nb - 1) // nb
        ths = []
        for i in range(nb):
            th = threading.Thread(target=_harvest, args=(per, f'{TOKENS_FILE}.{i}', 8),
                                  kwargs={'sink': capped}, daemon=True)
            th.start()
            ths.append(th)
        for th in ths:
            th.join()

    log(f'farm+register: {n} accounts, {workers} workers (producer/consumer)')
    t0 = time.time()
    res = run_pipeline(n, workers, produce, reg_one)
    dt = round(time.time() - t0)
    log(f"DONE: {res['ok']} ok / {res['fail']} fail in {dt}s -> {round(dt/max(n,1),1)}s/account wall avg")
    if res['durs']:
        d = res['durs']
        log(f'per-account: min {min(d)}s / avg {round(sum(d)/len(d),1)}s / max {max(d)}s')


if __name__ == '__main__':
    main()