# AI Prospecting Agency — Free

Tujuan:
Mengumpulkan database prospek bisnis setiap hari untuk ditawari jasa landing page.
Pengiriman DM tetap dilakukan MANUAL oleh pemilik agency.

## Stack
- GitHub Actions
- Python
- Mesin pencari publik (Google/Bing/DuckDuckGo)
- Gemini 3.6 Flash Free Tier
- Google Apps Script
- Google Sheets

Gemini model ID yang digunakan:
`gemini-3.6-flash`

## Secrets GitHub
Buat 3 Repository Secrets:
- GEMINI_API_KEY
- SHEET_WEBHOOK_URL
- WEBHOOK_TOKEN

## Database
Google Apps Script membuat tab `Leads` otomatis.

Kolom:
Tanggal ditemukan | Nama bisnis | Instagram | URL Instagram | Kota |
Kategori | Bukti publik | Skor | Alasan | Prioritas | Status | Catatan DM

## Jadwal
02:00, 08:00, 14:00, 20:00 WIB.

## Catatan
Agent hanya mengambil profil yang terindeks pada web publik.
Agent tidak login ke Instagram dan tidak mengirim DM otomatis.
