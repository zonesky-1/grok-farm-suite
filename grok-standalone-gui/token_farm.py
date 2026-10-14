# token_farm.py - harvest turnstile tokens from one minimal browser, STREAMED
# usage: token_farm.py <n_tokens> [out_file] [batch_size]
#   or: harvest(n, out, batch, sink=callable) -> each token pushed to sink AS IT LANDS,
#       so consumers start the moment token 1 exists instead of after the whole batch.
# env: GROK_HEADLESS=1 -> run the token browser headless (--headless=new).
# measured ceiling (2026-09-16): batch 6-8 -> ~1.8s/token; 12 degrades; 24 = 0/24.
#
# DrissionPage run_js CONTRACT (cost me a 420s hang): the script must contain a
# TOP-LEVEL `return`. A bare expression (`!!window.turnstile`) or a wrapping IIFE
# returns None, NOT the value. Every script below starts with `return ...`.
import sys, os, time, json

sys.path.insert(0, '.')
from DrissionPage import ChromiumPage, ChromiumOptions

SITEKEY = '0x4AAAAAAAhr9JGVDZbrZOo0'
URL = 'https://accounts.x.ai/sign-up?redirect=grok-com'

# Fire-and-forget render: creates N widgets, each pushes its token into
# window.__farm.out the instant it resolves. Python polls that buffer, so batch
# latency is per-widget -- the slowest widget no longer gates the fastest.
JS_START = r"""
return (function(){
    const N = %N%;
    const st = window.__farm = {out: [], done: 0, N: N};
    const holders = [];
    const t0 = Date.now();
    for (let i = 0; i < N; i++) {
        const h = document.createElement('div');
        h.id = 'farm-' + i;
        h.style.cssText = 'position:fixed;bottom:' + (10 + i * 70) + 'px;left:10px;z-index:99999;';
        document.body.appendChild(h);
        holders.push(h);
    }
    function settle(i, tok) {
        st.done++;
        if (tok) st.out.push(tok);
    }
    function tryRender() {
        if (window.turnstile) {
            holders.forEach((h, i) => {
                try {
                    window.turnstile.render(h, {
                        sitekey: %KEY%,
                        callback: (tok) => settle(i, tok),
                        'error-callback': () => settle(i, ''),
                    });
                } catch (e) { settle(i, ''); }
            });
        } else if (Date.now() - t0 > 45000) {
            holders.forEach((h, i) => settle(i, ''));
        } else {
            setTimeout(tryRender, 400);
        }
    }
    tryRender();
    // ponytail: 25s batch watchdog. A late token landing after done==N goes into
    // an abandoned buffer (next round overwrites window.__farm) -- measured real
    // solves are ~2.5s/widget, so this only fires when the IP is already hot.
    setTimeout(() => { if (st.done < N) st.done = N; }, 25000);
    return true;
})()
"""

# One round trip: drain the buffer, report progress. Top-level return is load-bearing.
JS_POLL = ("return (function(){const s=window.__farm;if(!s)return[[],0,0];"
           "const o=s.out;s.out=[];return[o,s.done,s.N];})()")


def harvest(n=1, out='turnstile_tokens.json', batch=8, sink=None):
    """Farm n turnstile tokens from one browser. If `sink` is given, push each
    token to it the moment it lands (consumers run concurrently)."""
    co = ChromiumOptions()
    co.auto_port()
    co.set_argument('--window-size=1100,900')
    # Headless is opt-in via env so a failed headless render can't silently
    # become the default. Turnstile render is the ONLY thing this browser does.
    if os.environ.get('GROK_HEADLESS') == '1':
        co.set_argument('--headless=new')
        co.set_argument('--disable-blink-features=AutomationControlled')
    b = ChromiumPage(co)
    tokens = []
    t_start = time.time()
    first_at = None
    try:
        b.get(URL)
        time.sleep(4)          # SPA boot; JS_START retries the widget itself
        while len(tokens) < n:
            want = min(batch, n - len(tokens))
            b.run_js(JS_START.replace('%N%', str(want)).replace('%KEY%', json.dumps(SITEKEY)),
                     timeout=20)
            t0 = time.time()
            landed = 0
            while True:
                got, done, N = b.run_js(JS_POLL, timeout=20) or [[], 0, 0]
                for t in got:
                    if not t:
                        continue
                    tokens.append(t)
                    landed += 1
                    if first_at is None:
                        first_at = round(time.time() - t_start, 1)
                    if sink:
                        sink(t)
                if done >= N or time.time() - t0 > 40 or len(tokens) >= n:
                    break
                time.sleep(0.25)
            print(f'batch: +{landed}/{want} (done {done}/{N}) in {round(time.time()-t0,1)}s '
                  f'-> {len(tokens)}/{n} total', flush=True)
            b.run_js("return (function(){document.querySelectorAll('[id^=farm-]')"
                     ".forEach(e=>e.remove());return true;})()")
            if not landed:
                print('batch empty - cooling 15s', flush=True)
                time.sleep(15)
            else:
                time.sleep(1)
    finally:
        b.quit()
    tokens = tokens[:n]
    json.dump(tokens, open(out, 'w'))
    print(f'saved {len(tokens)} tokens -> {out} (first token after {first_at}s)', flush=True)
    return tokens


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = sys.argv[2] if len(sys.argv) > 2 else 'turnstile_tokens.json'
    bs = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    harvest(n, out, bs)