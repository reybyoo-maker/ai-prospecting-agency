import os
from datetime import datetime, timezone, timedelta

import requests

from email_sender import send_pending
from gemini_scorer import score_batch
from prospector import collect_prospects

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SHEET_WEBHOOK_URL = os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]

WIB = timezone(timedelta(hours=7))
MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES", "80"))
AI_BATCH_SIZE = int(os.getenv("AI_BATCH_SIZE", "5"))
AUTO_SEND_MIN_SCORE = int(os.getenv("AUTO_SEND_MIN_SCORE", "75"))

def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]

def fallback(lead, idx):
    return {
        "id": idx,
        "nama_bisnis": lead.get("search_title", "")[:100],
        "kota": "",
        "kategori": "",
        "skor": 0,
        "alasan": "AI scoring gagal; prospek ditahan.",
        "pain_point": "",
    }

def build_email(lead, ai):
    business = (ai.get("nama_bisnis") or lead.get("search_title") or "bisnis Anda").strip()
    category = (ai.get("kategori") or "bisnis").strip()
    city = (ai.get("kota") or "").strip()
    reason = (ai.get("alasan") or "Saya melihat ada peluang untuk memperkuat alur mendapatkan pelanggan.").strip()
    location = f" di {city}" if city else ""

    subject = f"Ide menambah lead{location} untuk {business}"
    body = (
        f"Halo tim {business},\n\n"
        f"Saya Rey dari Sonjaya AI Sales Engine. Saya menemukan {business} "
        f"dari informasi publik dan melihat peluang yang cukup menarik untuk "
        f"{category}{location}.\n\n"
        f"{reason}\n\n"
        f"Kami membantu bisnis membuat sistem AI yang terus mencari calon customer, "
        f"menyaring prospek yang paling potensial, lalu membantu mengarahkan mereka "
        f"ke proses konsultasi atau appointment tanpa seluruh proses dilakukan manual.\n\n"
        f"Saya tidak ingin mengirim presentasi panjang. Boleh saya kirim contoh "
        f"alur yang bisa diterapkan untuk {business}, lalu kita lihat apakah masuk akal?\n\n"
        f"Kalau berkenan, cukup balas email ini. Kalau email ini tidak relevan, "
        f"cukup balas UNSUBSCRIBE.\n\n"
        f"Salam,\n"
        f"Rey\n"
        f"Sonjaya AI Sales Engine"
    )
    return subject, body

def send_to_sheet(rows):
    response = requests.post(
        SHEET_WEBHOOK_URL,
        json={"token": WEBHOOK_TOKEN, "action": "ingest", "rows": rows},
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "Google Sheets ingest gagal."))
    return data

def main():
    print("=== SONJAYA AI SALES ENGINE ===")
    print("Model: AI Lead Generation + Appointment Setting")
    print("Mandatory field: public business email")

    prospects = collect_prospects(
        queries_per_run=int(os.getenv("QUERIES_PER_RUN", "8")),
        max_per_query=int(os.getenv("MAX_PER_QUERY", "12")),
    )[:MAX_CANDIDATES]

    print(f"Prospek ber-email: {len(prospects)}")
    if not prospects:
        print("Tidak ada prospect baru dengan email publik.")
        try:
            send_pending()
        except Exception as exc:
            print("Email sender:", exc)
        return

    rows = []

    for batch_no, batch in enumerate(
        chunks(prospects, AI_BATCH_SIZE),
        start=1,
    ):
        print(f"Gemini batch {batch_no} ({len(batch)} prospect)...")
        try:
            results = score_batch(GEMINI_API_KEY, batch)
            by_id = {int(item["id"]): item for item in results}

            for idx, lead in enumerate(batch):
                ai = by_id.get(idx) or fallback(lead, idx)
                score = int(ai.get("skor", 0) or 0)
                subject, body = build_email(lead, ai)

                status = (
                    "READY"
                    if score >= AUTO_SEND_MIN_SCORE and body
                    else "REVIEW"
                )

                rows.append({
                    "lead_id": "",
                    "tanggal_ditemukan": datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"),
                    "nama_bisnis": ai.get("nama_bisnis") or lead.get("search_title", "")[:100],
                    "recipient_email": lead.get("recipient_email", ""),
                    "email_source_url": lead.get("email_source_url", ""),
                    "website_url": lead.get("website_url", ""),
                    "social_url": lead.get("social_url", ""),
                    "kota": ai.get("kota", ""),
                    "kategori": ai.get("kategori", ""),
                    "bukti_publik": lead.get("public_evidence", ""),
                    "skor": score,
                    "alasan": ai.get("alasan", ""),
                    "pain_point": ai.get("pain_point", ""),
                    "subject": subject,
                    "body": body,
                    "status": status,
                    "catatan": "email publik ditemukan dari web",
                })
        except Exception as exc:
            print(f"Batch {batch_no} gagal: {exc}")
            for idx, lead in enumerate(batch):
                ai = fallback(lead, idx)
                subject, body = build_email(lead, ai)
                rows.append({
                    "lead_id": "",
                    "tanggal_ditemukan": datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"),
                    "nama_bisnis": ai["nama_bisnis"],
                    "recipient_email": lead.get("recipient_email", ""),
                    "email_source_url": lead.get("email_source_url", ""),
                    "website_url": lead.get("website_url", ""),
                    "social_url": lead.get("social_url", ""),
                    "kota": "",
                    "kategori": "",
                    "bukti_publik": lead.get("public_evidence", ""),
                    "skor": 0,
                    "alasan": ai["alasan"],
                    "pain_point": "",
                    "subject": subject,
                    "body": body,
                    "status": "REVIEW",
                    "catatan": "AI scoring gagal",
                })

    rows.sort(key=lambda x: int(x.get("skor", 0) or 0), reverse=True)
    result = send_to_sheet(rows)
    print("Sheets:", result)

    try:
        sent_result = send_pending()
        print("Email sender:", sent_result)
    except Exception as exc:
        print("Email sender gagal:", exc)

if __name__ == "__main__":
    main()
