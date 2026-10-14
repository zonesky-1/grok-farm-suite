# 🤖 Grok CLI Auto Register & 9Router Auto Submit Bot (Sayembara Edition)

Bot otomatisasi pendaftaran akun **Grok xAI (Grok CLI)**, pengambilan token OAuth resmi, dan auto-submit + aktivasi langsung ke **9Router**.  
Didesain **turnkey (tinggal running, zero-setup)** sesuai kriteria Sayembara.

---

## ✨ Fitur Unggulan

1. **Multi-Thread / Concurrency Fleksibel**:
   - Bebas mengatur jumlah worker (contoh: 5 akun diproses bersamaan secara paralel).
2. **Target Akun & Kuota Otomatis**:
   - Atur batas akun yang ingin dibuat (`--target 10`). Bot otomatis berhenti saat kuota tercapai.
3. **Zero-Setup Email Bawaan**:
   - Menggunakan Mail.tm (domain aktif) + fallback Tempmail.plus bawaan. **Tanpa perlu beli domain / tanpa setup Cloudflare Worker**.
4. **Auto Cloudflare Turnstile Bypass**:
   - Terintegrasi addon `turnstilePatch` otomatis yang menyelesaikan captcha Cloudflare tanpa intervensi manual.
5. **OAuth 2.0 Device Flow Resmi xAI**:
   - Menggunakan Client ID resmi Grok CLI (`b1a00492-073a-47ea-816f-4c329264a828`) untuk mendapatkan `access_token` & `refresh_token`.
6. **Auto Submit & Aktivasi ke 9Router**:
   - Otomatis mendeteksi database SQLite 9Router (`data.sqlite`) di Windows, macOS, maupun Linux.
   - Mengisi tabel `providerConnections` dengan status `isActive = 1`, `testStatus = 'active'`, dan prioritas otomatis. Akun langsung aktif tanpa perlu tes manual di UI 9Router.
7. **Dukungan Headless & Headed**:
   - Mode background tanpa jendela (`--headless`) atau mode visual jendela terlihat (`--headed`).
8. **Dukungan Proxy & Direct IP**:
   - Bisa berjalan dengan direct IP (tanpa proxy) atau dengan proxy pool (`--proxy proxies.txt`).

---

## 🚀 Cara Menjalankan (Paling Mudah)

### Cara 1: Mode Interaktif (Tinggal Klik / Run)

Cukup jalankan:
```bash
python run.py
```
*(Atau di Windows klik dua kali `start.bat`, di Linux/macOS jalankan `./start.sh`)*

Bot akan menampilkan menu interaktif:
```text
>> Masukkan Target Jumlah Akun [Default: 5]: 
>> Masukkan Jumlah Worker/Thread Simultan [Default: 3]: 
>> Jalankan Mode Headless / Tanpa Jendela? (y/n) [Default: y]: 
>> Masukkan File Proxy atau URL Proxy [Default: Direct]: 
>> Otomatis Submit & Aktivasi ke 9Router? (y/n) [Default: y]: 
```
*Cukup tekan **ENTER** untuk menggunakan pengaturan rekomendasi tercepat!*

---

### Cara 2: Mode CLI (Command Line Flags)

```bash
# Bikin 5 akun dengan 5 worker (paralel 5 akun sekaligus) mode headless:
python run.py --target 5 --workers 5 --headless

# Bikin 10 akun pakai proxy list:
python run.py --target 10 --workers 3 --proxy proxies.txt

# Bikin 2 akun mode GUI terbuka (Headed):
python run.py --target 2 --workers 1 --headed
```

---

## 📁 Struktur Direktori

```text
grok_bot_9router/
├── core/
│   ├── browser.py       # Engine otomasi browser & Turnstile handling
│   ├── mail.py          # Zero-setup temp mail inbox & OTP extractor
│   ├── oauth.py         # OAuth Device flow xAI client
│   └── router_sync.py   # Sinkronisasi & aktivasi database 9Router SQLite
├── turnstilePatch/      # Addon browser patch Cloudflare Turnstile
├── run.py               # Entry point utama (CLI + Interactive menu)
├── start.bat            # Windows 1-click launcher
├── start.sh             # Linux/macOS 1-click launcher
├── requirements.txt     # Dependensi library
├── accounts.txt         # Hasil ekspor (email|password|refresh_token)
└── accounts.json        # Hasil ekspor lengkap dalam format JSON
```

---

## 📊 Format Output

Data akun tersimpan otomatis di:
1. `accounts.txt` → `email|password|refresh_token`
2. `accounts.json` → JSON lengkap dengan timestamp, access token, dan status.
3. Database 9Router (`data.sqlite`) → Terdaftar dan langsung aktif di daftar Provider 9Router.

---

**Peserta Sayembara:** Dikirimkan untuk @schneizellyx  
*Status: Turnkey / Ready to Run.*
