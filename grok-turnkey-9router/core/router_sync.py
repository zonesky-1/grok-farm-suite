"""9Router Auto-Submit & Activation Engine.
Menyimpan token Grok CLI langsung ke database SQLite 9Router dan/atau REST API.
"""
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

DB_LOCK = threading.Lock()

def get_default_9router_db() -> Optional[Path]:
    """Mencari lokasi database SQLite 9Router di Windows, macOS, dan Linux."""
    candidates = []

    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "9router" / "db" / "data.sqlite")
        localappdata = os.getenv("LOCALAPPDATA")
        if localappdata:
            candidates.append(Path(localappdata) / "9router" / "db" / "data.sqlite")
    elif sys.platform == "darwin":
        home = Path.home()
        candidates.append(home / "Library" / "Application Support" / "9router" / "db" / "data.sqlite")
    else:  # Linux / Unix
        home = Path.home()
        candidates.append(home / ".config" / "9router" / "db" / "data.sqlite")
        candidates.append(home / ".9router" / "db" / "data.sqlite")
        candidates.append(home / "9router" / "db" / "data.sqlite")

    for p in candidates:
        if p.exists():
            return p

    # Fallback default location jika belum ada
    if sys.platform == "win32":
        fallback = Path(os.getenv("APPDATA", str(Path.home()))) / "9router" / "db" / "data.sqlite"
    else:
        fallback = Path.home() / ".config" / "9router" / "db" / "data.sqlite"

    return fallback

def submit_to_9router_sqlite(email: str, token_data: dict, db_path: Optional[str] = None) -> Tuple[bool, str]:
    """Menulis koneksi akun Grok CLI langsung ke tabel SQLite 9Router."""
    target_db = Path(db_path) if db_path else get_default_9router_db()

    if not target_db:
        return False, "Lokasi database 9Router tidak dapat ditentukan."

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    id_token = token_data.get("id_token", "")
    expires_in = int(token_data.get("expires_in", 21600))

    expires_at = datetime.fromtimestamp(time.time() + expires_in, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    now_iso = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")

    conn_data = {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "idToken": id_token,
        "tokenType": "Bearer",
        "expiresIn": expires_in,
        "expiresAt": expires_at,
        "scope": "openid profile email offline_access grok-cli:access api:access",
        "email": email,
        "displayName": f"Grok CLI ({email})",
        "testStatus": "active",
        "lastError": None,
        "lastErrorAt": None,
        "errorCode": None,
        "backoffLevel": 0,
        "providerSpecificData": {
            "authMethod": "device_code",
            "idToken": id_token,
            "email": email,
            "userId": f"usr_{uuid.uuid4().hex[:12]}",
            "hasGrokCodeAccess": True,
            "subscriptionTier": "Grok Free",
            "connectionProxyEnabled": False,
            "connectionProxyUrl": "",
            "connectionNoProxy": ""
        }
    }

    conn_data_str = json.dumps(conn_data, ensure_ascii=False)
    conn_id = str(uuid.uuid4())

    target_db.parent.mkdir(parents=True, exist_ok=True)

    with DB_LOCK:
        try:
            conn = sqlite3.connect(str(target_db), timeout=30.0)
            cursor = conn.cursor()

            # Pastikan schema tabel ada jika 9Router belum pernah di-start
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS providerConnections (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    authType TEXT NOT NULL,
                    name TEXT,
                    email TEXT,
                    priority INTEGER DEFAULT 1,
                    isActive INTEGER DEFAULT 1,
                    data TEXT,
                    createdAt TEXT,
                    updatedAt TEXT
                )
            """)

            cursor.execute("SELECT MAX(priority) FROM providerConnections WHERE provider = 'grok-cli'")
            max_p = cursor.fetchone()[0]
            next_p = (max_p or 0) + 1

            cursor.execute("SELECT id FROM providerConnections WHERE provider = 'grok-cli' AND email = ?", (email,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE providerConnections
                    SET data = ?, isActive = 1, updatedAt = ?
                    WHERE id = ?
                """, (conn_data_str, now_iso, existing[0]))
                msg = f"Berhasil memperbarui koneksi 9Router: {email}"
            else:
                cursor.execute("""
                    INSERT INTO providerConnections (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt)
                    VALUES (?, 'grok-cli', 'oauth', ?, ?, ?, 1, ?, ?, ?)
                """, (conn_id, f"Grok ({email})", email, next_p, conn_data_str, now_iso, now_iso))
                msg = f"Berhasil menambahkan koneksi 9Router #{next_p}: {email}"

            conn.commit()
            conn.close()
            return True, msg
        except Exception as e:
            return False, f"Gagal menulis ke SQLite 9Router ({target_db}): {e}"

def submit_to_9router_api(email: str, token_data: dict, api_url: str = "http://localhost:20128/api/provider-connections") -> Tuple[bool, str]:
    """Submit via 9Router REST API jika service sedang berjalan."""
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "provider": "grok-cli",
            "authType": "oauth",
            "name": f"Grok CLI ({email})",
            "email": email,
            "data": token_data,
            "isActive": True
        }
        req = urllib.request.Request(api_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status in (200, 201):
                return True, f"Berhasil submit ke 9Router REST API: {email}"
    except Exception as e:
        return False, f"REST API fallback: {e}"
    return False, "REST API tidak merespon"
