# ⚡ Grok CLI (xAI) Turbo Auto-Farming & 9Router Engine

Bot otomatisasi pendaftaran akun **Grok CLI (xAI)**, penarikan resmi OAuth 2.0 Access Token & Refresh Token melalui standar **RFC 8628 (OAuth 2.0 Device Authorization Grant)**, rotasi **Proxy Otomatis (2.200+ IP)**, serta sinkronisasi instan ke database lokal **9Router** (`http://127.0.0.1:20128/v1`).

> 🏆 **Zero-Setup & Out-of-the-Box**: Seluruh dependensi, monkeypatch kompatibilitas PyYAML Python 3.10–3.15, browser stealth Camoufox, integrasi Cloudflare Worker & Email Routing, rotasi proxy, dan database sync sudah tertangani secara otomatis.

---

## ⚡ Panduan Cepat (Quickstart)

### 🚀 Deteksi Otomatis Saat Memulai Farming (Zero-Confusion)
xAI memblokir seluruh domain email publik gratisan (*mail.tm*, *duck.com*, dll.). Oleh karena itu, modul ini menggunakan **Cloudflare Worker & Custom Domain Email Routing**.

Jika Anda baru pertama kali menjalankan tools ini dan **belum memasukkan URL Worker**:
- **Di `run.bat`**: Saat Anda memilih menu **`[1]`**, **`[2]`**, **`[3]`**, atau **`[4]`**, skrip **secara otomatis mendeteksi** bahwa Worker belum diatur, menampilkan **Panduan Cepat Setup (2 Menit)**, dan langsung menanyakan URL Worker Anda di tempat. Setelah Anda memasukkan URL, skrip langsung menyimpannya ke `config.json` dan **seketika melanjutkan proses farming** yang Anda pilih tanpa perlu kembali ke menu utama!
- **Di `main.py`**: Saat dijalankan via terminal (`python main.py`) tanpa flag `--worker-url`, skrip otomatis menampilkan panduan dan meminta input URL Worker di tempat, lalu otomatis melanjutkan proses farming.

---

### Cara 1: Menggunakan Launcher Satu-Klik (`run.bat`) — *Sangat Direkomendasikan*
Cukup klik dua kali file **`run.bat`** di Windows:
1. Skrip otomatis memeriksa Python, menginstal paket dari `requirements.txt`, dan menyiapkan binary browser stealth Camoufox.
2. Anda akan disajikan menu interaktif:
   - `[1]` **Bulk Farming Tak Terbatas Turbo (5 Worker - Non-Stop)** *(Paling Direkomendasikan)*: Membuat akun terus-menerus tanpa henti dengan 5 worker paralel. Mendukung pilihan **Direct Ultra-Fast** atau **Rotating Proxy (`proxies.txt`)**.
   - `[2]` **Buat Akun Tertentu**: Mode terukur untuk membuat sejumlah akun tertentu dengan worker yang Anda tentukan.
   - `[3]` **Bulk Farming Tak Terbatas Hemat RAM (2 Worker)**: Mode stabil hemat RAM untuk PC atau VPS spesifikasi standar.
   - `[4]` **Mode Kustom Lengkap**: Bebas tentukan target jumlah akun, jumlah worker, mode koneksi (Direct/Proxy/WARP), mode tampilan browser (Headless/Visible), dan opsi auto-inject 9Router.
   - `[5]` **Konfigurasi Cloudflare Worker & Kredensial**: Menu untuk mengatur URL Worker, domain kustom, membaca panduan setup, melihat daftar akun, atau mengosongkan kredensial.
   - `[6]` **Jalankan Token Auto-Refresher Daemon**: Background refresher tiap 3.5 jam agar token di 9Router tidak pernah kedaluwarsa.
   - `[7]` **Sinkronkan Ulang Akun ke 9Router**: Injeksi ulang kredensial yang tersimpan di `grok_credentials.json` ke database SQLite 9Router.
   - `[8]` **Tes Inferensi Model**: Uji coba inferensi ke model Grok (`gcli/grok-4.6`) di 9Router lokal.
   - `[0]` **Keluar**

---

### Cara 2: Menjalankan Langsung via Terminal / Command Prompt / PowerShell

Cukup buka terminal di folder ini dan ketik:
```powershell
# Default: Bulk Farming Tak Terbatas (5 Worker Paralel Non-Stop sampai Ctrl+C)
# Otomatis meminta URL Worker jika belum diatur, lalu menampilkan menu koneksi!
python main.py
```

*(Atau gunakan flag langsung tanpa prompt interaktif):*
```powershell
# 1. Mode Direct Ultra-Fast (Paling Kencang 18-25s per akun, Tanpa Proxy)
python main.py --proxy-mode direct

# 2. Mode Rotating Proxy (Menggunakan 2.223 IP dari proxies.txt, berganti tiap akun)
python main.py --proxy-mode proxy

# 3. Mode Cloudflare WARP lokal (port 40001/40002)
python main.py --proxy-mode warp

# 4. Tentukan jumlah akun terbatas (contoh: 10 akun dengan 3 worker)
python main.py -n 10 -w 3

# 5. Buat 1 akun instan saja
python main.py -n 1 -w 1

# 6. Mode Visible / Tampak (Jendela browser terbuka untuk inspeksi visual)
python main.py --no-headless

# 7. Jalankan dengan URL Worker kustom langsung dari CLI
python main.py --worker-url "https://workerku.subdomain.workers.dev"

# 8. Menjalankan Auto-Refresher Daemon di latar belakang
python auto_refresh_tokens.py --loop
```

---

## ☁️ Setup Cloudflare Worker Mandiri (Gratis 2 Menit)

Template backend Cloudflare Worker sudah disediakan lengkap dan siap deploy di folder **`cloudflare_worker/`**.

1. Pastikan Node.js terpasang di komputer Anda.
2. Buka terminal di folder `cloudflare_worker/` lalu jalankan:
   ```bash
   npx wrangler d1 create tempmail_db
   ```
   *(Salin `database_id` yang muncul)*
3. Eksekusi skema tabel database D1:
   ```bash
   npx wrangler d1 execute tempmail_db --file=schema.sql --remote
   ```
4. Buka file `wrangler.toml`, masukkan `database_id` dari langkah di atas dan ganti `yourdomain.com` dengan domain Anda.
5. Deploy worker:
   ```bash
   npx wrangler deploy
   ```
   *(Cloudflare akan memberikan URL seperti: `https://grok-tempmail-worker.subdomain.workers.dev`)*
6. Di Cloudflare Dashboard: Buka **Domain Anda** -> **Email Routing** -> **Routing Rules** -> buat **Catch-All** rule dengan Action: **Send to a Worker** (pilih worker yang baru di-deploy).
7. Salin URL Worker Anda dan masukkan saat diminta di `run.bat` atau `main.py`. Panduan lengkap ada di `cloudflare_worker/README.md`.

---

## 🌐 Sistem Jaringan & Proxy (`proxies.txt`)

Script ini mendukung 3 mode koneksi fleksibel:

1. **Direct Ultra-Fast (Default & Paling Direkomendasikan)**:
   - Koneksi langsung tanpa melalui routing proxy eksternal.
   - Kecepatan maksimal: **18–25 detik per akun**.
   - Bebas latency handshake proxy.

2. **Rotating Proxy (`proxies.txt`)**:
   - Membaca file `proxies.txt` yang berisi daftar proxy (format `ip:port:user:pass`, `user:pass@ip:port`, atau `ip:port`).
   - Setiap worker dan setiap pembuatan akun baru secara otomatis mengambil IP berikutnya secara bergilir (*round-robin thread-safe*).
   - Browser Camoufox berjalan 100% menggunakan IP proxy tersebut.
   - Dilengkapi sistem *fail-safe* otomatis untuk polling OTP dan OAuth token jika terjadi *network drop* pada salah satu proxy.

3. **Cloudflare WARP**:
   - Menggunakan SOCKS5 proxy lokal dari client Cloudflare WARP (port `40001` atau `40002`).

---

## 📖 Penjelasan Parameter CLI (`main.py`)

| Flag / Opsi | Pilihan Nilai | Default | Penjelasan |
| :--- | :---: | :---: | :--- |
| `-n`, `--count` | Integer (`0`, `1`, `5`, dll) | `0` | Jumlah akun yang ingin dibuat. `0` = **Mode Tak Terbatas / Infinite Loop**. |
| `--unlimited` | Flag | `False` | Mengaktifkan Mode Tak Terbatas (terus membuat akun hingga Anda menekan `Ctrl+C`). |
| `-w`, `--workers` | Integer (`1` – `10`) | `5` | Jumlah worker browser paralel. Rekomendasi: RAM 8GB = 2 worker, RAM 16GB+ = 5 worker. |
| `-m`, `--proxy-mode` | `direct`, `proxy`, `warp` | Interaktif / `direct` | Pilihan mode jaringan: direct, rotating proxy dari `proxies.txt`, atau Cloudflare WARP. |
| `--proxies-file` | Path file | `proxies.txt` | Path kustom file daftar proxy jika berbeda dari `proxies.txt`. |
| `-p`, `--proxy` | URL string | `None` | Proxy kustom tunggal (misal: `socks5://127.0.0.1:40001` atau `http://user:pass@ip:port`). |
| `--warp` | Flag | `False` | Menggunakan Cloudflare WARP proxy lokal di port `40001` atau `40002`. |
| `--no-headless` | Flag | `False` | Menampilkan antarmuka jendela browser (bukan senyap). Bagus untuk verifikasi visual alur pendaftaran. |
| `--worker-url` | URL string | `None` / `config.json` | URL Cloudflare Worker kustom Anda (misal: `https://mail.domainanda.com`). |
| `--worker-domains` | List string | `None` / `config.json` | Daftar domain kustom yang terhubung ke Cloudflare Email Routing. |
| `--no-9router` | Flag | `False` | Melewati injeksi otomatis ke 9Router (hanya simpan ke JSON). |
| `-o`, `--output` | Path file | `grok_credentials.json` | Path kustom file penyimpanan kredensial JSON. |

---

## 🔄 Siklus Kredensial & Sinkronisasi 9Router

1. **Real-Time Injection**:
   Setiap kali **1 akun selesai** dibuat, kredensial langsung disimpan secara aman ke `grok_credentials.json` dan seketika diinjeksikan ke database SQLite **9Router** (`data.sqlite`). Anda tidak perlu menunggu seluruh batch selesai untuk mulai menggunakan model Grok.

2. **Model Gratis yang Otomatis Aktif di 9Router**:
   - `gcli/grok-4.7` *(Model penalaran unggulan xAI)*
   - `gcli/grok-4.6`
   - `gcli/grok-4.5`
   
   Model ini langsung bisa dipakai di **Cline**, **Cursor**, **Roo Code**, **OpenCode**, atau aplikasi AI lokal lainnya via endpoint:
   `http://127.0.0.1:20128/v1` dengan Header `Authorization: Bearer 9router`.

3. **Auto-Refresher (Mencegah Token Expired 6 Jam)**:
   OAuth token xAI memiliki masa aktif 6 jam. Jalankan:
   ```powershell
   python auto_refresh_tokens.py --loop
   ```
   Script ini akan berjalan di latar belakang dan memperbarui token secara bergilir setiap 3.5 jam, serta otomatis membersihkan token yang hangus (*revoked*).

---

## 🛠️ Arsitektur Ketahanan & Self-Healing

Modul ini telah dilengkapi perlindungan otomatis terhadap masalah umum:

1. **Kompatibilitas PyYAML CLoader (Python 3.10 – 3.15 Windows)**:
   Di Windows, beberapa instalasi Python tidak memiliki ekstensi C `CLoader`. Script secara otomatis menerapkan *self-healing shim* (`CLoader = Loader`) sebelum Camoufox dimuat, sehingga tidak akan memicu error `ImportError: cannot import name 'CLoader'`.
2. **Graceful Teardown Playwright**:
   Objek halaman (`page`) selalu ditutup secara eksplisit sebelum browser dimatikan, membungkam noise peringatan `TargetClosedError` dan `Task was destroyed but it is pending`.
3. **Zero-Zombie Process Killer**:
   Sebelum dan sesudah batch berjalan, script membersihkan proses yatim `node.exe` dan `camoufox.exe` agar RAM dan CPU tidak bocor.
4. **Resilient Replenishing Worker Loop**:
   Ketika satu worker selesai atau mengalami kendala, worker baru langsung diluncurkan seketika sehingga jumlah pool 5 worker selalu aktif 100% tanpa henti.
5. **CRLF & Batch Goto Parser Compatibility**:
   File `run.bat` dirancang khusus dengan label `goto` terisolasi dan format baris Windows CRLF standar untuk mencegah bug parser `cmd.exe`.

---

## 📂 Struktur File

```text
grok_cli/
├── run.bat                 # Launcher 1-klik dengan menu interaktif (Bebas error CRLF)
├── main.py                 # Core engine pendaftaran akun, proxy manager & infinite loop
├── proxies.txt             # Daftar 2.200+ proxy aktif (ip:port:user:pass)
├── tempmail.py             # Engine mailbox Cloudflare Worker (Custom Domain Catch-All)
├── config.json             # Konfigurasi worker URL, domain, dan preferensi
├── cloudflare_worker/      # Template backend worker Cloudflare D1 siap deploy (gratis)
├── inject_to_9router.py    # Modul penyimpan kredensial ke SQLite 9Router
├── auto_refresh_tokens.py  # Daemon pembaru token 6 jam otomatis
├── test_connection.py      # Penguji respon inferensi model ke 9Router
├── requirements.txt        # Dependensi paket Python
├── grok_credentials.json   # Penyimpanan kredensial akun hasil generate
└── README.md               # Dokumentasi panduan ini
```
