import json
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

Field:
id
nama_bisnis
kota
kategori
skor
alasan
prioritas
"""

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
        raise ValueError("Respons Gemini tidak berisi JSON array.")

    return json.loads(text[start:end + 1])

def score_batch(api_key, leads):
    payload = []

    for idx, lead in enumerate(leads):
        payload.append({
            "id": idx,
            "username": lead.get("username", ""),
            "instagram_url": lead.get("instagram_url", ""),
            "title": lead.get("search_title", ""),
            "evidence": lead.get("public_evidence", "")[:1500],
            "query": lead.get("source_query", ""),
        })

    prompt = (
        SYSTEM_PROMPT
        + "\n\nDATA PROSPEK:\n"
        + json.dumps(payload, ensure_ascii=False)
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
        },
    }

    for attempt in range(3):
        r = requests.post(
            ENDPOINT,
            params={"key": api_key},
            json=body,
            timeout=90,
        )

        if r.status_code == 429 and attempt < 2:
            time.sleep(15 * (attempt + 1))
            continue

        r.raise_for_status()

        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]

        return extract_json(text)

    raise RuntimeError("Gemini gagal setelah beberapa percobaan.")
