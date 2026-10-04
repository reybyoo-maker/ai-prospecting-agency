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

Jangan mengarang nomor WhatsApp, followers, omzet, alamat, harga,
website, atau fakta lain.

Gunakan evidence dan query yang diberikan.
Nama bisnis boleh menggunakan nama pada title/evidence;
bila tidak jelas gunakan username.

Kembalikan hanya JSON terstruktur.
"""

SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "INTEGER"},
            "nama_bisnis": {"type": "STRING"},
            "kota": {"type": "STRING"},
            "kategori": {"type": "STRING"},
            "skor": {"type": "INTEGER"},
            "alasan": {"type": "STRING"},
            "prioritas": {
                "type": "STRING",
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

def score_batch(api_key, leads):
    payload = []

    for idx, lead in enumerate(leads):
        payload.append({
            "id": idx,
            "instagram": lead.get("username", ""),
            "instagram_url": lead.get("instagram_url", ""),
            "title": lead.get("search_title", ""),
            "evidence": lead.get(
                "public_evidence",
                "",
            )[:1500],
            "query": lead.get(
                "source_query",
                "",
            ),
        })

    prompt = (
        SYSTEM_PROMPT
        + "\n\nDATA PROSPEK:\n"
        + json.dumps(
            payload,
            ensure_ascii=False,
        )
    )

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
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

            if r.status_code in {
                408, 429, 500, 502, 503, 504
            }:
                last_error = (
                    f"HTTP {r.status_code}: "
                    f"{r.text[:300]}"
                )

                if attempt < 5:
                    wait = min(
                        5 * (2 ** attempt),
                        60,
                    ) + random.uniform(0, 2)

                    print(
                        f"Gemini sementara bermasalah "
                        f"({r.status_code}); "
                        f"retry {attempt + 1}/5 "
                        f"dalam {wait:.1f}s"
                    )
                    time.sleep(wait)
                    continue

                break

            r.raise_for_status()

            data = r.json()
            candidates = data.get(
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

            output = parts[0].get(
                "text",
                "",
            )

            if not output:
                raise RuntimeError(
                    "Gemini mengembalikan teks kosong."
                )

            parsed = json.loads(output)

            if not isinstance(parsed, list):
                raise ValueError(
                    "Output Gemini bukan array."
                )

            clean = []

            for item in parsed:
                score = int(
                    item.get("skor", 0) or 0
                )
                score = max(
                    0,
                    min(100, score),
                )

                if score >= 80:
                    priority = "A"
                elif score >= 65:
                    priority = "B"
                else:
                    priority = "C"

                clean.append({
                    "id": int(
                        item.get("id", 0)
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
            json.JSONDecodeError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            last_error = str(exc)

            if attempt < 5:
                wait = min(
                    5 * (2 ** attempt),
                    60,
                ) + random.uniform(0, 2)

                print(
                    f"Gemini retry {attempt + 1}/5 "
                    f"dalam {wait:.1f}s: {last_error}"
                )
                time.sleep(wait)
                continue

            break

    raise RuntimeError(
        "Gemini gagal setelah 6 percobaan: "
        + last_error
    )
