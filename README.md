# ⚡ Grok Farm Suite (Universal xAI CLI Automation Ecosystem)

Koleksi lengkap otomasi registrasi akun Grok xAI, manajemen OAuth 2.0 Device Flow, bypass Cloudflare Turnstile, dan sinkronisasi otomatis ke 9Router.

---

## 📂 Struktur Modul

Suite ini terdiri dari 4 varian implementasi untuk berbagai kebutuhan infrastruktur:

### 1. `grok-turnkey-9router/` (Turnkey Sayembara Edition)
- **Karakteristik**: Siap pakai, zero-setup, otomatis submit ke database 9Router (`data.sqlite`).
- **Fitur**:
  - Menu interaktif (cukup jalankan `python run.py` / `start.bat` / `start.sh`).
  - Mode CLI fleksibel (`--target`, `--workers`, `--headless`, `--proxy`).
  - Zero-setup email bawaan (Mail.tm & Tempmail.plus fallback).
  - Built-in Turnstile solver extension.

### 2. `grok-standalone-gui/` (Enterprise GUI & Web Control Plane)
- **Karakteristik**: Full desktop application (Tkinter TTK) & Web Dashboard.
- **Fitur**:
  - Desktop GUI monitoring dengan visualisasi status thread.
  - Web UI Control Plane (`web/server.py`) untuk kontrol via browser.
  - Proxy Pool Engine v3 dengan rotasi dinamis & health checking.
  - Automated test suite (35+ unit tests).

### 3. `grok-v3-batch/` (Headless CLI Batch Engine)
- **Karakteristik**: Performa tinggi dan minimal footprint resource.
- **Fitur**:
  - Script batch execution (`grok.py`, `run_batch.sh`).
  - Integrasi klien TempMail headless (`tempik_client.py`).
  - Cocok untuk eksekusi terjadwal via cron atau sub-process worker.

### 4. `grok-discord-tools/` (Community Edition)
- **Karakteristik**: Varian dengan integrasi Cloudflare Worker untuk custom domain email.
- **Fitur**:
  - `cloudflare_worker.js` untuk email routing pribadi.
  - Auto-launcher Windows 1-click batch files.

### 5. `vps-systemd/` (Production Deployment)
- Service systemd Linux (`syad-grok-turbo.service`) dan launcher skrip bash untuk runtime 24/7 di server cloud / VPS.

---

## 🚀 Panduan Memulai Cepat

### Prasyarat
- Python 3.10+ (disarankan Python 3.11 atau 3.12)
- Playwright / Camoufox browser dependencies

### Instalasi Dependensi
```bash
pip install -r grok-turnkey-9router/requirements.txt
playwright install
```

### Menjalankan Mode Turnkey (Rekomendasi)
```bash
cd grok-turnkey-9router
python run.py --target 5 --workers 3 --headless
```

---

## 🔒 Keamanan & Lisensi

- Semua data kredensial, token akun, dan file proxy di-ignore secara otomatis via `.gitignore`.
- Dilisensikan untuk penggunaan laboratorium keamanan dan pengujian performa infrastruktur.
