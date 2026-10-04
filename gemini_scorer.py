import json
import requests

MODEL = "gemini-3.6-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"

SYSTEM_PROMPT = """
Kamu adalah AI sales research assistant untuk agency landing page di Indonesia.

Tugas:
1) menilai apakah sebuah profil tampak seperti BISNIS yang layak ditawari jasa landing page;
2) beri skor 0-100;
3) jelaskan alasan berdasarkan BUKTI yang diberikan;
4) jangan mengarang alamat, nomor HP, website, omzet, followers, atau fakta lain yang tidak ada;
5) utamakan bisnis jasa/retail yang kemungkinan memperoleh manfaat dari landing page:
   booking, reservasi, katalog, promo, lead WhatsApp, form, atau penjualan;
6) akun personal/influencer tanpa indikasi bisnis harus mendapat skor rendah;
7) hasil harus berupa JSON array valid saja.

Kategori output harus singkat dalam Bahasa Indonesia.
Prioritas:
- A = skor 80-100
- B = skor 65-79
- C = skor 0-64
"""

def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("JSON array tidak ditemukan")
    return json.loads(text[start:end+1])

def score_batch(api_key: str, leads: list):
    payload = []
    for i, x in enumerate(leads):
        payload.append({
            "id": i,
            "instagram": x.get("instagram_url", ""),
            "username": x.get("username", ""),
            "title": x.get("search_title", ""),
            "evidence": x.get("public_evidence", ""),
            "query": x.get("source_query", "")
        })

    user_prompt = (
        SYSTEM_PROMPT
        + "\n\nData prospek:\n"
        + json.dumps(payload, ensure_ascii=False)
        + """

Kembalikan array dengan field persis:
id, nama_bisnis, kota, kategori, skor, alasan, prioritas

Untuk kota/nama/kategori yang tidak cukup terbukti, gunakan string kosong.
"""
    )

    body = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    r = requests.post(
        ENDPOINT,
        params={"key": api_key},
        json=body,
        timeout=60
    )
    r.raise_for_status()
    data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return _extract_json(text)
