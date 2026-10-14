# Grok auto-register — standalone bundle

Extract, install, run. No git, no clone, no helper scripts.

## Install

```
uv venv .venv --python 3.11
uv pip install -r requirements.txt --python .venv
```

No uv? `python -m venv .venv` then `.venv\Scripts\pip install -r requirements.txt`.

## Set your mail domain (required)

Sign up at duckmail, add a domain, verify the DNS records. Then:

```
bash:  export GROK_MAIL_DOMAIN=yourdomain.tld
cmd:   set GROK_MAIL_DOMAIN=yourdomain.tld
```

The script refuses to start without it. Nothing is hardcoded to anyone else's domain.

## Run

```
.venv\Scripts\python.exe http_farm.py 25 8
```

`arg1` = how many accounts. `arg2` = worker threads (8 is the tuned value — 30 accounts in 97s, 3.2s/account wall).

Back to back, forever:

```
bash:  while true; do .venv/Scripts/python.exe http_farm.py 25 8; done
cmd:   for /l %i in () do .venv\Scripts\python.exe http_farm.py 25 8
```

Stop with Ctrl+C.

## Output

`cpa_auths\xai-<email>.json` — one file per account, written right after mint. Fields: `id`, `name`, `email`, `access_token`, `refresh_token`, `expired`.

## Needs

- Windows + a real Chrome install. DrissionPage drives it; the browser's only job is farming turnstile tokens.
- Internet.
- Email is duckmail — anonymous, no API key. But you need your own verified domain (see above).
- **Headless does not work.** Three variants probed: `--headless=new` dies at the DevTools handshake, `--headless` legacy never boots the turnstile widget. Zero tokens. Keep a real browser window open.
- `config.json` ships pre-set: `email_provider=duckmail`, `cpa_export_enabled=true`, `cpa_auth_dir=./cpa_auths`, `proxy_mode=direct`. All credential fields are blank. Leave them.

## Rate limit

Turnstile soft-throttles one IP after ~2-3 signups. If `batch empty - cooling 15s` keeps repeating, stop for 15-60 minutes. Hitting it harder makes the block longer, not shorter.

## Not in this bundle

Telegram reporting and the NDJSON merge step. `cpa_auths\*.json` is the credential store — read it directly.

## Timing you should expect

- first account of a run: ~20s (turnstile cold start)
- steady state: 3-4s/account wall at 8 workers
- token arrival is the pace-setter; the email poll is ~10s of each account's lifetime