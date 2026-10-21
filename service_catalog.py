SERVICES = [
  {
    "key": "n8n_automation_24_7",
    "name": "Otomasi Workflow n8n 24/7",
    "signals": [
      "n8n", "automation", "otomasi", "workflow", "integrasi aplikasi",
      "integrasi sistem", "pekerjaan berulang", "proses manual", "data entry",
      "lead generation", "follow-up", "whatsapp", "crm", "form",
      "booking", "reservasi", "invoice", "e-commerce",
      "notifikasi", "sinkronisasi data", "operasional"
    ],
    "pitch": "membangun otomasi workflow menggunakan n8n untuk menghubungkan aplikasi dan menjalankan proses berulang secara otomatis; workflow dirancang agar dapat berjalan 24/7 sesuai kebutuhan dan konfigurasi bisnis."
  }
]

def catalog_text():
    return "\n".join(f"- {x['key']}: {x['name']} — {x['pitch']}" for x in SERVICES)
