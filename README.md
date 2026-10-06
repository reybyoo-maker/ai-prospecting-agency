# Sonjaya AI Remote Agency

Sistem saat ini dipisah menjadi tiga jalur agar aman:
1. Prospecting AI mencari bisnis + email publik dan mengisi Google Sheets.
2. Email pertama **tidak pernah dikirim otomatis**. Pengiriman dilakukan manual dari kolom **Manual Send** atau menu **Sonjaya -> Kirim Lead Terpilih**. Setelah email pertama terkirim, follow-up dan deteksi reply tetap otomatis.
3. Content engine hanya membuat **content planning + carousel 7 slide**. Tidak ada upload otomatis. File carousel disimpan di repository dan link PDF/cover masuk ke sheet **Content Planning**.

## Sales engine

Discovery berjalan terjadwal melalui GitHub Actions. Kandidat tanpa email publik dibuang.

Gemini membaca evidence publik sebelum memilih satu layanan:
- Virtual Assistant / Admin Remote
- Customer Support / WhatsApp Support
- Lead Generation / Prospecting
- Social Media Management
- Content / Design / Video
- Copywriting
- Research / Data Support
- E-commerce Operations
- Appointment Setting
- Documents / Presentation / Reporting

Field inti prospect diberi fallback yang tidak mengarang fakta ketika AI mengembalikan nilai kosong. Data lama di sheet tidak dihapus atau dipindahkan.

## Manual email sending

Status awal tetap READY atau REVIEW.

Kolom baru:
- Manual Send = checkbox. Centang baris untuk mengirim.
- Send Result = hasil pengiriman.

Menu spreadsheet:
- Sonjaya -> Kirim Lead Terpilih
- Sonjaya -> Pasang Kontrol Manual Send

Email pertama tidak lagi dikirim oleh GitHub workflow. Endpoint lama send_queue tetap ada tetapi menjadi no-op sebagai safety guard.

Setelah manual send berhasil:
SENT -> FOLLOWUP_1 -> FOLLOWUP_2 -> FOLLOWUP_DONE

Jika ada reply, follow-up berhenti. UNSUBSCRIBE menghentikan komunikasi.

## Social comment -> DM

Apps Script sekarang menerima webhook Instagram dan memeriksa keyword yang disimpan di Script Property IG_COMMENT_KEYWORD (default REY MAU).

Jika komentar cocok:
Instagram comment -> private reply DM -> WhatsApp link -> Social Leads

Lead sosial dicatat di sheet baru Social Leads.

Script Properties:
- META_VERIFY_TOKEN
- IG_USER_ID
- IG_ACCESS_TOKEN
- IG_API_VERSION (opsional)
- IG_MESSAGING_HOST (opsional, default https://graph.instagram.com)
- IG_COMMENT_KEYWORD (opsional, default REY MAU)
- WA_NUMBER

Private replies Instagram menggunakan comment ID dan tunduk pada aturan jendela waktu serta batas reply per komentar.

### TikTok

Sistem tidak memalsukan dukungan TikTok comment -> DM. Dokumentasi TikTok saat ini menyediakan akses komentar melalui Research API dan data portability untuk riwayat DM, tetapi tidak menyediakan endpoint publik yang setara untuk mengirim DM berdasarkan komentar. Karena itu jalur TikTok comment -> DM tidak diaktifkan dengan scraping atau endpoint tidak resmi.

## Content planning

Workflow content sekarang:
Gemini -> content planning 7 hari -> 7 carousel x 7 slide -> commit file -> link masuk Google Sheets

Sheet baru:
Content Planning

Kolom penting:
- Tanggal
- Platform
- Tujuan
- Topik
- Hook
- Caption
- CTA
- Slide Count
- Carousel PDF URL
- Carousel Cover URL
- Slides JSON
- Status
- Publish Mode

Tidak ada langkah publish ke Instagram/TikTok di workflow.

Carousel dibuat dengan AI content director yang merancang alur slide, hook, copy, dan visual direction, lalu renderer membuat layout 1080x1350 yang konsisten dan rapi.

Google Gemini memiliki model image-generation khusus untuk aset visual, tetapi pricing saat ini mencantumkan model image-generation tanpa free tier. Pipeline utama karena itu memakai AI text + renderer carousel lokal agar tidak memicu biaya tersembunyi.

## Google Sheets setup

1. Tempel apps-script/Code.gs ke Apps Script yang terikat ke spreadsheet.
2. Jalankan setup() satu kali dan izinkan akses.
3. Pastikan Script Properties berikut sudah ada:
   - WEBHOOK_TOKEN
   - WA_NUMBER
   - META_VERIFY_TOKEN
   - IG_USER_ID
   - IG_ACCESS_TOKEN
   - IG_COMMENT_KEYWORD = REY MAU
4. Karena perubahan Apps Script perlu masuk ke deployment Web App, buat versi deployment baru setelah mengganti Code.gs.
5. Refresh spreadsheet. Menu Sonjaya akan muncul dan checkbox Manual Send tersedia.

## Automation safety

- Initial email: manual.
- Follow-up: otomatis setelah initial email manual terkirim.
- Reply detection: otomatis.
- Instagram keyword DM: otomatis setelah webhook + API permission siap.
- Content planning: otomatis.
- Content upload: nonaktif.

## Limits

Discovery hanya menemukan data publik yang dapat diindeks/diakses sumber discovery. Tidak ada klaim cakupan 100% internet.

GitHub Actions adalah automation terjadwal, bukan proses server yang hidup setiap detik.
