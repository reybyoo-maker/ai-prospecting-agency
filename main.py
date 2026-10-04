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
AI_BATCH_SIZE = 5


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def fallback_score(lead):
    """
    Backup scoring so a temporary Gemini outage never creates score=0
    rows that look like genuine low-quality leads.
    """
    text = (
        (lead.get("search_title", "") + " " +
         lead.get("public_evidence", "") + " " +
         lead.get("source_query", ""))
        .lower()
    )

    keywords = {
        "whatsapp": 14,
        "booking": 12,
        "order": 10,
        "link in bio": 10,
        "instagram": 4,
        "cafe": 6,
        "restaurant": 6,
        "barbershop": 7,
        "salon": 7,
        "florist": 7,
        "wedding": 9,
        "rental": 8,
        "travel": 7,
        "property": 8,
        "clinic": 8,
        "gym": 7,
        "bakery": 6,
        "catering": 7,
    }

    score = 45

    for word, points in keywords.items():
        if word in text:
            score += points

    score = max(25, min(78, score))

    return {
        "skor": score,
        "prioritas": "B" if score >= 65 else "C",
        "alasan": (
            "Penilaian sementara berbasis sinyal publik karena "
            "Gemini sedang tidak tersedia. Akan dinilai ulang pada run berikutnya."
        ),
        "kategori": "",
        "kota": "",
        "nama_bisnis": lead.get(
            "search_title",
            lead.get("username", ""),
        ),
    }


def build_chat_template(lead, ai):
    business = (
        ai.get("nama_bisnis")
        or lead.get("username")
        or "kak"
    ).strip()

    username = (
        lead.get("username")
        or ""
    ).strip()

    category = (
        ai.get("kategori")
        or "bisnis kakak"
    ).strip()

    city = (
        ai.get("kota")
        or ""
    ).strip()

    location = (
        f" di {city}"
        if city
        else ""
    )

    return (
        f"Halo kak, izin kenalan. Saya Rey. "
        f"Saya menemukan akun @{username} dan melihat {business} "
        f"punya potensi bagus untuk diarahkan ke landing page yang lebih rapi. "
        f"Untuk {category}{location}, landing page bisa membantu calon customer "
        f"melihat layanan, promo, dan langsung chat tanpa harus mencari-cari "
        f"informasi. Saya menyediakan jasa landing page yang bisa disesuaikan "
        f"dengan kebutuhan bisnis. Boleh saya kirim contoh portofolionya kak?"
    )


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
    print("Search: TinyFish")
    print("AI: Gemini 3.6 Flash via official Google GenAI SDK")
    print("Output: Google Sheet + Template Chat")

    prospects = collect_prospects(
        queries_per_run=8,
        max_per_query=12,
    )[:MAX_CANDIDATES]

    print(
        f"Kandidat yang akan dinilai: "
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
                int(item["id"]): item
                for item in results
            }

            for idx, lead in enumerate(batch):
                ai = by_id.get(idx)

                if not ai:
                    ai = fallback_score(lead)
                    status = "AI_REVIEW_PENDING"
                else:
                    status = "BELUM DI-DM"

                rows.append({
                    "tanggal_ditemukan": datetime.now(
                        WIB
                    ).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "nama_bisnis": ai.get(
                        "nama_bisnis",
                        lead.get("username", ""),
                    ),
                    "instagram": lead.get(
                        "username",
                        "",
                    ),
                    "url_instagram": lead.get(
                        "instagram_url",
                        "",
                    ),
                    "kota": ai.get(
                        "kota",
                        "",
                    ),
                    "kategori": ai.get(
                        "kategori",
                        "",
                    ),
                    "bukti_publik": lead.get(
                        "public_evidence",
                        "",
                    ),
                    "skor": int(
                        ai.get("skor", 0)
                        or 0
                    ),
                    "alasan": ai.get(
                        "alasan",
                        "",
                    ),
                    "prioritas": ai.get(
                        "prioritas",
                        "C",
                    ),
                    "status": status,
                    "catatan_dm": "",
                    "template_chat": build_chat_template(
                        lead,
                        ai,
                    ),
                })

        except Exception as exc:
            print(
                f"Batch {batch_no} gagal setelah retry: "
                f"{exc}"
            )

            # Never lose discovered candidates.
            for lead in batch:
                ai = fallback_score(lead)

                rows.append({
                    "tanggal_ditemukan": datetime.now(
                        WIB
                    ).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "nama_bisnis": ai.get(
                        "nama_bisnis",
                        lead.get("username", ""),
                    ),
                    "instagram": lead.get(
                        "username",
                        "",
                    ),
                    "url_instagram": lead.get(
                        "instagram_url",
                        "",
                    ),
                    "kota": "",
                    "kategori": "",
                    "bukti_publik": lead.get(
                        "public_evidence",
                        "",
                    ),
                    "skor": ai["skor"],
                    "alasan": ai["alasan"],
                    "prioritas": ai["prioritas"],
                    "status": "AI_REVIEW_PENDING",
                    "catatan_dm": "",
                    "template_chat": build_chat_template(
                        lead,
                        ai,
                    ),
                })

    rows.sort(
        key=lambda x: x.get("skor", 0),
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
            result,
        )


if __name__ == "__main__":
    main()
