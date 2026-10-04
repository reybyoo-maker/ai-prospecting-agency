import random
import time
from typing import List

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

MODEL = "gemini-3.6-flash"


class LeadScore(BaseModel):
    id: int
    nama_bisnis: str = Field(default="")
    kota: str = Field(default="")
    kategori: str = Field(default="")
    skor: int = Field(default=0, ge=0, le=100)
    alasan: str = Field(default="")
    prioritas: str = Field(default="C")


class LeadResponse(BaseModel):
    leads: List[LeadScore]


SYSTEM_PROMPT = """
Kamu adalah AI sales researcher untuk agency landing page Indonesia.

Nilai setiap profil bisnis dari 0 sampai 100 berdasarkan kemungkinan
bisnis tersebut cocok ditawari jasa landing page.

Prioritaskan:
- bisnis lokal Indonesia;
- bisnis jasa atau retail;
- bisnis yang kemungkinan menerima booking, order, reservasi,
  katalog, promo, atau lead WhatsApp;
- bisnis yang tampak memiliki peluang memperbaiki alur konversi.

Gunakan hanya evidence dan search query yang diberikan.

JANGAN mengarang:
- nomor WhatsApp
- followers
- omzet
- alamat
- harga
- website
- fakta bisnis lain yang tidak diberikan.

Nama bisnis:
Gunakan nama pada title/evidence jika jelas. Jika tidak jelas,
gunakan username Instagram.

Kota:
Isi hanya jika terbukti dari evidence atau query.

Kategori:
Gunakan kategori bisnis singkat, misalnya Wedding Organizer,
Rental Mobil, Barbershop, Florist, Cafe.

Skor:
80-100 = A = sangat prospektif
65-79 = B = prospektif
0-64 = C = kurang prospektif

Alasan harus spesifik berdasarkan evidence.

Kembalikan semua ID yang diberikan.
"""


def _client(api_key: str):
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=120_000
        ),
    )


def score_batch(api_key: str, leads: list):
    payload = []

    for idx, lead in enumerate(leads):
        payload.append({
            "id": idx,
            "username": lead.get("username", ""),
            "instagram_url": lead.get("instagram_url", ""),
            "title": lead.get("search_title", ""),
            "evidence": lead.get(
                "public_evidence",
                ""
            )[:1400],
            "search_query": lead.get(
                "source_query",
                ""
            ),
        })

    prompt = (
        SYSTEM_PROMPT
        + "\n\nDATA PROSPEK:\n"
        + str(payload)
    )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=LeadResponse,
        max_output_tokens=5000,
    )

    client = _client(api_key)
    last_error = ""

    # Smaller batches are intentionally used to reduce malformed/overlong
    # structured responses.
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config,
            )

            if getattr(response, "parsed", None):
                parsed = response.parsed

                if isinstance(parsed, LeadResponse):
                    result = parsed.leads
                elif isinstance(parsed, dict):
                    result = LeadResponse.model_validate(parsed).leads
                else:
                    result = []

                if result:
                    return [
                        {
                            "id": int(x.id),
                            "nama_bisnis": str(x.nama_bisnis),
                            "kota": str(x.kota),
                            "kategori": str(x.kategori),
                            "skor": max(
                                0,
                                min(100, int(x.skor)),
                            ),
                            "alasan": str(x.alasan),
                            "prioritas": (
                                "A"
                                if int(x.skor) >= 80
                                else (
                                    "B"
                                    if int(x.skor) >= 65
                                    else "C"
                                )
                            ),
                        }
                        for x in result
                    ]

            # Fallback parsing if SDK does not expose parsed.
            text = (response.text or "").strip()
            if text:
                import json
                data = json.loads(text)
                result = LeadResponse.model_validate(data).leads

                return [
                    {
                        "id": int(x.id),
                        "nama_bisnis": str(x.nama_bisnis),
                        "kota": str(x.kota),
                        "kategori": str(x.kategori),
                        "skor": max(
                            0,
                            min(100, int(x.skor)),
                        ),
                        "alasan": str(x.alasan),
                        "prioritas": (
                            "A"
                            if int(x.skor) >= 80
                            else (
                                "B"
                                if int(x.skor) >= 65
                                else "C"
                            )
                        ),
                    }
                    for x in result
                ]

            raise RuntimeError(
                "Gemini tidak mengembalikan hasil terstruktur."
            )

        except Exception as exc:
            last_error = str(exc)

            # google-genai already has retry handling for transient errors.
            # We add a small application-level retry for any final 5xx/429
            # surfaced by the SDK.
            if attempt < 4:
                wait = min(
                    8 * (2 ** attempt),
                    60,
                ) + random.uniform(0, 3)

                print(
                    f"Gemini retry {attempt + 1}/4 "
                    f"dalam {wait:.1f}s: {last_error}"
                )

                time.sleep(wait)
                continue

            break

    raise RuntimeError(
        "Gemini gagal setelah beberapa percobaan: "
        + last_error
    )
