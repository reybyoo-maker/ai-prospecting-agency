import json
import random
import time

import requests

MODEL = "gemini-3.6-flash"

ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + MODEL
    + ":generateContent"
)

SYSTEM_PROMPT = """
Kamu adalah AI sales researcher untuk agency landing page Indonesia.

Nilai setiap profil bisnis dari 0 sampai 100 berdasarkan kemungkinan
bisnis tersebut cocok ditawari jasa landing page.

Prioritaskan:
- bisnis lokal Indonesia;
- bisnis jasa atau retail;
- bisnis yang kemungkinan menerima booking, order, reservasi,
  katalog, promo, atau lead WhatsApp;
- bisnis yang terlihat memiliki peluang memperbaiki alur konversi.

PENTING:
Gunakan hanya data yang diberikan.
Jangan mengarang nomor WhatsApp, followers, omzet, alamat, harga,
website, atau fakta lain.

Nama bisnis:
- gunakan nama dari title/evidence bila jelas;
- bila tidak jelas, gunakan username Instagram.

Kota:
- isi hanya bila terbukti dari evidence/query.

Kategori:
- singkat, misalnya "Wedding Organizer", "Rental Mobil", "Barbershop".

Skor:
80-100 = A, sangat prospektif
65-79 = B, prospektif
0-64 = C, kurang prospektif

Alasan harus menjelaskan kenapa bisnis tersebut cocok atau tidak cocok
untuk ditawari landing page.

Kembalikan HANYA array JSON sesuai schema.
"""

SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
            },
            "nama_bisnis": {
                "type": "string",
            },
            "kota": {
                "type": "string",
            },
            "kategori": {
                "type": "string",
            },
            "skor": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
            },
            "alasan": {
                "type": "string",
            },
            "prioritas": {
                "type": "string",
                "enum": ["A", "B", "C"],
            },
        },
        "required": [
            "id",
            "nama_bisnis",
            "kota",
            "kategori",
            "skor",
            "alasan",
            "prioritas",
        ],
    },
}

TRANSIENT = {
    408,
    429,
    500,
    502,
    503,
    504,
}

def score_batch(
    api_key: str,
    leads: list,
):
    data = []

    for index, lead in enumerate(leads):
        data.append({
            "id": index,
            "instagram": lead.get(
                "username",
                "",
            ),
            "instagram_url": lead.get(
                "instagram_url",
                "",
            ),
            "title": lead.get(
                "search_title",
                "",
            ),
            "evidence": lead.get(
                "public_evidence",
                "",
            )[:1600],
            "search_query": lead.get(
                "source_query",
                "",
            ),
        })

    prompt = (
        SYSTEM_PROMPT
        + "\n\nDATA PROSPEK:\n"
        + json.dumps(
            data,
            ensure_ascii=False,
        )
    )

    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": {
            # Official Gemini 3.6 guidance: use structured output
            # and do not send temperature/top_p/top_k.
            "responseFormat": {
                "text": {
                    "mimeType": "application/json",
                    "schema": SCHEMA,
                }
            },
            "maxOutputTokens": 5000,
        },
    }

    last_error = ""

    for attempt in range(6):
        try:
            r = requests.post(
                ENDPOINT,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=120,
            )

            if r.status_code in TRANSIENT:
                last_error = (
                    f"HTTP {r.status_code}: "
                    f"{r.text[:300]}"
                )

                if attempt < 5:
                    wait = min(
                        5 * (2 ** attempt),
                        60,
                    ) + random.uniform(
                        0,
                        2,
                    )

                    print(
                        f"Gemini temporary error "
                        f"{r.status_code}; "
                        f"retry {attempt + 1}/5 "
                        f"in {wait:.1f}s"
                    )

                    time.sleep(wait)
                    continue

                break

            r.raise_for_status()

            payload = r.json()

            candidates = payload.get(
                "candidates",
                [],
            )

            if not candidates:
                raise RuntimeError(
                    "Gemini tidak mengembalikan candidates."
                )

            parts = candidates[0].get(
                "content",
                {},
            ).get(
                "parts",
                [],
            )

            if not parts:
                raise RuntimeError(
                    "Gemini tidak mengembalikan parts."
                )

            text = parts[0].get(
                "text",
                "",
            )

            if not text:
                raise RuntimeError(
                    "Gemini mengembalikan teks kosong."
                )

            result = json.loads(text)

            # Validate scoring before sending to Sheet.
            if not isinstance(result, list):
                raise ValueError(
                    "Output Gemini bukan array."
                )

            clean = []

            for item in result:
                score = int(
                    item.get(
                        "skor",
                        0,
                    )
                )

                score = max(
                    0,
                    min(
                        100,
                        score,
                    ),
                )

                if score >= 80:
                    priority = "A"
                elif score >= 65:
                    priority = "B"
                else:
                    priority = "C"

                clean.append({
                    "id": int(
                        item.get(
                            "id",
                            0,
                        )
                    ),
                    "nama_bisnis": str(
                        item.get(
                            "nama_bisnis",
                            "",
                        )
                    ),
                    "kota": str(
                        item.get(
                            "kota",
                            "",
                        )
                    ),
                    "kategori": str(
                        item.get(
                            "kategori",
                            "",
                        )
                    ),
                    "skor": score,
                    "alasan": str(
                        item.get(
                            "alasan",
                            "",
                        )
                    ),
                    "prioritas": priority,
                })

            return clean

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ) as exc:
            last_error = str(exc)

            if attempt < 5:
                wait = min(
                    5 * (2 ** attempt),
                    60,
                ) + random.uniform(
                    0,
                    2,
                )

                print(
                    f"Gemini retry {attempt + 1}/5 "
                    f"in {wait:.1f}s: {last_error}"
                )

                time.sleep(wait)
                continue

            break

    raise RuntimeError(
        "Gemini gagal setelah 6 percobaan: "
        + last_error
    )
