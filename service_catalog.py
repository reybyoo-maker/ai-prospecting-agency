SERVICES = [
  {"key":"virtual_assistant","name":"Virtual Assistant / Admin Remote","signals":["administrasi","admin","back office","data entry","jadwal","dokumen","virtual assistant"],"pitch":"membantu pekerjaan admin, dokumen, input data, dan follow-up rutin secara remote."},
  {"key":"customer_support","name":"Customer Service & WhatsApp Support","signals":["customer service","chat","whatsapp","cs","customer support","complaint","reservation","booking"],"pitch":"membantu membalas pertanyaan pelanggan, follow-up chat, dan menjaga respons tetap cepat."},
  {"key":"lead_generation","name":"Lead Generation & Prospecting","signals":["sales","lead","prospecting","business development","marketing","promotion","outbound"],"pitch":"membantu mencari dan menyaring prospek baru secara terstruktur."},
  {"key":"social_media","name":"Social Media Management","signals":["instagram","tiktok","social media","content","brand","promo","engagement"],"pitch":"membantu mengelola konten harian, kalender konten, caption, dan engagement."},
  {"key":"content_creation","name":"Content, Design & Video","signals":["content creator","designer","design","video","editor","reels","creative"],"pitch":"membantu membuat materi konten, desain, short video, dan variasi kreatif."},
  {"key":"copywriting","name":"Copywriting & Marketing Content","signals":["copywriter","caption","campaign","marketing communication","sales copy","promotion"],"pitch":"membantu membuat caption, landing-page copy, email, dan materi promosi."},
  {"key":"research_data","name":"Research & Data Support","signals":["research","analyst","data","market research","database","report"],"pitch":"membantu riset pasar, pengumpulan data publik, pembersihan data, dan laporan sederhana."},
  {"key":"ecommerce_support","name":"E-commerce Operations","signals":["ecommerce","marketplace","product listing","catalog","online store","shopee","tokopedia"],"pitch":"membantu upload produk, katalog, deskripsi, pengecekan data, dan pekerjaan operasional marketplace."},
  {"key":"appointment_setting","name":"Appointment Setting","signals":["appointment","booking","reservasi","sales","clinic","property","consultation"],"pitch":"membantu menindaklanjuti calon pelanggan sampai siap diarahkan ke konsultasi atau appointment."},
  {"key":"document_presentation","name":"Documents, Presentation & Reporting","signals":["presentation","powerpoint","report","document","proposal","spreadsheet"],"pitch":"membantu merapikan dokumen, presentasi, spreadsheet, dan laporan bisnis."}
]

def catalog_text():
    return "\\n".join(f"- {x['key']}: {x['name']} — {x['pitch']}" for x in SERVICES)
