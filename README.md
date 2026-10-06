# Sonjaya AI Sales Engine

Satu mesin otomatis untuk mencari calon klien bisnis Indonesia, wajib menemukan email publik, menganalisis kecocokan dengan AI, membuat email personal, lalu mengirim outreach secara otomatis setiap hari.

Model bisnis dikunci:
AI Lead Generation + Appointment Setting.

Alur:
Discovery -> Email Finder -> AI Scoring -> Personalized Email -> Google Sheets -> Gmail Sender.

Aturan inti:
1. Prospect tanpa email publik dibuang dan tidak pernah masuk antrean kirim.
2. Email hanya diambil dari informasi publik pada hasil pencarian atau halaman web yang dapat diakses umum.
3. AI tidak boleh mengarang fakta bisnis.
4. Hanya skor >= 75 yang berstatus READY dan dapat dikirim otomatis.
5. Daily send limit default 20 email/hari.
6. Ada jeda acak 20-45 detik antar email.
7. Email menyertakan instruksi opt-out: balas UNSUBSCRIBE.
8. Jangan memakai daftar email curian, data pribadi sensitif, atau alamat yang diperoleh dari akses login.

Komponen:
- TinyFish: web/business discovery.
- Gemini: scoring dan analisis prospek.
- Google Apps Script + Google Sheets: database dan send queue.
- Gmail SMTP: pengiriman email.
- GitHub Actions: scheduler 4 kali sehari.

Google Sheet:
Buat spreadsheet lalu buka Extensions -> Apps Script.
Salin isi apps-script/Code.gs.
Set Script Property:
WEBHOOK_TOKEN = token acak yang sama dengan GitHub Secret WEBHOOK_TOKEN.
Deploy sebagai Web app:
Execute as: Me.
Who has access: Anyone.
Salin URL Web App ke GitHub Secret SHEET_WEBHOOK_URL.
Jalankan fungsi setup sekali dari Apps Script.

GitHub Secrets wajib:
GEMINI_API_KEY
TINYFISH_API_KEY
SHEET_WEBHOOK_URL
WEBHOOK_TOKEN
GMAIL_ADDRESS
GMAIL_APP_PASSWORD
AGENCY_NAME

Gmail:
Gunakan akun Gmail khusus untuk outreach dan App Password, bukan password Gmail biasa. Aktifkan 2-Step Verification pada akun tersebut sebelum membuat App Password.

Pengiriman:
GitHub Actions menjalankan engine pada 08:00, 14:00, 20:00, dan 02:00 WIB.
Setiap run mencari prospect baru ber-email dan kemudian mengambil antrean READY.
Daily send limit dihitung dari Google Sheet, sehingga total tidak melebihi 20 email/hari secara default.

Status Sheet:
READY = lolos AI dan menunggu pengiriman otomatis
SENT = sudah dikirim
ERROR = gagal kirim dan akan dicoba lagi sampai 3 kali
FAILED = gagal 3 kali
REVIEW = belum lolos syarat kirim otomatis
OPTOUT = tidak boleh dihubungi lagi

Catatan:
Cold outreach harus tetap relevan, sopan, dan mematuhi aturan anti-spam serta kebijakan penyedia email. Sistem ini bukan jaminan inbox placement atau hasil penjualan.
