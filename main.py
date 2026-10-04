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

def make_pending_row(lead):
    return {
        "tanggal_ditemukan": datetime.now(WIB).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "nama_bisnis": lead.get(
            "search_title",
            lead.get("username", "")
        ),
        "instagram": lead.get("username", ""),
        "url_instagram": lead.get(
            "instagram_url",
            ""
        ),
        "kota": "",
        "kategori": "",
        "bukti_publik": lead.get(
            "public_evidence",
            ""
        ),
        "skor": 0,
        "alasan": (
            "Menunggu penilaian Gemini "
            "karena layanan sementara tidak tersedia."
        ),
        "prioritas": "REVIEW",
        "status": "AI_REVIEW_PENDING",
        "catatan_dm": "",
    }

def main():
    print("=== AI PROSPECTING AGENCY — INDONESIA ===")
    print("Search layer: TinyFish")
    print("AI layer: Gemini 3.6 Flash")

    prospects = collect_prospects(
        queries_per_run=8,
        max_per_query=10,
    )[:MAX_CANDIDATES]

    print(
        f"Kandidat yang akan diproses: "
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

        try:
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
                score = int(
                    ai.get("skor", 0) or 0
                )

                if score >= 80:
                    priority = "A"
                elif score >= 65:
                    priority = "B"
                else:
                    priority = "C"

                rows.append({
                    "tanggal_ditemukan": datetime.now(
                        WIB
                    ).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "nama_bisnis": ai.get(
                        "nama_bisnis",
                        lead.get(
                            "search_title",
                            lead.get("username", "")
                        ),
                    ),
                    "instagram": lead.get(
                        "username",
                        ""
                    ),
                    "url_instagram": lead.get(
                        "instagram_url",
                        ""
                    ),
                    "kota": ai.get(
                        "kota",
                        ""
                    ),
                    "kategori": ai.get(
                        "kategori",
                        ""
                    ),
                    "bukti_publik": lead.get(
                        "public_evidence",
                        ""
                    ),
                    "skor": score,
                    "alasan": ai.get(
                        "alasan",
                        ""
                    ),
                    "prioritas": priority,
                    "status": "BELUM DI-DM",
                    "catatan_dm": "",
                })

        except Exception as exc:
            print(
                f"Gemini batch {batch_no} gagal "
                f"setelah retry: {exc}"
            )

            # Keep the candidate instead of dropping it.
            for lead in batch:
                rows.append(
                    make_pending_row(lead)
                )

    rows.sort(
        key=lambda x: x.get(
            "skor",
            0
        ),
        reverse=True,
    )

    print(
        f"Total baris siap dikirim: "
        f"{len(rows)}"
    )

    if rows:
        result = send_to_sheet(rows)
        print(
            "GOOGLE SHEET:",
            result
        )

if __name__ == "__main__":
    main()
