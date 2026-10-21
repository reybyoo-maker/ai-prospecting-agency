# AIGROWTH — Automatic Prospecting & Outreach

Repository ini menjalankan discovery bisnis publik di Indonesia dan sejumlah pasar internasional, riset/scoring Gemini, sinkronisasi langsung ke panel Database Scraping AIGROWTH, serta dukungan email dan deteksi balasan. Sistem tidak menggunakan Google Sheets atau Apps Script untuk ingest prospek. Email otomatis tetap nonaktif secara default.

## Alur utama

1. GitHub Actions berjalan otomatis setiap 2 jam.
2. prospecting_engine.py mencari bisnis dari web publik, mengambil bukti relevan, dan memvalidasi alamat email yang dipublikasikan.
3. Gemini memberi skor dan menulis pesan personal. Skor minimal 75 memenuhi syarat untuk email otomatis.
4. Prospek baru dikirim ke endpoint dashboard dengan status queued dan ID stabil.
5. Email yang diterima server SMTP memperbarui record ID yang sama menjadi sent.
6. Inbox IMAP dipindai untuk balasan. Status `replied`, waktu balasan, dan cuplikan balasan dikirim ke dashboard; status `replied` otomatis masuk ke CRM. Permintaan berhenti kontak mengubah status menjadi `blocked` dan menghentikan follow-up.
7. Follow-up pertama dijadwalkan 3 hari setelah email awal, lalu setiap 3 hari (hari ke-6 dan ke-9) sampai maksimal 3 follow-up. Jika penerima membalas atau meminta berhenti, follow-up dihentikan. Pengiriman baru dilakukan hanya jika SMTP dan IMAP siap agar balasan bisa dilacak ke dashboard.

## Gaya outreach dan pasar internasional

- Email dibuat singkat, hangat, profesional, dan disesuaikan dengan masalah yang benar-benar didukung bukti publik.
- Prospek Indonesia menggunakan Bahasa Indonesia; prospek internasional menggunakan Bahasa Inggris.
- Discovery mengalokasikan query untuk Indonesia dan sejumlah kota internasional secara bergantian.
- Pesan menawarkan audit workflow dan konsultasi awal gratis tanpa komitmen.
- Penghematan biaya dijelaskan secara wajar untuk pekerjaan repetitif; sistem tidak menjanjikan otomasi selalu lebih murah atau menggantikan semua karyawan.
- Footer memakai https://aigrowth.my.id, Instagram @ai.growth.agency, dan tanda tangan Rey — Founder, AI Growth Agency.

## Kontrak dashboard

Endpoint:
https://aigrowth-owner-dashboard.reybyoo.workers.dev/api/ingest/scrape

Header:
Authorization: Bearer INGEST_TOKEN

Setiap record mengikuti kontrak Database Scraping:
id, platform, name, handle, contact, phone, url, category, city, campaign, message_preview, status, sent_at, replied_at, error.

Status sistem:
queued, sent, replied, failed, blocked.

Status delivered dan read tidak dibuat-buat. Status itu hanya boleh ditulis jika provider pengiriman benar-benar mengonfirmasinya. SMTP sukses dicatat sebagai sent.

ID dibentuk dari HMAC email yang dikunci oleh INGEST_TOKEN: stabil antar-run, tetapi tidak menampilkan alamat email dalam ID.

## GitHub Secrets yang diperlukan

Buka Repository → Settings → Secrets and variables → Actions.

Untuk scraping dan sinkronisasi:
- GEMINI_API_KEY
- INGEST_TOKEN — Bearer token yang cocok dengan dashboard

Untuk email otomatis:
- SMTP_HOST
- SMTP_PORT — 465 untuk SSL atau 587 untuk STARTTLS
- SMTP_USERNAME
- SMTP_PASSWORD
- SMTP_FROM
- SMTP_REPLY_TO (opsional, default mengikuti SMTP_FROM)

Untuk deteksi balasan dan follow-up:
- IMAP_HOST — default imap.gmail.com
- IMAP_PORT — default 993
- IMAP_USERNAME (opsional, default mengikuti SMTP_USERNAME)
- IMAP_PASSWORD (opsional, default mengikuti SMTP_PASSWORD)

Untuk Gmail, gunakan App Password dan pastikan IMAP aktif. Jangan menaruh token, API key, atau password di source code.

## Pengaktifan pengiriman

Pengiriman otomatis membutuhkan Actions Variable `ENABLE_AUTO_EMAIL=true` serta secrets SMTP dan IMAP yang valid. Sistem fail-closed: meskipun variabel aktif, tidak ada email yang dikirim bila konfigurasi SMTP/IMAP belum lengkap atau pemindaian inbox gagal. Balasan masuk ke dashboard/CRM saat thread email dapat dicocokkan.

Scraping dan sinkronisasi ke dashboard tetap membutuhkan GEMINI_API_KEY dan INGEST_TOKEN.

## Batas dan keamanan

- Maksimal 20 email otomatis per hari kalender WIB, termasuk follow-up.
- Maksimal tiga percobaan pengiriman per record.
- Maksimal tiga follow-up per penerima, pada hari ke-3, ke-6, dan ke-9.
- Pengiriman ditahan sampai SMTP dan IMAP tersedia; hal ini memastikan respons bisa dibaca dan disinkronkan ke dashboard.
- Batch antrean harus diterima dashboard sebelum sistem mengirim email.
- Balasan dan opt-out menghentikan follow-up.
- State serta counter tersimpan sebagai ciphertext pada runtime/prospecting-state.enc. File tersebut tidak menyimpan data kontak dalam bentuk teks biasa.
- INGEST_TOKEN digunakan untuk derivasi kunci enkripsi state. Jangan mengganti token tanpa migrasi state; jika dekripsi gagal, pengiriman dihentikan agar tidak menggandakan email.
- Panel Content Studio tetap terpisah. Asetnya disimpan di GitHub untuk unggah manual dan tidak disinkronkan ke database eksternal.

## Menjalankan manual

Buka Actions → AIGROWTH Automatic Scraping & Outreach → Run workflow. Status sinkronisasi terlihat di log GitHub Actions. Pengujian POST yang nyata membutuhkan INGEST_TOKEN yang cocok dengan dashboard.
