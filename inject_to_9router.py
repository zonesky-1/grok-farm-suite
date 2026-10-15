#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ 9Router Injector for Grok CLI (Grok Build)
=============================================
Menyinkronkan kredensial Grok CLI dari grok_credentials.json
ke database 9Router (data.sqlite) sebagai provider 'grok-cli'.
"""

import os
import sys
import json
import uuid
import sqlite3
from pathlib import Path

# Fix Windows console UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
CRED_FILE = CURRENT_DIR / "grok_credentials.json"


def get_db_path() -> Path:
    """Mendeteksi lokasi database 9Router secara cross-platform (Windows, macOS, Linux)."""
    if os.environ.get("ROUTER_DB_PATH"):
        return Path(os.environ["ROUTER_DB_PATH"])
    if os.environ.get("DATA_DIR"):
        return Path(os.environ["DATA_DIR"]) / "db" / "data.sqlite"
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "9router" / "db" / "data.sqlite"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "9router" / "db" / "data.sqlite"
    else:
        return Path.home() / ".config" / "9router" / "db" / "data.sqlite"


DB_PATH = get_db_path()


def load_credentials():
    if not CRED_FILE.exists():
        return []
    try:
        return json.loads(CRED_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[-] Error membaca {CRED_FILE}: {e}")
        return []


def inject_grok():
    db_path = get_db_path()
    if not db_path.exists():
        print(f"[-] Database 9Router tidak ditemukan di: {db_path}")
        return

    creds = load_credentials()
    if not creds:
        print(f"[*] Tidak ada akun di {CRED_FILE.name} untuk diinjeksi.")
        return

    print("=" * 65)
    print(f"[*] 9Router Injector: Ditemukan {len(creds)} akun di {CRED_FILE.name}")
    print(f"[*] Database: {db_path}")
    print("=" * 65)

    conn = sqlite3.connect(db_path, timeout=30.0)
    cur = conn.cursor()
    cur.execute("PRAGMA busy_timeout = 30000")

    # Ambil existing connections untuk grok-cli
    cur.execute("SELECT id, name, data FROM providerConnections WHERE provider='grok-cli'")
    existing_rows = cur.fetchall()
    existing_map = {}
    for row in existing_rows:
        try:
            d = json.loads(row[2])
            existing_map[row[1]] = (row[0], d)
        except Exception:
            pass

    inserted = 0
    updated = 0

    for item in creds:
        email = item.get("email")
        access_token = item.get("accessToken")
        refresh_token = item.get("refreshToken", "")
        id_token = item.get("idToken", "")
        user_id = item.get("userId", str(uuid.uuid4()))
        display_name = item.get("displayName", email.split("@")[0] if "@" in email else "Grok User")

        conn_data = {
            "displayName": display_name,
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresAt": item.get("expiresAt", "2026-12-31T23:59:59.999Z"),
            "scope": "openid profile email offline_access grok-cli:access api:access conversations:read conversations:write",
            "testStatus": "active",
            "expiresIn": item.get("expiresIn", 21600),
            "providerSpecificData": {
                "authMethod": "device_code",
                "idToken": id_token,
                "email": email,
                "userId": user_id,
                "hasGrokCodeAccess": True,
                "subscriptionTier": None
            },
            "lastUsedAt": None,
            "consecutiveUseCount": 0,
            "modelLock_grok-build": None,
            "lastError": None,
            "errorCode": None,
            "lastErrorAt": None,
            "backoffLevel": 0,
            "rateLimitedUntil": None
        }

        if email in existing_map:
            cid, old_data = existing_map[email]
            old_data.update(conn_data)
            cur.execute(
                "UPDATE providerConnections SET data = ?, updatedAt = datetime('now') WHERE id = ?",
                (json.dumps(old_data), cid)
            )
            updated += 1
            print(f"  [UPDATE] {email} -> Status: active")
        else:
            cid = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO providerConnections (id, provider, name, authType, data, createdAt, updatedAt)
                VALUES (?, 'grok-cli', ?, 'oauth', ?, datetime('now'), datetime('now'))
                """,
                (cid, email, json.dumps(conn_data))
            )
            inserted += 1
            print(f"  [INSERT] {email} -> ID: {cid[:8]}... (active)")

    conn.commit()
    conn.close()

    print("\n" + "=" * 65)
    print(f"🎉 Sukses Sinkronisasi! {inserted} Baru ditambahkan, {updated} Diperbarui.")
    print("=" * 65)


if __name__ == "__main__":
    inject_grok()
