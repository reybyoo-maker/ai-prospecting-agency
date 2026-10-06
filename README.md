# Sonjaya AI Remote Agency

Mesin utama sekarang adalah V2: discovery bisnis -> email publik -> AI membaca kebutuhan -> pilih satu layanan paling relevan -> personalisasi email -> Google Sheets -> Gmail otomatis -> monitor reply -> handoff WhatsApp.

## V2 tanpa TinyFish dan tanpa SMTP

Discovery V2 menggunakan DDGS + halaman web publik, jadi tidak membutuhkan API TinyFish. Gemini API dipakai untuk research/scoring/copy. Pengiriman Gmail dan pembacaan reply dilakukan oleh Google Apps Script menggunakan akun Google yang mengotorisasi script.

Gemini menyediakan Free Tier untuk model yang memenuhi syarat, tetapi tetap memiliki quota/rate limit. Gmail juga mempunyai batas pengiriman harian dan batas penggunaan; V2 sengaja memakai default 20 email/hari.

## Yang dilakukan otomatis

Setiap 2 jam GitHub Actions:
1. mencari bisnis dari banyak kota dan kategori;
2. membuka halaman publik untuk mencari email bisnis;
3. membuang kandidat yang tidak mempunyai email publik;
4. mengirim evidence ke Gemini;
5. mendeteksi kebutuhan yang terlihat dan memilih satu layanan;
6. membuat subject + body personal;
7. memasukkan semuanya ke Google Sheets;
8. meminta Apps Script mengirim antrean READY;
9. meminta Apps Script memeriksa reply.

Saat ada reply, Apps Script menandai REPLIED/WA_HANDOFF dan mengirim balasan pada thread yang berisi link WhatsApp. Email yang meminta UNSUBSCRIBE langsung ditandai OPTOUT.

## Layanan yang bisa dijual

Virtual Assistant/Admin Remote, Customer Support/WhatsApp, Lead Generation, Social Media Management, Content/Design/Video, Copywriting, Research/Data Support, E-commerce Operations, Appointment Setting, dan Documents/Presentation/Reporting.

Email tidak mengatakan "kami mengerjakan semua". AI memilih satu layanan berdasarkan bukti supaya outreach tetap relevan.

## Google Sheet

Sheet Prospects dibuat otomatis oleh Code.gs dengan kolom:
Lead ID, tanggal, bisnis, email, sumber email, website, social, kota, kategori, bukti publik, skor, prioritas, kebutuhan terdeteksi, layanan direkomendasikan, pain point, hook, subject, body, status, Sent At, Reply At, Reply Intent, Last Reply, WhatsApp Handoff, Attempts, Last Error, Opt Out, catatan.

Sheet Content disiapkan untuk kalender konten Instagram/TikTok.

## Social media

social_content.py menghasilkan ide/caption harian untuk Instagram dan TikTok. Metricool yang sudah terhubung bisa membantu penjadwalan dan auto-publish Instagram pada akun business/creator. Namun API Metricool saat ini hanya tersedia pada paket Advanced/Custom, bukan Free/Starter, sehingga integrasi API untuk auto-publish tidak bisa disebut 100% gratis.

Karena targetmu gratis, V2 tidak memasukkan biaya API Metricool sebagai dependency. Content generator tetap otomatis; publishing dapat memakai scheduler gratis yang tersedia pada akunmu. DM automation penuh tidak dipaksakan lewat password/scraping karena membutuhkan akses platform yang sesuai.

## Setup satu kali yang tetap membutuhkan otorisasi

Agar sistem dapat menyentuh akunmu, kamu tetap harus memberikan otorisasi akun.

1. Buka Google Sheet.
2. Extensions -> Apps Script.
3. Ganti Code.gs dengan apps-script/Code.gs di repo ini.
4. Jalankan setup() satu kali dan izinkan Gmail + Spreadsheet.
5. Set Script Property WEBHOOK_TOKEN dengan token acak.
6. Set Script Property WA_NUMBER dengan nomor WhatsApp bisnis yang akan menerima handoff, format internasional tanpa tanda +.
7. Deploy sebagai Web App dan salin URL-nya.
8. Di GitHub Secrets, isi GEMINI_API_KEY, SHEET_WEBHOOK_URL, WEBHOOK_TOKEN.
9. Aktifkan GitHub Actions.

V2 tidak membutuhkan GMAIL_APP_PASSWORD atau TINYFISH_API_KEY.

## Batasan penting

"Semua perusahaan di internet" tidak dapat dijamin. Mesin hanya dapat menemukan bisnis yang punya jejak publik yang dapat diindeks/dibuka. Email yang ditemukan harus publik; tidak memakai database curian atau data dari login.

20 email/hari adalah default yang sengaja konservatif. Quota Gmail dan Gemini dapat berubah atau habis.
