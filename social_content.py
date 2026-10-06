from __future__ import annotations
import json, os
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import types
from service_catalog import catalog_text

WIB=timezone(timedelta(hours=7))
MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite")
KEY=os.environ["GEMINI_API_KEY"]

def generate_week(days=7):
    client=genai.Client(api_key=KEY)
    today=datetime.now(WIB).date()
    schema={"type":"object","properties":{"posts":{"type":"array","items":{
      "type":"object","properties":{
        "date":{"type":"string"},"platform":{"type":"string"},"format":{"type":"string"},
        "topic":{"type":"string"},"hook":{"type":"string"},"caption":{"type":"string"},
        "cta":{"type":"string"},"visual_prompt":{"type":"string"}
      },"required":["date","platform","format","topic","hook","caption","cta","visual_prompt"]
    }},"required":["posts"]}
    prompt=f"""
Buat kalender konten {days} hari untuk agensi remote yang menawarkan:
{catalog_text()}
Niche audiens: pemilik bisnis/UMKM Indonesia.
Platform: Instagram dan TikTok.
Setiap hari buat satu ide yang berguna, tidak memalukan, tidak spam, dan mengarah ke jasa secara halus.
Gunakan format campuran Reel, carousel, dan single image.
CTA boleh mengarah ke WhatsApp.
Tanggal mulai: {today.isoformat()}.
Return JSON only.
"""
    r=client.models.generate_content(model=MODEL,contents=prompt,config=types.GenerateContentConfig(response_mime_type="application/json",response_json_schema=schema,max_output_tokens=5000))
    return r.parsed if getattr(r,"parsed",None) else json.loads(r.text)

if __name__=="__main__":
    print(json.dumps(generate_week(7),ensure_ascii=False,indent=2))
