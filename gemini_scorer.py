import json
import requests

MODEL = "gemini-3.6-flash"

ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + MODEL
    + ":generateContent"
)

SYSTEM_PROMPT = """
Kamu adalah AI sales research assistant untuk agency landing page di Indonesia.

Nilai setiap prospek bisnis dari 0-100 berdasarkan seberapa masuk akal
ditawari jasa landing page.

Prioritaskan:
- bisnis jasa / retail;
- bisnis yang tampak menerima booking, reservasi, order, katalog, promo,
  lead WhatsApp, formulir, atau penjualan;
- bisnis yang tampak belum memiliki jalur website/landing page yang jelas.

Jangan mengarang fakta.
Jangan mengarang nomor WhatsApp, followers, omzet, alamat, atau website.
Gunakan hanya informasi pada data yang diberikan.

Skala:
A = 80-100
B = 65-79
C = 0-64

Jawab HANYA JSON array yang valid.
"""

def extract_json(text: str):
    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]

    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1:
        raise ValueError("Respons Gemini tidak berisi JSON array.")

    return json.loads(text[start:end + 1])

def score_batch(api_key: str, leads: list):
    payload = []

    for i, lead in enumerate(leads):
        payload.append({
            "id": i,
            "username": lead.get("username", ""),
            "instagram_url": lead.get("instagram_url", ""),
            "title": lead.get("search_title", ""),
            "evidence": lead.get("public_evidence", ""),
            "search_query": lead.get("source_query", ""),
        })

    prompt = (
        SYSTEM_PROMPT
        + "\n\nDATA PROSPEK:\n"
        + json.dumps(payload, ensure_ascii=False)
        + """

Kembalikan field persis:
id, nama_bisnis, kota, kategori, skor, alasan, prioritas

Jadikan string kosong untuk nama/kota/kategori yang tidak cukup terbukti.
"""
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
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    response = requests.post(
        ENDPOINT,
        params={"key": api_key},
        json=body,
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]

    return extract_json(text)
