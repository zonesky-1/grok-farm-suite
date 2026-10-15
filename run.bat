@echo off
setlocal enabledelayedexpansion
title Grok CLI (xAI) Auto-Farming Launcher
color 0B
chcp 65001 >nul

cd /d "%~dp0"

echo ======================================================================
echo    GROK CLI (xAI) AUTO-REGISTER ^& 9ROUTER INJECTOR LAUNCHER
echo ======================================================================
echo.

REM 1. Verifikasi Python
set "PY_CMD="

REM Prioritaskan Python Launcher (py) versi stabil
py -3.12 --version >nul 2>&1 && set "PY_CMD=py -3.12"
if "!PY_CMD!"=="" (
    py -3.13 --version >nul 2>&1 && set "PY_CMD=py -3.13"
)
if "!PY_CMD!"=="" (
    py -3.11 --version >nul 2>&1 && set "PY_CMD=py -3.11"
)
if "!PY_CMD!"=="" (
    py -3.14 --version >nul 2>&1 && set "PY_CMD=py -3.14"
)
if "!PY_CMD!"=="" (
    py -3.10 --version >nul 2>&1 && set "PY_CMD=py -3.10"
)

REM Cek folder instalasi standar Windows
if "!PY_CMD!"=="" (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD=\"%LOCALAPPDATA%\Programs\Python\Python312\python.exe\""
)
if "!PY_CMD!"=="" (
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY_CMD=\"%LOCALAPPDATA%\Programs\Python\Python313\python.exe\""
)
if "!PY_CMD!"=="" (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_CMD=\"%LOCALAPPDATA%\Programs\Python\Python311\python.exe\""
)
if "!PY_CMD!"=="" (
    if exist "%ProgramFiles%\Python312\python.exe" set "PY_CMD=\"%ProgramFiles%\Python312\python.exe\""
)
if "!PY_CMD!"=="" (
    if exist "%ProgramFiles%\Python313\python.exe" set "PY_CMD=\"%ProgramFiles%\Python313\python.exe\""
)
if "!PY_CMD!"=="" (
    if exist "%ProgramFiles%\Python311\python.exe" set "PY_CMD=\"%ProgramFiles%\Python311\python.exe\""
)

REM Cek perintah umum python / py di PATH
if "!PY_CMD!"=="" (
    python --version >nul 2>&1 && set "PY_CMD=python"
)
if "!PY_CMD!"=="" (
    py --version >nul 2>&1 && set "PY_CMD=py"
)

if "!PY_CMD!"=="" goto NO_PYTHON_FOUND
goto PY_READY

:NO_PYTHON_FOUND
color 0E
echo ======================================================================
echo  [!] Python belum terdeteksi di komputer ini.
echo ======================================================================
echo  Ingin memasang Python 3.12 (Stable) secara otomatis?
echo.
echo   [1] Pasang Otomatis Sekarang (Praktis ^& Instan)
echo   [2] Batal / Keluar
echo.
set /p auto_py=">> Masukkan pilihan [1/2, Default: 1]: "
if "!auto_py!"=="" set auto_py=1
if not "!auto_py!"=="1" exit /b 1

echo.
echo [*] Mengunduh installer resmi Python 3.12 dari python.org...
curl -sSL -o "%TEMP%\python-3.12-installer.exe" https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe
if not exist "%TEMP%\python-3.12-installer.exe" (
    echo [!] Gagal mengunduh installer. Periksa koneksi internet Anda.
    pause
    exit /b 1
)

echo [*] Memasang Python 3.12 di latar belakang (mohon tunggu ~20 detik)...
start /wait "" "%TEMP%\python-3.12-installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 SimpleInstall=1
del /f /q "%TEMP%\python-3.12-installer.exe" >nul 2>&1

set "PY_CMD=\"%LOCALAPPDATA%\Programs\Python\Python312\python.exe\""
if not exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    python --version >nul 2>&1 && set "PY_CMD=python"
)

if "!PY_CMD!"=="" (
    echo [!] Instalasi selesai tapi belum masuk PATH sesi ini.
    echo Silakan tutup jendela ini dan buka kembali run.bat.
    pause
    exit /b 0
)
echo [✓] Python 3.12 berhasil dipasang!
echo.

:PY_READY

REM 2. Verifikasi Visual C++ Redistributable
if not exist "%SystemRoot%\System32\vcruntime140.dll" (
    color 0E
    echo [!] PERINGATAN: Visual C++ Redistributable x64 belum terdeteksi.
    echo Browser stealth Camoufox membutuhkan Microsoft Visual C++ 2015-2022.
    echo Unduh jika diperlukan: https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo.
    color 0B
)

REM 3. Auto-Install Dependencies
%PY_CMD% -c "import camoufox, playwright, requests" >nul 2>&1
if errorlevel 1 %PY_CMD% -m pip install -r requirements.txt --disable-pip-version-check

%PY_CMD% -c "import yaml; yaml.CLoader = getattr(yaml, 'CLoader', yaml.Loader); import os; from camoufox.pkgman import launch_path; p = launch_path(); exit(0 if (p and os.path.exists(p)) else 1)" >nul 2>&1
if errorlevel 1 %PY_CMD% -m camoufox fetch

:MENU
cls
REM Baca konfigurasi dari config.json
set "CFG_WORKER_URL="
set "CFG_DOMAINS="
set "CFG_WORKERS=5"
set "CFG_AUTO_INJECT=1"
for /f "delims=" %%A in ('%PY_CMD% -c "import json, os; f='config.json'; d=json.loads(open(f, encoding='utf-8').read()) if os.path.exists(f) else {}; print(d.get('worker_url', ''))" 2^>nul') do set "CFG_WORKER_URL=%%A"
for /f "delims=" %%A in ('%PY_CMD% -c "import json, os; f='config.json'; d=json.loads(open(f, encoding='utf-8').read()) if os.path.exists(f) else {}; print(' '.join(d.get('worker_domains', [])))" 2^>nul') do set "CFG_DOMAINS=%%A"
for /f %%A in ('%PY_CMD% -c "import json, os; f='config.json'; d=json.loads(open(f, encoding='utf-8').read()) if os.path.exists(f) else {}; print(d.get('concurrency', 5))" 2^>nul') do set "CFG_WORKERS=%%A"
for /f %%A in ('%PY_CMD% -c "import json, os; f='config.json'; d=json.loads(open(f, encoding='utf-8').read()) if os.path.exists(f) else {}; print(1 if d.get('auto_inject_9router', True) else 0)" 2^>nul') do set "CFG_AUTO_INJECT=%%A"

if not "!CFG_WORKER_URL!"=="" (
    set "MAIL_INFO=Cloudflare Worker (!CFG_WORKER_URL!)"
) else (
    set "MAIL_INFO=[PERINGATAN] BELUM DIATUR (Wajib Cloudflare Worker Sendiri)"
)
if "!CFG_AUTO_INJECT!"=="1" (
    set "INJECT_INFO=Aktif (Real-Time)"
) else (
    set "INJECT_INFO=Nonaktif (Hanya JSON)"
)

REM Hitung jumlah kredensial tersimpan saat ini
for /f %%A in ('%PY_CMD% -c "import json, os; f='grok_credentials.json'; print(len(json.loads(open(f, encoding='utf-8').read())) if os.path.exists(f) and open(f, encoding='utf-8').read().strip() else 0)" 2^>nul') do set "CRED_COUNT=%%A"
if "!CRED_COUNT!"=="" set "CRED_COUNT=0"

echo ======================================================================
echo    ⚡ GROK CLI (xAI) AUTO-FARMING ^& 9ROUTER INJECTOR LAUNCHER
echo ======================================================================
echo  [Info Sistem]
echo   - TempMail Engine : !MAIL_INFO!
echo   - Akun Tersimpan  : !CRED_COUNT! Akun (grok_credentials.json)
echo   - Default Worker  : !CFG_WORKERS! Worker Paralel
echo   - Auto-Inject 9R  : !INJECT_INFO!
echo ======================================================================
echo.
echo  Pilih Operasi:
echo.
echo   [1] Bulk Farming Tak Terbatas Turbo (!CFG_WORKERS! Worker - Non-Stop)
echo   [2] Buat Akun Tertentu (Tentukan Jumlah Akun ^& Worker)
echo   [3] Bulk Farming Tak Terbatas Hemat RAM (2 Worker)
echo   [4] Mode Kustom Lengkap (Jumlah Akun, Worker, Proxy, Browser, dll)
echo.
echo  Pengaturan ^& Utilitas:
echo   [5] Konfigurasi Cloudflare Worker ^& Kredensial (Panduan Setup / URL)
echo   [6] Jalankan Auto-Refresher Daemon (Refresh Token Tiap 3.5 Jam)
echo   [7] Sinkronkan Ulang Akun ke 9Router (Manual Sync)
echo   [8] Tes Inferensi Model Grok di 9Router (test_connection.py)
echo.
echo   [0] Keluar
echo ======================================================================
set /p opt="Masukkan pilihan [1-8, 0]: "

if "%opt%"=="1" (
    if "!CFG_WORKER_URL!"=="" goto PROMPT_SETUP_WORKER
    goto OPT1
)
if "%opt%"=="2" (
    if "!CFG_WORKER_URL!"=="" goto PROMPT_SETUP_WORKER
    goto OPT2
)
if "%opt%"=="3" (
    if "!CFG_WORKER_URL!"=="" goto PROMPT_SETUP_WORKER
    goto OPT3
)
if "%opt%"=="4" (
    if "!CFG_WORKER_URL!"=="" goto PROMPT_SETUP_WORKER
    goto OPT4
)
if "%opt%"=="5" goto OPT5
if "%opt%"=="6" goto OPT6
if "%opt%"=="7" goto OPT7
if "%opt%"=="8" goto OPT8
if "%opt%"=="0" goto OPT0
goto MENU

:PROMPT_SETUP_WORKER
cls
color 0E
echo ======================================================================
echo    [!] PERHATIAN: CLOUDFLARE WORKER BELUM DIKONFIGURASI
echo ======================================================================
echo.
echo  xAI memblokir seluruh domain email disposable publik gratisan.
echo  Agar akun tidak terblokir, Anda wajib menggunakan Cloudflare Worker
echo  dengan domain kustom Anda sendiri (Cloudflare Email Routing Catch-All).
echo.
echo  ------------------------------------------------------------------
echo  TATA CARA SETUP CEPAT (2 MENIT):
echo  ------------------------------------------------------------------
echo   1. Buka folder: cloudflare_worker\
echo   2. Jalankan perintah di terminal:
echo        npx wrangler d1 create tempmail_db
echo        npx wrangler d1 execute tempmail_db --file=schema.sql --remote
echo   3. Buka wrangler.toml -^> masukkan database_id dan domain Anda.
echo   4. Deploy: npx wrangler deploy
echo   5. Di Cloudflare Dashboard: Domain -^> Email Routing -^> Catch-all
echo      pilih Action: Send to a Worker (pilih worker Anda).
echo.
echo  Panduan langkah demi langkah lengkap ada di: cloudflare_worker\README.md
echo ======================================================================
echo.
echo  Sudah memiliki URL Cloudflare Worker yang aktif?
set /p quick_url=">> Masukkan URL Worker Anda sekarang (Enter untuk kembali): "
if not "!quick_url!"=="" (
    %PY_CMD% -c "import sys, json, os; f='config.json'; d=json.loads(open(f, encoding='utf-8').read()) if os.path.exists(f) else {}; u=sys.argv[1].strip().strip('\"\'').rstrip('/'); u='https://'+u if u and not u.startswith(('http://','https://')) else u; d['worker_url']=u; open(f, 'w', encoding='utf-8').write(json.dumps(d, indent=2))" "!quick_url!"
    for /f "delims=" %%A in ('%PY_CMD% -c "import json; print(json.load(open('config.json')).get('worker_url',''))"') do set "CFG_WORKER_URL=%%A"
    set "MAIL_INFO=Cloudflare Worker (!CFG_WORKER_URL!)"
    color 0B
    echo.
    echo [✓] Cloudflare Worker URL berhasil disimpan: !CFG_WORKER_URL!
    echo [*] Melanjutkan ke operasi menu [!opt!]...
    timeout /t 2 >nul 2>&1
    if "!opt!"=="1" goto OPT1
    if "!opt!"=="2" goto OPT2
    if "!opt!"=="3" goto OPT3
    if "!opt!"=="4" goto OPT4
    goto MENU
)
color 0B
echo.
echo [*] Konfigurasi Worker dibatalkan. Kembali ke menu utama.
timeout /t 2 >nul 2>&1
goto MENU

:OPT1
cls
echo ======================================================================
echo    BULK FARMING TAK TERBATAS TURBO (NON-STOP HINGGA CTRL+C)
echo ======================================================================
echo.
set /p w_choice=">> Tentukan jumlah worker paralel [Default: !CFG_WORKERS!, Enter untuk lanjut]: "
if "!w_choice!"=="" set w_choice=!CFG_WORKERS!

echo.
echo  Pilih Mode Koneksi Jaringan:
echo   [1] Direct Ultra-Fast (Direkomendasikan: 18-25s, Tanpa Proxy) [Default]
echo   [2] Rotating Proxy (proxies.txt - 2.200+ IP aktif berganti otomatis)
echo   [3] Cloudflare WARP (Port 40001/40002)
echo.
set /p conn_opt=">> Pilih mode [1/2/3, Default: 1]: "
if "!conn_opt!"=="" set conn_opt=1
set p_flag=--proxy-mode direct
if "!conn_opt!"=="2" set p_flag=--proxy-mode proxy
if "!conn_opt!"=="3" set p_flag=--proxy-mode warp

set inj_flag=
if "!CFG_AUTO_INJECT!"=="0" set inj_flag=--no-9router

cls
echo [*] Memulai Bulk Farming TAK TERBATAS dengan !w_choice! worker paralel...
echo [*] Engine TempMail: !MAIL_INFO!
echo [*] Mode Koneksi: !p_flag!
echo [*] Tiap akun selesai otomatis tersimpan ke grok_credentials.json
echo [*] Tekan tombol Ctrl + C kapan saja di keyboard untuk berhenti.
echo.
%PY_CMD% main.py -n 0 -w !w_choice! !p_flag! !inj_flag!
echo.
pause
goto MENU

:OPT2
cls
echo ======================================================================
echo    BUAT AKUN TERTENTU (TESTING / JUMLAH TERUKUR)
echo ======================================================================
echo.
set /p acc_num=">> Masukkan jumlah akun yang ingin dibuat [Default: 1]: "
if "!acc_num!"=="" set acc_num=1

set /p w_num=">> Masukkan jumlah worker paralel [Default: 1]: "
if "!w_num!"=="" set w_num=1

echo.
echo  Pilih Mode Koneksi Jaringan:
echo   [1] Direct Ultra-Fast [Default]
echo   [2] Rotating Proxy (proxies.txt)
echo   [3] Cloudflare WARP
echo.
set /p conn_opt=">> Pilih mode [1/2/3, Default: 1]: "
if "!conn_opt!"=="" set conn_opt=1
set p_flag=--proxy-mode direct
if "!conn_opt!"=="2" set p_flag=--proxy-mode proxy
if "!conn_opt!"=="3" set p_flag=--proxy-mode warp

set inj_flag=
if "!CFG_AUTO_INJECT!"=="0" set inj_flag=--no-9router

cls
echo.
echo [*] Menjalankan pembuatan !acc_num! akun Grok CLI dengan !w_num! worker...
echo [*] Engine TempMail: !MAIL_INFO!
echo.
%PY_CMD% main.py -n !acc_num! -w !w_num! !p_flag! !inj_flag!
echo.
pause
goto MENU

:OPT3
cls
echo ======================================================================
echo    BULK FARMING TAK TERBATAS STABIL (2 WORKER PARALEL - HEMAT RAM)
echo ======================================================================
echo.
echo  Pilih Mode Koneksi Jaringan:
echo   [1] Direct Ultra-Fast [Default]
echo   [2] Rotating Proxy (proxies.txt)
echo   [3] Cloudflare WARP
echo.
set /p conn_opt=">> Pilih mode [1/2/3, Default: 1]: "
if "!conn_opt!"=="" set conn_opt=1
set p_flag=--proxy-mode direct
if "!conn_opt!"=="2" set p_flag=--proxy-mode proxy
if "!conn_opt!"=="3" set p_flag=--proxy-mode warp

set inj_flag=
if "!CFG_AUTO_INJECT!"=="0" set inj_flag=--no-9router

cls
echo [*] Menjalankan pembuatan akun tanpa henti (2 Worker Paralel)...
echo [*] Engine TempMail: !MAIL_INFO!
echo [*] Tekan tombol Ctrl + C kapan saja di keyboard untuk berhenti.
echo.
%PY_CMD% main.py -n 0 -w 2 !p_flag! !inj_flag!
echo.
pause
goto MENU

:OPT4
cls
echo ======================================================================
echo    PENGATURAN KUSTOM LENGKAP GROK CLI
echo ======================================================================
echo.
set /p custom_count=">> Masukkan target jumlah akun [0 = Tak Terbatas, Default: 5]: "
if "!custom_count!"=="" set custom_count=5

set /p custom_workers=">> Masukkan jumlah worker paralel [Default: !CFG_WORKERS!]: "
if "!custom_workers!"=="" set custom_workers=!CFG_WORKERS!

echo.
echo  Pilih Mode Koneksi:
echo   [1] Direct Ultra-Fast (Default)
echo   [2] Rotating Proxy (proxies.txt)
echo   [3] Cloudflare WARP
echo.
set /p conn_opt=">> Pilih mode [1/2/3, Default: 1]: "
if "!conn_opt!"=="" set conn_opt=1
set p_flag=--proxy-mode direct
if "!conn_opt!"=="2" set p_flag=--proxy-mode proxy
if "!conn_opt!"=="3" set p_flag=--proxy-mode warp

echo.
echo  Mode Tampilan Browser:
echo   [1] Headless (Senyap di latar belakang - Default)
echo   [2] Visible (Tampilkan jendela browser Camoufox)
echo.
set /p mode_vis=">> Pilih mode [1/2, Default: 1]: "
set extra_flags=
if "!mode_vis!"=="2" set extra_flags=--no-headless

echo.
echo  Injeksi Otomatis ke 9Router:
echo   [1] Ya, langsung injeksi ke 9Router (Default)
echo   [2] Tidak, hanya simpan ke file JSON
echo.
set /p opt_inj=">> Pilih opsi [1/2, Default: 1]: "
if "!opt_inj!"=="2" set extra_flags=!extra_flags! --no-9router

cls
echo [*] Memulai pembuatan !custom_count! akun dengan !custom_workers! worker...
echo [*] Mode Koneksi: !p_flag!
echo.
%PY_CMD% main.py -n !custom_count! -w !custom_workers! !p_flag! !extra_flags!
echo.
pause
goto MENU

:OPT5
cls
set "CFG_WORKER_DISP=!CFG_WORKER_URL!"
if "!CFG_WORKER_DISP!"=="" set "CFG_WORKER_DISP=(BELUM DIKONFIGURASI)"
set "CFG_DOMAINS_DISP=!CFG_DOMAINS!"
if "!CFG_DOMAINS_DISP!"=="" set "CFG_DOMAINS_DISP=(Otomatis dari Worker)"

echo ======================================================================
echo    ⚙️  KONFIGURASI CLOUDFLARE WORKER ^& KREDENSIAL (config.json)
echo ======================================================================
echo.
echo   [1] Atur Cloudflare Worker URL
echo       Saat ini: !CFG_WORKER_DISP!
echo.
echo   [2] Atur Domain Worker Kustom
echo       Saat ini: !CFG_DOMAINS_DISP!
echo.
echo   [3] Tampilkan Tata Cara / Panduan Setup Cloudflare Worker (2 Menit)
echo.
echo   [4] Ubah Default Jumlah Worker Paralel (Saat ini: !CFG_WORKERS! Worker)
echo   [5] Toggle Injeksi Otomatis ke 9Router (Saat ini: !INJECT_INFO!)
echo   [6] Lihat Daftar Akun Tersimpan di grok_credentials.json
echo   [7] Kosongkan Seluruh Kredensial Lokal (Hapus Akun / [])
echo   [8] Bersihkan Akun Grok di Database 9Router Lokal (Reset Total)
echo.
echo   [0] Kembali ke Menu Utama
echo ======================================================================
set /p cfg_opt=">> Masukkan pilihan [1-8, 0]: "

if "%cfg_opt%"=="1" (
    echo.
    echo Masukkan URL Cloudflare Worker Anda (misal: https://workerku.subdomain.workers.dev)
    echo Tekan Enter langsung jika ingin mengosongkan / membatalkan:
    set /p new_w_url=">> Worker URL: "
    %PY_CMD% -c "import sys, json, os; f='config.json'; d=json.loads(open(f, encoding='utf-8').read()) if os.path.exists(f) else {}; u=sys.argv[1].strip().strip('\"\'').rstrip('/'); u='https://'+u if u and not u.startswith(('http://','https://')) else u; d['worker_url']=u; open(f, 'w', encoding='utf-8').write(json.dumps(d, indent=2))" "!new_w_url!"
    for /f "delims=" %%A in ('%PY_CMD% -c "import json; print(json.load(open('config.json')).get('worker_url',''))"') do set "CFG_WORKER_URL=%%A"
    set "MAIL_INFO=Cloudflare Worker (!CFG_WORKER_URL!)"
    echo [✓] Worker URL berhasil diperbarui!
    pause
    goto OPT5
)
if "%cfg_opt%"=="2" (
    echo.
    echo Masukkan domain kustom yang terhubung ke Cloudflare Email Routing.
    echo (Pisahkan dengan spasi jika lebih dari 1 domain, misal: domainku.com email2.com)
    set /p new_w_doms=">> Domain(s): "
    %PY_CMD% -c "import json, os; f='config.json'; d=json.loads(open(f, encoding='utf-8').read()) if os.path.exists(f) else {}; d['worker_domains']='!new_w_doms!'.strip().split() if '!new_w_doms!'.strip() else []; open(f, 'w', encoding='utf-8').write(json.dumps(d, indent=2))"
    echo [✓] Daftar domain worker berhasil diperbarui!
    pause
    goto OPT5
)
if "%cfg_opt%"=="3" (
    cls
    echo ======================================================================
    echo    📖 TATA CARA SETUP CLOUDFLARE WORKER MANDIRI (GRATIS ^& 2 MENIT)
    echo ======================================================================
    echo.
    echo  Modul ini memerlukan Cloudflare Worker untuk menerima email OTP
    echo  secara real-time melalui domain kustom Anda.
    echo.
    echo  Langkah-langkah:
    echo  1. Pastikan Node.js terpasang di komputer Anda.
    echo  2. Buka terminal command prompt di folder:
    echo        cloudflare_worker\
    echo  3. Jalankan perintah pembuatan database D1:
    echo        npx wrangler d1 create tempmail_db
    echo     (Salin database_id yang muncul)
    echo.
    echo  4. Eksekusi skema tabel email:
    echo        npx wrangler d1 execute tempmail_db --file=schema.sql --remote
    echo.
    echo  5. Buka file wrangler.toml di notepad, sesuaikan:
    echo        TEMPMAIL_DOMAIN = "domainanda.com"
    echo        database_id     = "id-dari-langkah-3"
    echo.
    echo  6. Deploy worker ke Cloudflare:
    echo        npx wrangler deploy
    echo.
    echo  7. Di Dashboard Cloudflare:
    echo        Buka Domain Anda -^> Email Routing -^> Routing Rules
    echo        Buat Catch-All rule dengan action: "Send to a Worker"
    echo        Pilih worker yang baru saja Anda deploy.
    echo.
    echo  8. Salin URL Worker Anda lalu masukkan pada menu [1] di sini.
    echo.
    echo  Panduan selengkapnya tertulis di: cloudflare_worker\README.md
    echo ======================================================================
    pause
    goto OPT5
)
if "%cfg_opt%"=="4" (
    echo.
    set /p new_w=">> Masukkan jumlah worker default baru [1-10]: "
    if not "!new_w!"=="" (
        %PY_CMD% -c "import json, os; f='config.json'; d=json.loads(open(f, encoding='utf-8').read()) if os.path.exists(f) else {}; d['concurrency']=int('!new_w!'); open(f, 'w', encoding='utf-8').write(json.dumps(d, indent=2))"
        echo [✓] Default worker berhasil disimpan!
    )
    pause
    goto OPT5
)
if "%cfg_opt%"=="5" (
    %PY_CMD% -c "import json, os; f='config.json'; d=json.loads(open(f, encoding='utf-8').read()) if os.path.exists(f) else {}; cur=d.get('auto_inject_9router', True); d['auto_inject_9router']=not cur; open(f, 'w', encoding='utf-8').write(json.dumps(d, indent=2)); print('[✓] Status Injeksi Otomatis 9Router diubah menjadi:', 'AKTIF' if not cur else 'NONAKTIF')"
    pause
    goto OPT5
)
if "%cfg_opt%"=="6" (
    cls
    echo [*] Membaca grok_credentials.json...
    echo.
    %PY_CMD% -c "import json, os; f='grok_credentials.json'; d=json.loads(open(f, encoding='utf-8').read()) if os.path.exists(f) and open(f, encoding='utf-8').read().strip() else []; print(f'Total: {len(d)} akun tersimpan\n'); [print(f' - #{i+1}: {acc.get(\"email\")} (User ID: {acc.get(\"userId\", \"-\")[:8]}...)') for i, acc in enumerate(d)]"
    echo.
    pause
    goto OPT5
)
if "%cfg_opt%"=="7" (
    echo.
    echo [!] PERINGATAN: Opsi ini akan mengosongkan isi grok_credentials.json menjadi []
    set /p conf_del=">> Apakah Anda yakin ingin mengosongkan kredensial? [y/N]: "
    if /i "!conf_del!"=="y" (
        %PY_CMD% -c "open('grok_credentials.json', 'w', encoding='utf-8').write('[]\n')"
        echo [✓] Seluruh kredensial di grok_credentials.json berhasil dikosongkan!
    ) else (
        echo [*] Dibatalkan.
    )
    pause
    goto OPT5
)
if "%cfg_opt%"=="8" (
    echo.
    echo [!] PERINGATAN: Menghapus semua providerConnections grok-cli di 9Router (data.sqlite)
    set /p conf_db=">> Apakah Anda yakin ingin membersihkan database 9Router untuk Grok? [y/N]: "
    if /i "!conf_db!"=="y" (
        %PY_CMD% -c "import sqlite3; from inject_to_9router import get_db_path; p=get_db_path(); conn=sqlite3.connect(p); cur=conn.cursor(); cur.execute(\"DELETE FROM providerConnections WHERE provider='grok-cli'\"); conn.commit(); print('[✓] Berhasil menghapus', cur.rowcount, 'koneksi grok-cli dari 9Router!')"
    ) else (
        echo [*] Dibatalkan.
    )
    pause
    goto OPT5
)
goto MENU

:OPT6
cls
echo [*] Memulai Token Auto-Refresher Daemon...
%PY_CMD% auto_refresh_tokens.py --loop
pause
goto MENU

:OPT7
cls
echo [*] Menyinkronkan seluruh kredensial ke database 9Router...
%PY_CMD% inject_to_9router.py
echo.
pause
goto MENU

:OPT8
cls
echo [*] Menguji respon inferensi model ke 9Router...
%PY_CMD% test_connection.py
echo.
pause
goto MENU

:OPT0
exit /b 0
