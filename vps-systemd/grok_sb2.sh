#!/bin/bash
F="/home/ubuntu/farm"
RESI="$F/proxyfarm/residential_proxies.txt"
ALIVE="$F/proxyfarm/resi_alive.txt"
BURN="$F/proxyfarm/burnt.txt"
touch "$BURN"
cd "$F/grok-tools/v3/grok-farm" || exit 1
export DISPLAY=:99
LOG="/home/ubuntu/farm/grok_sb2.log"

refresh_alive() {
  /home/ubuntu/farm/venv/bin/python - "$RESI" "$ALIVE" "$BURN" <<'PYEOF'
import subprocess, concurrent.futures, random, sys
resi, out, burn = sys.argv[1], sys.argv[2], sys.argv[3]
burnt = set()
try: burnt = set(open(burn).read().split())
except Exception: pass
cands = [l.strip() for l in open(resi) if l.strip() and not l.startswith('#') and l.startswith(('socks5://','http://'))]
cands = [c for c in cands if c.split('@')[-1] not in burnt]
pick = random.sample(cands, min(120, len(cands)))
def check(px):
    try:
        r = subprocess.run(['curl','-s','-m','8','--proxy',px,'https://api.ipify.org'], capture_output=True, text=True, timeout=10)
        v = r.stdout.strip()
        return px if (v and v.replace('.','').isdigit()) else None
    except Exception:
        return None
alive = []
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    for res in ex.map(check, pick):
        if res: alive.append(res)
open(out,'w').write('\n'.join(alive))
print('refresh alive:', len(alive), 'burnt:', len(burnt), flush=True)
PYEOF
}

burn_proxy() {
  local host=$(echo "$1" | sed 's|.*@||')
  echo "$host" >> "$BURN"
  echo "[burn] $host" >> "$LOG"
}

refresh_alive
echo "START $(date +%H:%M:%S) SB2-4w-BURN alive=$(wc -l < $ALIVE) burnt=$(wc -l < $BURN)" > "$LOG"

worker() {
  local wid=$1
  local px_idx=$((wid * 11))
  while true; do
    NOW=$(wc -l < sso.txt 2>/dev/null || echo 0)
    if [ "$NOW" -ge 1000 ]; then echo "[W$wid] TARGET 1000 REACHED" >> "$LOG"; return; fi
    if [ $((px_idx % 25)) -eq 0 ]; then refresh_alive >> "$LOG"; fi
    PX=$(sed -n "${px_idx}p" "$ALIVE")
    if [ -z "$PX" ]; then refresh_alive >> "$LOG"; px_idx=$((wid * 11 + 1)); PX=$(sed -n "${px_idx}p" "$ALIVE"); fi
    echo "[W$wid] $(date +%H:%M:%S) sso=$NOW px=$(echo $PX | sed 's|://[^@]*@|://***@|')" >> "$LOG"
    OUT=$(timeout 420 "$F/venv/bin/python" grok.py 1 --no-install --proxy "$PX" 2>&1)
    if echo "$OUT" | grep -q "SUCCESS"; then
      echo "[W$wid] $(date +%H:%M:%S) SUCCESS" >> "$LOG"
    else
      REASON=$(echo "$OUT" | grep -E 'FAILED|SKIPPED' | tail -1 | sed 's/.*RuntimeError: //;s/.*TimeoutError: //' | cut -c1-70)
      echo "[W$wid] $(date +%H:%M:%S) FAIL: $REASON" >> "$LOG"
      if echo "$OUT" | grep -qE "email submit not confirmed|Email sign-up isn.t available|turnstile solve failed"; then
        burn_proxy "$PX"
      fi
    fi
    px_idx=$((px_idx + 4))
    sleep 2
  done
}

# Jalankan 4 worker paralel memanfaatkan 8 core mesin ini
worker 1 &
worker 2 &
worker 3 &
worker 4 &
wait
