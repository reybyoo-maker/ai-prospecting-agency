# Sonjaya AI Remote Agency

V2 adalah mesin remote-service sales dan content automation:
Discovery bisnis -> email publik -> AI membaca kebutuhan -> pilih satu layanan -> personalized email -> Google Sheets -> Gmail -> follow-up otomatis -> deteksi reply -> WhatsApp handoff.

## Sales engine

Discovery berjalan setiap 2 jam melalui GitHub Actions. Mesin mencari banyak kombinasi kota/niche/query dan menerima hasil dari website serta profil sosial publik hanya ketika email bisnis terlihat secara publik. Kandidat tanpa email publik dibuang.

Gemini membaca evidence publik sebelum memilih layanan:
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

Email tidak menawarkan seluruh katalog sekaligus. AI memilih satu layanan yang paling relevan dengan bukti.

## Email sequence

Status utama:
READY -> SENT -> FOLLOWUP_1 -> FOLLOWUP_2 -> FOLLOWUP_DONE

Follow-up default:
- +2 hari
- +5 hari
- +9 hari

Begitu ada reply, follow-up berhenti. UNSUBSCRIBE menandai OPTOUT dan menghentikan komunikasi.

Reply yang terdeteksi diarahkan ke WhatsApp menggunakan nomor yang disimpan di Script Property WA_NUMBER. Jika nomor belum diatur, balasan tetap dicatat tetapi tidak membuat link WhatsApp.

Default outbound limit adalah 20 recipient per hari dan mesin menghormati quota MailApp.

## Google Sheets

Apps Script membuat:
- Prospects: semua prospect, evidence, score, kebutuhan, service, email, status, reply, follow-up, opt-out.
- Content: kalender konten dan status publish.

## Setup Google sekali

1. Buka Google Sheet.
2. Extensions -> Apps Script.
3. Tempel apps-script/Code.gs.
4. Jalankan setup() satu kali dan berikan izin Gmail/Spreadsheet.
5. Script Properties:
   - WEBHOOK_TOKEN = token acak.
   - WA_NUMBER = nomor WhatsApp format internasional tanpa +.
6. Deploy -> New deployment -> Web app.
7. Execute as: Me.
8. Beri akses sesuai kebutuhan endpoint. URL Web App disimpan sebagai GitHub Secret SHEET_WEBHOOK_URL.
9. GitHub Secrets minimum:
   - GEMINI_API_KEY
   - SHEET_WEBHOOK_URL
   - WEBHOOK_TOKEN

V2 tidak membutuhkan GMAIL_APP_PASSWORD atau TINYFISH_API_KEY.

## Social content

content_runner.py membuat kalender 7 hari Instagram + TikTok dan dua asset PNG per hari. Asset disimpan ke social_assets/, lalu workflow meng-commit asset agar URL raw GitHub dapat menjadi media source publik.

social_dispatch.py memanggil Apps Script untuk publish:
- Instagram photo post menggunakan token/API account Instagram professional.
- TikTok photo Direct Post menggunakan token OAuth.

## Social credentials

Script Properties untuk Instagram:
- IG_USER_ID
- IG_ACCESS_TOKEN
- optional IG_API_VERSION (default v26.0)

Script Properties untuk TikTok:
- TIKTOK_CLIENT_KEY
- TIKTOK_CLIENT_SECRET
- TIKTOK_ACCESS_TOKEN
- TIKTOK_REFRESH_TOKEN

TikTok access token harus dapat direfresh. Adapter menyimpan access token dan refresh token baru yang dikembalikan TikTok.

Jika credential sosial belum ada, workflow tetap membuat content + assets dan tidak gagal.

## Important platform constraints

Instagram publishing hanya tersedia untuk akun profesional dan membutuhkan izin API yang sesuai.

TikTok Direct Post membutuhkan TikTok developer app, scope publish, user authorization, dan approval/audit sesuai keadaan app. Unaudited clients can be restricted to private visibility.

DM automation tidak dipaksakan memakai password/scraping. Untuk inbox/DM penuh dibutuhkan API permissions, webhook/authorization, dan implementasi kanal resmi yang sesuai.

## Discovery limits

Tidak ada crawler yang jujur dapat menjamin 100% internet. Sistem hanya menemukan bisnis yang memiliki jejak publik dan dapat diakses/index oleh sumber discovery.

Email wajib berasal dari informasi publik. Tidak menggunakan database curian, login-only data, atau credential pihak lain.

## Automation limits

GitHub Actions menjalankan workflow terjadwal; "24/7" berarti pekerjaan otomatis berulang, bukan proses server yang hidup setiap detik. Scheduled workflows pada repository publik dapat dinonaktifkan GitHub setelah 60 hari tanpa aktivitas repository, jadi repository perlu tetap aktif.

## Validation

validate.yml menjalankan:
- Python syntax validation.
- JavaScript syntax validation untuk apps-script/Code.gs.
