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

## Social automation

Apps Script menerima webhook Instagram dan menangani dua jalur:
1. Komentar dengan keyword pada `IG_COMMENT_KEYWORD` -> private reply ke commenter -> public comment reply -> pencatatan di **Social Leads**.
2. Inbound Instagram DM -> auto-reply text -> pencatatan di **Social Leads**.

Script Properties untuk Instagram:
- `META_VERIFY_TOKEN`
- `WEBHOOK_TOKEN`
- `IG_USER_ID`
- `IG_ACCESS_TOKEN`
- `IG_API_VERSION` (default `v26.0`)
- `IG_MESSAGING_HOST` (default `https://graph.instagram.com`)
- `IG_COMMENT_KEYWORD` (default `REY MAU`)
- `IG_PUBLIC_COMMENT_REPLY`
- `WA_NUMBER`

Aksi webhook `social_health` melakukan pemeriksaan non-publish ke Instagram `/me` dan TikTok creator info, tanpa mengirim pesan atau posting.

### TikTok

TikTok photo Direct Post didukung oleh Content Posting API. Foto dapat dikirim dari URL publik yang sudah diverifikasi oleh aplikasi, dan Direct Post memakai scope `video.publish`. Konten dari client yang belum diaudit dibatasi ke private viewing sampai proses audit selesai.

Comment -> DM TikTok tidak diaktifkan menggunakan scraping atau endpoint tidak resmi.

## Content publishing

Workflow harian menghasilkan 7-day plan + carousel 7 slide, menyimpan asset ke GitHub, lalu otomatis mem-publish **Instagram** untuk konten hari berjalan.

Alur:
`Gemini -> 7-day content plan -> 7 carousel x 7 slide -> commit assets -> Google Sheets -> Instagram publish`

TikTok memiliki workflow `TikTok Publish (Manual Approval)` terpisah. Parameter tanggal approval sekarang dihormati oleh publisher, sehingga workflow dapat memilih tanggal yang diberikan.

Publisher melakukan retry dan mengecek seluruh asset URL terlebih dahulu sebelum meminta platform memproses konten.

## Google Sheets setup

1. Tempel `apps-script/Code.gs` ke Apps Script yang terikat ke spreadsheet.
2. Jalankan `setup()` satu kali dan izinkan akses.
3. Pastikan Script Properties utama sudah ada.
4. Deploy Apps Script sebagai Web App dan buat deployment baru setelah mengganti `Code.gs`.
5. Jalankan endpoint healthcheck melalui workflow GitHub untuk memverifikasi webhook, Apps Script version, Instagram, TikTok (jika dikonfigurasi), dan Gemini.

Sheet yang dibuat/dikelola oleh Apps Script:
- `Prospects`
- `Content`
- `Content Planning`
- `Social Leads`

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
