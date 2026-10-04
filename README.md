# AI Prospecting Agency — Nasional

Tujuan:
Mengumpulkan kandidat prospek bisnis Indonesia untuk ditawari jasa landing page.

Alur:
Web publik → Jina Reader → kandidat Instagram → Gemini 3.6 Flash → Google Sheets.

Tidak ada login Instagram dan tidak ada auto-DM.

## Volume target

Konfigurasi:
- 12 query per run
- maksimal 100 kandidat yang dinilai AI per run
- 4 scheduled runs per hari
- kapasitas teoritis maksimal 400 baris kandidat/hari

Catatan: 400/hari adalah batas konfigurasi, bukan jaminan. Hasil nyata
bergantung pada jumlah profil publik yang ditemukan, duplikasi, dan rate limit.

## Gemini

Model:
`gemini-3.6-flash`

## GitHub Secrets

- GEMINI_API_KEY
- SHEET_WEBHOOK_URL
- WEBHOOK_TOKEN

## Jadwal WIB

02:00
08:00
14:00
20:00

## Google Sheet

Nama tab:
`Leads`

Kolom:
Tanggal ditemukan | Nama bisnis | Instagram | URL Instagram | Kota |
Kategori | Bukti publik | Skor | Alasan | Prioritas | Status | Catatan DM

Status awal:
`BELUM DI-DM`

## Search layer

Menggunakan Jina Reader untuk membaca halaman pencarian web publik.
Jina mencantumkan 20 RPM untuk Reader API tanpa API key; free API key dapat
memberikan rate limit yang lebih tinggi. Jangan menganggap volume unlimited.

## Catatan penting

Agent hanya mengambil hasil web publik yang dapat diakses.
Kualitas data bergantung pada hasil index mesin pencari.
Gunakan database ini untuk outreach manual yang relevan, bukan spam massal.
