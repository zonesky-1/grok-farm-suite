#!/bin/bash
F="/home/ubuntu/farm"
RESI="$F/proxyfarm/residential_proxies.txt"
ALIVE="$F/proxyfarm/resi_alive.txt"
BURN="$F/proxyfarm/burnt.txt"
touch "$BURN"
cd "$F/grok-tools/v3/grok-farm" || exit 1
export DISPLAY=:99
LOG="/home/ubuntu/farm/grok_sb2_turbo.log"

refresh_alive() {
  /home/ubuntu/farm/venv/bin/python - "$RESI" "$ALIVE" "$BURN" << 'PYEOF'
import subprocess, concurrent.futures, random, sys
from curl_cffi import requests as cr
resi, out, burn = sys.argv[1], sys.argv[2], sys.argv[3]
burnt = set()
try: burnt = set(open(burn).read().split())
except Exception: pass
cands = [l.strip() for l in open(resi) if l.strip() and not l.startswith('#') and l.startswith(('socks5://','http://'))]
cands = [c for c in cands if c.split('@')[-1] not in burnt]
pick = random.sample(cands, min(800, len(cands)))

def check(px):
    # Tahap 1: liveness murah via ipify
    try:
        r = subprocess.run(['curl','-s','-m','5','--proxy',px,'https://api.ipify.org'], capture_output=True, text=True, timeout=6)
        v = r.stdout.strip()
        if not (v and v.replace('.','').isdigit()):
            return None
    except Exception:
        return None
    # Tahap 2: lolos xAI Cloudflare? (curl_cffi chrome131)
    try:
        prox = px if px.startswith('http') else 'socks5h://' + px.split('://',1)[1]
        s = cr.Session(impersonate='chrome131', proxies={'all': prox})
        rr = s.get('https://accounts.x.ai/sign-up?redirect=grok-com', timeout=12)
        return px if rr.status_code == 200 and ('Sign up' in rr.text or 'Create' in rr.text) else None
    except Exception:
        return None

alive = []
with concurrent.futures.ThreadPoolExecutor(max_workers=100) as ex:
    for res in ex.map(check, pick):
        if res: alive.append(res)
open(out,'w').write('\n'.join(alive))
print('alive (xAI-ready):', len(alive), '/', len(pick), 'burnt:', len(burnt), flush=True)
PYEOF
}

burn_proxy() {
  local host=$(echo "$1" | sed 's|.*@||')
  echo "$host" >> "$BURN"
  echo "[burn] $host" >> "$LOG"
}

refresh_alive
echo "START $(date +%H:%M:%S) SB2-TURBO-12w (xAI-checked proxies, 2 DIRECT + 10 RESI)" > "$LOG"

worker_direct() {
  local wid=$1
  local streak=0
  sleep $(( (wid - 1) * 8 ))
  while true; do
    NOW=$(wc -l < sso.txt 2>/dev/null || echo 0)
    if [ "$NOW" -ge 2500 ]; then echo "[W$wid-DIRECT] TARGET REACHED" >> "$LOG"; return; fi
    echo "[W$wid-DIRECT] $(date +%H:%M:%S) sso=$NOW (DIRECT, streak=$streak)" >> "$LOG"
    OUT=$(timeout 360 "$F/venv/bin/python" grok.py 1 --no-install 2>&1)
    if echo "$OUT" | grep -q "SUCCESS"; then
      echo "[W$wid-DIRECT] $(date +%H:%M:%S) SUCCESS" >> "$LOG"
      streak=0
      sleep 8
    else
      REASON=$(echo "$OUT" | grep -E 'FAILED|SKIPPED' | tail -1 | sed 's/.*RuntimeError: //;s/.*TimeoutError: //' | cut -c1-70)
      echo "[W$wid-DIRECT] $(date +%H:%M:%S) FAIL: $REASON" >> "$LOG"
      streak=$((streak + 1))
      COOL=$(( streak * 45 )); [ "$COOL" -gt 600 ] && COOL=600
      echo "[W$wid-DIRECT] cooldown ${COOL}s" >> "$LOG"
      sleep $((COOL + RANDOM % 30))
    fi
  done
}

worker_resi() {
  local wid=$1
  local px_idx=$(( (wid - 2) * 30 ))
  while true; do
    NOW=$(wc -l < sso.txt 2>/dev/null || echo 0)
    if [ "$NOW" -ge 2500 ]; then echo "[W$wid-RESI] TARGET REACHED" >> "$LOG"; return; fi
    PX=$(sed -n "${px_idx}p" "$ALIVE")
    if [ -z "$PX" ]; then refresh_alive >> "$LOG"; px_idx=$(( (wid - 2) * 30 + 1 )); PX=$(sed -n "${px_idx}p" "$ALIVE"); fi
    echo "[W$wid-RESI] $(date +%H:%M:%S) sso=$NOW px=$(echo $PX | sed 's|://[^@]*@|://***@|')" >> "$LOG"
    OUT=$(timeout 360 "$F/venv/bin/python" grok.py 1 --no-install --proxy "$PX" 2>&1)
    if echo "$OUT" | grep -q "SUCCESS"; then
      echo "[W$wid-RESI] $(date +%H:%M:%S) SUCCESS" >> "$LOG"
      sleep 3
    else
      REASON=$(echo "$OUT" | grep -E 'FAILED|SKIPPED' | tail -1 | sed 's/.*RuntimeError: //;s/.*TimeoutError: //' | cut -c1-70)
      echo "[W$wid-RESI] $(date +%H:%M:%S) FAIL: $REASON" >> "$LOG"
      if echo "$OUT" | grep -qE "email submit not confirmed|Email sign-up isn.t available|turnstile solve failed|OTP never arrived|Page.goto"; then
        burn_proxy "$PX"
      fi
    fi
    px_idx=$((px_idx + 7))
    sleep 2
  done
}

for w in 1 2; do worker_direct $w & done
for w in 3 4 5 6 7 8 9 10 11 12; do worker_resi $w & done
wait
