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
Kamu adalah AI sales researcher untuk agency landing page di Indonesia.

Tugas:
Menilai apakah sebuah profil bisnis layak ditawari jasa landing page.

Prioritas tinggi:
- bisnis lokal Indonesia;
- jasa atau retail;
- bisnis yang menerima booking, reservasi, order, katalog, promo,
  WhatsApp leads, formulir, atau penjualan;
- bisnis yang tampak belum memiliki alur website/landing page yang kuat.

Gunakan hanya evidence yang diberikan.
JANGAN mengarang nomor WhatsApp, followers, omzet, alamat, harga,
website, atau fakta lain.

Nilai:
80-100 = sangat prospektif (A)
65-79 = prospektif (B)
0-64 = kurang prospektif (C)

Jawab HANYA JSON array valid.
"""

TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}

def extract_json(text):
    text = text.strip()

    if "```" in text:
        text = (
            text.replace("```json", "")
            .replace("```", "")
            .strip()
        )

    start = text.find("[")
    end = text.rfind("]")

    if start < 0 or end < 0:
        raise ValueError(
            "Respons Gemini tidak berisi JSON array."
        )

    return json.loads(text[start:end + 1])

def score_batch(api_key, leads):
    payload = []

    for idx, lead in enumerate(leads):
        payload.append({
            "id": idx,
            "username": lead.get("username", ""),
            "instagram_url": lead.get("instagram_url", ""),
            "title": lead.get("search_title", ""),
            "evidence": lead.get(
                "public_evidence", ""
            )[:1500],
            "query": lead.get("source_query", ""),
        })

    prompt = (
        SYSTEM_PROMPT
        + "\n\nDATA PROSPEK:\n"
        + json.dumps(
            payload,
            ensure_ascii=False
        )
        + "\n\nKembalikan JSON array valid."
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
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "maxOutputTokens": 3000,
        },
    }

    last_error = None

    # 6 attempts: 5s, 10s, 20s, 40s, 60s, 60s (+ small jitter).
    for attempt in range(6):
        try:
            r = requests.post(
                ENDPOINT,
                params={"key": api_key},
                json=body,
                timeout=120,
            )

            if r.status_code in TRANSIENT_STATUS:
                last_error = (
                    f"Gemini HTTP {r.status_code}: "
                    f"{r.text[:500]}"
                )

                if attempt < 5:
                    wait = min(
                        5 * (2 ** attempt),
                        60
                    )
                    wait += random.uniform(0, 2)

                    print(
                        f"Gemini sementara tidak tersedia "
                        f"({r.status_code}). "
                        f"Retry {attempt + 1}/5 dalam "
                        f"{wait:.1f} detik..."
                    )
                    time.sleep(wait)
                    continue

                break

            r.raise_for_status()

            data = r.json()

            candidates = data.get(
                "candidates",
                []
            )

            if not candidates:
                raise RuntimeError(
                    "Gemini mengembalikan 0 candidates."
                )

            parts = candidates[0].get(
                "content",
                {}
            ).get("parts", [])

            if not parts:
                raise RuntimeError(
                    "Respons Gemini tidak memiliki parts."
                )

            text = parts[0].get("text", "")

            if not text:
                raise RuntimeError(
                    "Gemini mengembalikan teks kosong."
                )

            return extract_json(text)

        except requests.RequestException as exc:
            last_error = str(exc)

            if attempt < 5:
                wait = min(
                    5 * (2 ** attempt),
                    60
                ) + random.uniform(0, 2)

                print(
                    f"Gemini request error. "
                    f"Retry {attempt + 1}/5 dalam "
                    f"{wait:.1f} detik..."
                )
                time.sleep(wait)
                continue

            break

    raise RuntimeError(
        "Gemini gagal setelah 6 percobaan. "
        f"Error terakhir: {last_error}"
    )
