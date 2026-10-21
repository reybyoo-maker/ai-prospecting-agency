# Sonjaya AI Remote Agency

Production system sekarang hanya memiliki **2 flow aktif**.

## FLOW 1 — SALES TEAM

Alur:

`Discovery web publik -> validasi email publik -> Gemini research/scoring -> Google Sheets -> kirim otomatis -> follow-up otomatis -> deteksi reply -> balasan contextual AI -> WhatsApp handoff`

### Discovery
- GitHub Actions berjalan terjadwal setiap 2 jam.
- Mesin mencari bisnis Indonesia dari web publik.
- Kandidat tanpa email publik dibuang.
- Email dideduplicasi.
- Evidence publik disimpan.
- Gemini memilih kebutuhan/service berdasarkan evidence.
- Lead dengan skor >= 75 masuk status `READY`; sisanya `REVIEW`.

### Automatic email
Email pertama sekarang **tidak lagi manual**.

GitHub Actions menjalankan satu sales cycle setiap 2 jam:
1. discovery + scoring + queueing lead baru,
2. scan reply terbaru,
3. proses follow-up yang sudah jatuh tempo,
4. proses follow-up yang sudah jatuh tempo terlebih dahulu, lalu gunakan sisa kuota harian untuk email awal READY (prioritas skor tertinggi); gabungan email awal dan follow-up otomatis dibatasi **maksimal 20 pesan per hari WIB**.

Setelah initial email berhasil:
`SENT -> FOLLOWUP_1 (+2 hari) -> FOLLOWUP_2 (+5 hari) -> FOLLOWUP_3 (+9 hari) -> FOLLOWUP_DONE`

Jika prospek membalas, follow-up berhenti. Jika mereka mengirim `UNSUBSCRIBE`, status berubah menjadi `OPTOUT` dan komunikasi berikutnya dihentikan.

Semua pengiriman menggunakan lock, retry/error state, Lead ID, dan subject tag `[SJ-xxxxxxxxxxxx]` agar thread dapat dilacak.

### Daily automated email limit
- Batas keras sistem adalah **maksimal 20 email otomatis per hari kalender WIB**, mencakup balasan AI kepada prospek, follow-up terjadwal, dan email awal.
- Batas yang sama dihitung lintas workflow menggunakan counter harian di Apps Script Properties; menjalankan workflow berulang kali tidak mengatur ulang batas.
- Prioritas pengiriman: balasan prospek yang sudah masuk, kemudian follow-up yang jatuh tempo, lalu email awal ke prospek baru.
- Sistem tetap memindai email masuk untuk memproses permintaan `UNSUBSCRIBE`, meskipun kuota pengiriman otomatis hari itu telah habis.
- Semua jenis email otomatis tunduk pada kuota akun Google melalui `MailApp.getRemainingDailyQuota()`; sistem memakai batas yang lebih rendah antara kuota Google dan batas internal 20 email per hari.
- Sebelum mengirim, GitHub Actions memeriksa bahwa Apps Script live sudah menggunakan versi `2026-10-21.1`. Jika belum, tahap pengiriman otomatis dilewati agar versi lama tidak mengirim melebihi batas; lead tetap dapat ditemukan dan dimasukkan ke antrean.
- Agar pengiriman aktif kembali, salin `apps-script/Code.gs` versi terbaru ke Google Apps Script lalu simpan dan perbarui deployment Web App. Setelah endpoint mengembalikan versi `2026-10-21.1`, workflow berikutnya akan melanjutkan pengiriman.

### Main service offer
Layanan utama yang ditawarkan melalui email prospek adalah **otomasi workflow menggunakan n8n yang dirancang berjalan 24/7** sesuai kebutuhan dan konfigurasi operasional bisnis. Email awal dan follow-up mengarahkan penerima ke portofolio: https://agencyai.reybyoo.workers.dev/

## FLOW 2 — CONTENT STUDIO

Tidak ada lagi auto-upload.

Alur:

`Content strategy -> Gemini script -> quality gate -> 7-slide feed carousel -> JPG/PNG/PDF -> Google Sheets -> manual upload oleh tim`

### Content standard
Setiap batch membuat 7 hari konten.

Struktur setiap carousel:
1. Hook
2. Problem
3. Insight
4. Framework
5. Example
6. Mistake / objection
7. CTA

Setiap hari menggunakan pilar berbeda dan design family berbeda.

Design family:
- BOLD_EDITORIAL
- SPLIT_SCREEN
- DASHBOARD
- FLOW_DIAGRAM
- CARD_STACK
- TYPE_POSTER
- MINIMAL_TECH

Standar copy:
- Bahasa Indonesia natural.
- 1 gagasan utama per slide.
- Headline kuat dan ringkas.
- Contoh operasional realistis.
- Tidak mengarang testimonial, omzet, statistic, client, pricing, atau performance.
- Soft selling maksimum satu slide.
- CTA bervariasi.
- Tidak menggunakan slogan AI generik atau clickbait murahan.

### Output Content Planning
Google Sheets `Content Planning` menyimpan:
- tanggal
- platform
- format
- tujuan
- topik
- hook
- caption
- CTA
- jumlah slide
- PDF carousel
- cover
- Slides JSON
- status
- publish mode
- pilar konten
- script lengkap per slide
- URL Slide 1 sampai Slide 7

Status production:
`READY_FOR_MANUAL_UPLOAD`

Tidak ada proses upload otomatis ke Instagram atau TikTok.

## Google Sheets

Apps Script mengelola:
- `Prospects`
- `Content`
- `Content Planning`

Kolom utama Prospects:
- Lead ID
- Tanggal ditemukan
- Nama bisnis
- Email
- Sumber email
- Website
- Social
- Kota
- Kategori
- Bukti publik
- Skor
- Prioritas
- Kebutuhan terdeteksi
- Layanan direkomendasikan
- Pain point
- Hook personal
- Subject
- Body
- Status
- Sent At
- Follow-up 1 At
- Follow-up 2 At
- Follow-up 3 At
- Reply At
- Reply Intent
- Last Reply
- WhatsApp Handoff
- Attempts
- Last Error
- Opt Out

## Automation

Sales discovery tetap menggunakan GitHub Actions terjadwal. Scheduled workflows berjalan dari default branch dan dapat mengalami delay ketika load GitHub tinggi, sehingga sistem tidak menjanjikan ketepatan detik; interval 2 jam tetap menjadi target jadwal.

GitHub Actions menjadi satu-satunya scheduler Sales. Apps Script hanya menjadi execution layer untuk Google Sheets dan Gmail.

## Social platforms

Instagram dan TikTok **tidak lagi memiliki flow otomatis** di project ini.

Tidak ada:
- auto-post
- auto-upload
- auto-DM
- auto-comment reply
- TikTok comment -> DM
- Instagram comment -> DM

Semua aktivitas social posting dilakukan manual oleh tim Content Studio.

## Retired code

Kode dan workflow social/publishing lama sengaja dipensiunkan agar tidak ada jalur ketiga yang berjalan diam-diam.

Production source utama:
- `prospecting_engine.py`
- `content_runner.py`
- `service_catalog.py`
- `apps-script/Code.gs`
- `.github/workflows/daily.yml`
- `.github/workflows/content-daily.yml`
- `.github/workflows/healthcheck.yml`
- `.github/workflows/validate.yml`

Folder/file legacy yang masih tersimpan tetapi tidak aktif boleh diperlakukan sebagai arsip sampai cleanup terakhir dilakukan.

## Security rules

- API keys dan webhook token disimpan di GitHub Secrets / Apps Script Properties.
- Secret tidak ditulis di source code.
- Email hanya diproses dari data publik.
- `UNSUBSCRIBE` menghentikan follow-up.
- Sending memakai lock dan state machine.
- Content Studio tidak mempunyai hak untuk auto-publish social.
