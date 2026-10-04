# AI Prospecting Agency — GRATIS

Sistem ini mengumpulkan prospek bisnis setiap hari dan memasukkannya ke Google Sheets.
Kamu tetap melakukan DM/chat secara manual.

## Alur

GitHub Actions (terjadwal)
→ pencarian web publik
→ ambil profil Instagram bisnis yang terindeks
→ Gemini AI menyaring & memberi skor
→ Google Apps Script Web App
→ Google Sheets
→ kamu pilih prospek terbaik dan DM manual.

## Kenapa tidak login/scrape Instagram langsung?

Versi ini sengaja memakai hasil web publik yang mengindeks profil bisnis, bukan login akun Instagram atau bot yang mengakses endpoint internal Instagram.
Ini lebih sederhana untuk pemula dan mengurangi risiko akun terkena challenge/block.

## Yang dibutuhkan

1. Akun Google
2. Google Sheet
3. Google AI Studio API key (paket gratis / Free Tier)
4. Akun GitHub
5. Repo GitHub public untuk workflow terjadwal gratis

## Struktur

- `prospector.py` — mencari profil bisnis publik
- `gemini_scorer.py` — scoring prospek dengan Gemini
- `main.py` — menjalankan semuanya dan mengirim ke Google Sheets
- `apps-script/Code.gs` — endpoint Google Sheets
- `.github/workflows/daily.yml` — jalan otomatis setiap hari

## Kolom Google Sheets

Tanggal ditemukan | Nama bisnis | Instagram | URL Instagram | Kota | Kategori | Bukti publik | Skor | Alasan | Prioritas | Status | Catatan DM

Status awal: `BELUM DI-DM`

## Setup singkat

### A. Google Sheet

Buat Google Sheet baru.

Extensions → Apps Script.

Hapus isi `Code.gs` lalu paste file `apps-script/Code.gs`.

Di Apps Script:
Project Settings → Script Properties → Add Script Property:

`WEBHOOK_TOKEN` = buat token acak panjang, misalnya 32+ karakter.

Deploy → New deployment → Web app:
- Execute as: Me
- Who has access: Anyone

Salin URL Web App.

### B. Gemini API

Buka Google AI Studio dan buat API key.
Simpan sebagai GitHub Secret, jangan ditulis di file kode.

### C. GitHub

Buat repository PUBLIC, misalnya `ai-prospecting-agency`.

Upload:
- `prospector.py`
- `gemini_scorer.py`
- `main.py`
- `requirements.txt`
- folder `.github/workflows/daily.yml`

Repository → Settings → Secrets and variables → Actions → New repository secret:

`GEMINI_API_KEY`
`SHEET_WEBHOOK_URL`
`WEBHOOK_TOKEN`

Nilai `WEBHOOK_TOKEN` harus sama dengan Script Property di Apps Script.

### D. Aktifkan

GitHub → Actions → pilih workflow → Run workflow untuk tes pertama.

Setelah itu workflow berjalan otomatis setiap hari.

## Jadwal default

Workflow default dijalankan 1 kali sehari pukul 08:00 WIB (01:00 UTC).

Untuk lebih agresif, ubah cron:
- 08:00 WIB = `0 1 * * *`
- 14:00 WIB = `0 7 * * *`
- 20:00 WIB = `0 13 * * *`

Jangan membuat volume terlalu besar. Free tier Gemini memiliki batas RPM/TPM/RPD yang dapat berbeda menurut model/project. 
