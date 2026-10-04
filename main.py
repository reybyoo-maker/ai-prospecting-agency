import os
from datetime import datetime, timezone, timedelta

import requests

from prospector import collect_prospects
from gemini_scorer import score_batch

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SHEET_WEBHOOK_URL = os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]

WIB = timezone(timedelta(hours=7))

def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]

def send_to_sheet(rows):
    response = requests.post(
        SHEET_WEBHOOK_URL,
        json={
            "token": WEBHOOK_TOKEN,
            "rows": rows
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()

def main():
    print("=== AI PROSPECTING AGENCY ===")
    print("Mencari prospek publik...")

    prospects = collect_prospects(max_per_query=5)

    # Batas 60 prospek/run agar tetap hemat API.
    prospects = prospects[:60]

    print(f"Prospek yang akan dinilai AI: {len(prospects)}")

    scored_rows = []

    for batch_no, batch in enumerate(chunks(prospects, 10), start=1):
        print(f"Menilai batch AI {batch_no}...")

        results = score_batch(GEMINI_API_KEY, batch)
        results_by_id = {int(item["id"]): item for item in results}

        for idx, lead in enumerate(batch):
            ai = results_by_id.get(idx, {})

            score = int(ai.get("skor", 0) or 0)

            if score >= 80:
                priority = "A"
            elif score >= 65:
                priority = "B"
            else:
                priority = "C"

            scored_rows.append({
                "tanggal_ditemukan": datetime.now(WIB).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "nama_bisnis": ai.get("nama_bisnis", ""),
                "instagram": lead.get("username", ""),
                "url_instagram": lead.get("instagram_url", ""),
                "kota": ai.get("kota", ""),
                "kategori": ai.get("kategori", ""),
                "bukti_publik": lead.get("public_evidence", ""),
                "skor": score,
                "alasan": ai.get("alasan", ""),
                "prioritas": priority,
                "status": "BELUM DI-DM",
                "catatan_dm": "",
            })

    scored_rows.sort(
        key=lambda x: x.get("skor", 0),
        reverse=True
    )

    print(f"Prospek siap dikirim ke Google Sheet: {len(scored_rows)}")

    if scored_rows:
        result = send_to_sheet(scored_rows)
        print("HASIL GOOGLE SHEET:", result)

if __name__ == "__main__":
    main()
