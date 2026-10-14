#!/bin/bash
# Sequential grok batch — 1 akun/proses, proxy rotate per akun (IP segar tiap signup)
set -u
VENV=/home/agentuser/.hermes/profiles/syadagentic/farm/venv/bin/python
DIR=/home/agentuser/.hermes/profiles/syadagentic/farm/grok-tools/v3/grok-farm
PX_FILE=/home/agentuser/.hermes/profiles/syadagentic/farm/proxyfarm/grok_alive_fresh.txt
SSO="$DIR/sso.txt"
TARGET_EXTRA=4            # tambahan sukses yang dikejar (5 existing -> 9)
BASE=$(wc -l < "$SSO" 2>/dev/null || echo 0)
export DISPLAY=:99
cd "$DIR" || exit 1

i=0
while IFS= read -r px; do
  [ -z "$px" ] && continue
  i=$((i+1))
  NOW=$(wc -l < "$SSO" 2>/dev/null || echo 0)
  if [ "$((NOW - BASE))" -ge "$TARGET_EXTRA" ]; then
    echo "TARGET TERCAPAI: $NOW akun (+$((NOW-BASE))). berhenti."; break
  fi
  SAFE=$(echo "$px" | sed 's|://[^@]*@|://***@|')
  echo ""
  echo "=== RUN $i/6 | $SAFE | $(date '+%H:%M:%S') | sso: $NOW ==="
  timeout 600 "$VENV" grok.py 1 --proxy "$px" --no-install
  echo "--- run $i exit=$? ---"
done < "$PX_FILE"

FINAL=$(wc -l < "$SSO" 2>/dev/null || echo 0)
echo ""
echo "BATCH SELESAI. sso.txt: $BASE -> $FINAL (+$((FINAL-BASE)))"
