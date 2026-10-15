# ⚡ Cloudflare Email Worker for Grok CLI TempMail

Worker ini berfungsi menangkap email masuk dari **Cloudflare Email Routing** (*catch-all*) secara gratis, mengekstrak 6-digit kode OTP secara otomatis, dan menyediakannya via endpoint HTTP instan (`/code?email=...`).

---

## 🚀 Panduan Setup Singkat (2 Menit)

### 1. Buat Database D1
Di terminal komputer Anda:
```bash
npx wrangler d1 create tempmail_db
```
Salin `database_id` yang muncul ke file `wrangler.toml`.

### 2. Jalankan Skema Database
```bash
npx wrangler d1 execute tempmail_db --file=schema.sql --remote
```

### 3. Konfigurasi `wrangler.toml`
Buka `wrangler.toml`, sesuaikan:
```toml
[vars]
TEMPMAIL_DOMAIN = "domainanda.com"
TEMPMAIL_DOMAINS = "domainanda.com"

[[d1_databases]]
binding = "DB"
database_name = "tempmail_db"
database_id = "MASUKKAN_DATABASE_ID_DARI_LANGKAH_1"
```

### 4. Deploy Worker ke Cloudflare
```bash
npx wrangler deploy
```
Setelah deploy selesai, Cloudflare akan memberikan URL seperti:
`https://grok-tempmail-worker.subdomain.workers.dev`

### 5. Hubungkan Cloudflare Email Routing
1. Masuk ke Dashboard Cloudflare -> Pilih Domain Anda -> **Email Routing**.
2. Buka tab **Routing Rules** -> Tambahkan **Catch-all rule**.
3. Pilih Action: **Send to a Worker** -> Pilih Worker `grok-tempmail-worker`.
4. Simpan.

### 6. Hubungkan ke Grok CLI
Jalankan `run.bat` di folder utama Grok CLI:
- Pilih menu **`[5] Konfigurasi Worker & Manajemen Kredensial`**.
- Pilih **`[1] Atur Cloudflare Worker URL`**, lalu tempelkan URL Worker Anda:
  `https://grok-tempmail-worker.subdomain.workers.dev`
- Selesai! Grok CLI sekarang menggunakan domain kustom Anda sendiri.
