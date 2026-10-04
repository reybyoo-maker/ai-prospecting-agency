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
Kamu adalah AI sales research assistant untuk agency landing page di Indonesia.

Nilai prospek bisnis dari 0-100 berdasarkan kemungkinan bisnis tersebut
cocok ditawari jasa landing page.

Prioritaskan:
- bisnis lokal Indonesia;
- jasa atau retail;
- bisnis yang kemungkinan menerima booking, order, reservasi,
  katalog, promo, atau lead WhatsApp;
- bisnis yang tampak memiliki peluang memperbaiki alur konversi.

Jangan mengarang:
- nomor WhatsApp
- followers
- omzet
- alamat
- website
- harga
- informasi bisnis yang tidak terdapat di evidence.

Nama bisnis boleh diambil dari username/evidence jika cukup jelas.

Output JSON array saja.

Field:
id
nama_bisnis
kota
kategori
skor
alasan
prioritas

Prioritas:
A = skor 80-100
B = skor 65-79
C = skor 0-64
"""

def extract_json(text):
    text = text.strip()

    if "```" in text:
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("[")
    end = text.rfind("]")

    if start < 0 or end < 0:
        raise ValueError("Gemini tidak mengembalikan JSON array.")

    return json.loads(text[start:end + 1])

def score_batch(api_key, leads):
    payload = []

    for idx, lead in enumerate(leads):
        payload.append({
            "id": idx,
            "username": lead.get("username", ""),
            "instagram_url": lead.get("instagram_url", ""),
            "evidence": lead.get("public_evidence", "")[:1400],
            "query": lead.get("source_query", ""),
        })

    prompt = (
        SYSTEM_PROMPT
        + "\n\nDATA:\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n\nKembalikan JSON array valid."
    )

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    for attempt in range(3):
        response = requests.post(
            ENDPOINT,
            params={"key": api_key},
            json=body,
            timeout=90,
        )

        if response.status_code == 429 and attempt < 2:
            time.sleep(20 * (attempt + 1))
            continue

        response.raise_for_status()

        data = response.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]

        return extract_json(text)

    raise RuntimeError("Gemini gagal setelah beberapa percobaan.")
