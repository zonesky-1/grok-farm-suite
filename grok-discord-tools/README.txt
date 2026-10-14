=============================================================================
             9ROUTER GROK CLI AUTO-CREATE & 9ROUTER ENGINE
=============================================================================

Tools ini digunakan untuk membuat akun resmi xAI Grok (Grok CLI) secara 
100% otomatis (hands-free) dan langsung mengkoneksikannya ke 9Router 
(TANPA VPN / Direct Connection).

Model AI yang otomatis aktif di 9Router:
- gcli/grok-build
- gcli/grok-4.5
- gcli/grok-4.5-high
- gcli/grok-4.5-medium
- gcli/grok-4.5-low

-----------------------------------------------------------------------------
CARA SETUP CEPAT:
-----------------------------------------------------------------------------

1. INSTALL DEPENDENSI (Cukup 1x di awal):
   - Double-click '1_Setup_Install.bat'

2. SETUP CLOUDFLARE EMAIL WORKER:
   - Buka file 'PANDUAN_SETUP_CLOUDFLARE.txt' untuk panduan lengkapnya.
   - Deploy file 'cloudflare_worker.js' ke Cloudflare Workers Anda.
   - Hubungkan Cloudflare Email Routing domain Anda ke Worker tersebut.

3. ISI 'config.json':
   - Masukkan URL Worker (.workers.dev) & domain Anda di 'config.json'.

4. JALANKAN AUTO-CREATE & CONNECT:
   - Double-click '0_AUTO_CREATE_AND_CONNECT_9ROUTER.bat'
   - Masukkan jumlah akun (misal: 5, 10, atau 20) & pilih worker.
   - Selesai! Semua akun langsung aktif di 9Router & tersimpan di 'accounts.txt'.

=============================================================================
