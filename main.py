import os
import json
from datetime import datetime, timezone, timedelta

import requests

from prospector import collect_prospects
from gemini_scorer import score_batch

SHEET_WEBHOOK_URL = os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

def chunks(items, n):
    for i in range(0, len(items), n):
        yield items[i:i+n]

def post_rows(rows):
    body = {
        "token": WEBHOOK_TOKEN,
        "rows": rows
    }
    r = requests.post(SHEET_WEBHOOK_URL, json=body, timeout=60)
    r.raise_for_status()
    return r.json()

def main():
    print("Mencari prospek publik...")
    prospects = collect_prospects(max_per_query=5)
    print(f"Profil unik ditemukan: {len(prospects)}")

    # AI dipanggil dalam batch untuk menghemat quota.
    scored = []
    for batch in chunks(prospects[:60], 10):
        try:
            results = score_batch(GEMINI_API_KEY, batch)
            by_id = {int(x["id"]): x for x in results}
            for idx, lead in enumerate(batch):
                s = by_id.get(idx, {})
                scored.append({
                    "tanggal_ditemukan": (
                        datetime.now(timezone(timedelta(hours=7)))
                        .strftime("%Y-%m-%d %H:%M:%S")
                    ),
                    "nama_bisnis": s.get("nama_bisnis", ""),
                    "instagram": lead.get("username", ""),
                    "url_instagram": lead.get("instagram_url", ""),
                    "kota": s.get("kota", ""),
                    "kategori": s.get("kategori", ""),
                    "bukti_publik": lead.get("public_evidence", ""),
                    "skor": s.get("skor", 0),
                    "alasan": s.get("alasan", ""),
                    "prioritas": s.get("prioritas", "C"),
                    "status": "BELUM DI-DM",
                    "catatan_dm": ""
                })
        except Exception as e:
            print("Batch AI gagal:", e)

    # Utamakan prospek A/B, tetap simpan semua hasil yang bisa dinilai.
    scored.sort(key=lambda x: int(x.get("skor", 0) or 0), reverse=True)
    print(f"Siap dikirim ke Sheets: {len(scored)}")

    if scored:
        result = post_rows(scored)
        print("Sheets:", result)

if __name__ == "__main__":
    main()
