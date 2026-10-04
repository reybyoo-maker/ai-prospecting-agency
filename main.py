import os
from datetime import datetime, timezone, timedelta

import requests

from prospector import collect_prospects
from gemini_scorer import score_batch

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SHEET_WEBHOOK_URL = os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]

WIB = timezone(timedelta(hours=7))

MAX_CANDIDATES = 100
AI_BATCH_SIZE = 40

def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]

def send_to_sheet(rows):
    r = requests.post(
        SHEET_WEBHOOK_URL,
        json={
            "token": WEBHOOK_TOKEN,
            "rows": rows,
        },
        timeout=90,
    )
    r.raise_for_status()
    return r.json()

def main():
    print("=== AI PROSPECTING AGENCY — INDONESIA ===")
    print("Search layer: TinyFish")
    print("AI layer: Gemini 3.6 Flash")

    prospects = collect_prospects(
        queries_per_run=8,
        max_per_query=10,
    )

    prospects = prospects[:MAX_CANDIDATES]

    print(
        f"Kandidat yang akan dinilai Gemini: "
        f"{len(prospects)}"
    )

    rows = []

    for batch_no, batch in enumerate(
        chunks(prospects, AI_BATCH_SIZE),
        start=1,
    ):
        print(
            f"Gemini scoring batch {batch_no} "
            f"({len(batch)} kandidat)..."
        )

        results = score_batch(
            GEMINI_API_KEY,
            batch,
        )

        by_id = {
            int(x["id"]): x
            for x in results
        }

        for idx, lead in enumerate(batch):
            ai = by_id.get(idx, {})

            score = int(ai.get("skor", 0) or 0)

            if score >= 80:
                priority = "A"
            elif score >= 65:
                priority = "B"
            else:
                priority = "C"

            rows.append({
                "tanggal_ditemukan": datetime.now(WIB).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "nama_bisnis": ai.get(
                    "nama_bisnis",
                    lead.get("search_title", lead.get("username", "")),
                ),
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

    rows.sort(
        key=lambda x: x.get("skor", 0),
        reverse=True,
    )

    print(
        f"Hasil AI: {len(rows)} baris. "
        f"Mengirim ke Google Sheet..."
    )

    if rows:
        result = send_to_sheet(rows)
        print("GOOGLE SHEET:", result)

if __name__ == "__main__":
    main()
