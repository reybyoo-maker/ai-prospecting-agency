# AIGROWTH — Automatic Prospecting & Outreach

Repository ini menjalankan discovery dari sumber web publik untuk bisnis dan profesional independen di Indonesia serta pasar internasional, riset/scoring Gemini, sinkronisasi langsung ke panel Database Scraping AIGROWTH, serta dukungan email dan deteksi balasan. Sistem tidak menggunakan Google Sheets atau Apps Script untuk ingest prospek. Email otomatis tetap nonaktif secara default.

## Alur utama

1. GitHub Actions berjalan otomatis setiap 2 jam.
2. prospecting_engine.py mencari bisnis dan profesional independen dari web publik, mengambil bukti relevan, dan mengutamakan alamat email yang dipublikasikan dalam konteks kerja/profesional.
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


## Discovery multi-mesin dan profesional independen

Pencarian memprioritaskan kebutuhan kerja yang dapat dilayani AIGROWTH, bukan hanya nama perusahaan. Secara default, sekitar 30% kueri dialokasikan untuk profesional independen seperti freelancer, konsultan, solo founder, coach, dan content creator yang memiliki sinyal kebutuhan kerja yang dipublikasikan secara terbuka. Sisanya mencari bisnis dan organisasi. Rasio dapat diubah lewat `INDIVIDUAL_QUERY_RATIO` (0 sampai 0.5).

Mesin dan fallback yang tersedia:
- DDGS mencoba beberapa backend bergilir: Google, Brave, Bing, dan DuckDuckGo.
- Jika hasil sedikit atau backend gagal, fallback HTML mencoba Google, Bing, DuckDuckGo, Brave Search, Yandex, Startpage, Ecosia, Qwant, dan Swisscows. Sistem menggabungkan hasil unik lintas sumber dan mencatat status HTTP serta jumlah hasil per provider.
- SearXNG dapat ditambahkan melalui `SEARXNG_BASE_URLS`, berupa daftar URL instance yang dipisahkan koma. Format JSON bergantung pada konfigurasi instance; sistem mencoba fallback HTML bila JSON tidak tersedia.
- Brave Search API dapat digunakan dengan `BRAVE_SEARCH_API_KEY`. Tanpa key, sistem tetap menggunakan fallback pencarian publik.
- Kueri profesional mencari sinyal kerja publik seperti permintaan bantuan workflow, administrasi, lead follow-up, onboarding klien, jadwal/booking, dan layanan pelanggan. Pencarian dengan operator seperti `site:` digunakan untuk memfokuskan hasil ke sumber profesional tertentu.

Batas privasi: sistem hanya menggunakan bukti yang tersedia publik dan relevan dengan kegiatan bisnis/kerja. Sistem tidak melakukan pemeriksaan akun privat, enumerasi pendaftaran akun email, reverse lookup nomor telepon pribadi, atau profiling atribut sensitif. Profil sosial hanya dicari sebagai jejak profesional publik; halaman media sosial tidak di-crawl untuk mengekstrak kontak tersembunyi.

### Pengayaan profil opsional (Apify)

Pengayaan profil sosial dengan Apify tersedia tetapi **nonaktif secara default** karena dapat memakai kredit berbayar. Untuk mengaktifkannya secara sengaja, atur GitHub Actions Secrets `APIFY_API_TOKEN`, lalu variable `APIFY_ENRICHMENT_ENABLED=true`. Actor default adalah `tri_angle~social-media-finder`; ganti `APIFY_ACTOR_ID` bila menggunakan actor lain yang input/output-nya kompatibel. `APIFY_MAX_NAMES_PER_RUN` membatasi jumlah nama yang dikirim. Integrasi ini hanya mengambil URL profil sosial yang dapat dicocokkan dengan nama prospek publik; tidak mengimpor telepon pribadi atau email privat.

Pengaturan pencarian ada di `.env.example`. Batas `DIRECT_SEARCH_PROVIDERS_PER_QUERY` dan timeout menjaga siklus agar tidak terus menunggu mesin yang sedang bermasalah. Provider bisa menolak permintaan, menerapkan rate limit, menampilkan CAPTCHA, atau mengubah markup; karena itu hasil setiap provider dicatat dan hasil penemuan tidak dijamin pada setiap siklus.

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
