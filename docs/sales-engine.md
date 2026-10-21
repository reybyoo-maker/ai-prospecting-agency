# Sales Engine — Dashboard Scraping

## Alur produksi

1. GitHub Actions berjalan setiap 2 jam.
2. prospecting_engine.py menemukan bisnis dari web publik, memvalidasi email publik, memperkaya evidence, lalu memberi skor dengan Gemini.
3. Prospek baru di-upsert melalui POST /api/ingest/scrape pada AIGROWTH Owner Dashboard.
4. Sistem baru mengirim email setelah record queued berhasil disinkronkan. Status setelah SMTP menerima pesan berubah menjadi sent.
5. Inbox IMAP dipindai sebelum follow-up. Balasan memperbarui record ID yang sama menjadi replied, sehingga dashboard membuat lead CRM. Balasan opt-out menjadi blocked.
6. Follow-up dijadwalkan sekitar hari ke-2, ke-5, dan ke-9. Jika pemeriksaan inbox gagal, follow-up dilewati.
7. Status yang digunakan: queued, sent, replied, failed, blocked. Status delivered atau read hanya dicatat jika benar-benar dikonfirmasi provider.

## Pengendalian

- ID HMAC email stabil antar-run tanpa mengekspos alamat email di ID.
- Batch scraping harus diterima dashboard sebelum email dikirim.
- Maksimal 20 pengiriman otomatis per hari WIB, termasuk follow-up.
- Maksimal tiga percobaan per record.
- Balasan atau opt-out menghentikan follow-up.
- SMTP secrets diperlukan untuk mengirim email; IMAP diperlukan untuk deteksi balasan dan follow-up.
- Counter dan riwayat tersimpan terenkripsi di runtime/prospecting-state.enc. Jangan mengganti INGEST_TOKEN saat state masih dipakai.

## Batas integrasi

Repository ini mengirim data ke endpoint dashboard yang diberikan. Source code dashboard tidak berada di repository ini, jadi perubahan frontend/backend dashboard tidak dilakukan di sini.
