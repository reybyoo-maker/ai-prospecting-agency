from __future__ import annotations
import json, os
from datetime import datetime, timezone, timedelta
import requests
from google import genai
from google.genai import types
from service_catalog import catalog_text

WIB=timezone(timedelta(hours=7))
KEY=os.environ["GEMINI_API_KEY"]
MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite")
SHEET_WEBHOOK_URL=os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN=os.environ["WEBHOOK_TOKEN"]

def generate():
    client=genai.Client(api_key=KEY)
    start=datetime.now(WIB).date()
    schema={"type":"object","properties":{"posts":{"type":"array","items":{"type":"object","properties":{
      "date":{"type":"string"},"platform":{"type":"string"},"format":{"type":"string"},"topic":{"type":"string"},
      "hook":{"type":"string"},"caption":{"type":"string"},"cta":{"type":"string"},"visual_prompt":{"type":"string"}
    },"required":["date","platform","format","topic","hook","caption","cta","visual_prompt"]}}},"required":["posts"]}
    prompt=f"""
Buat konten 7 hari untuk Sonjaya Remote Business Services.
Target: pemilik bisnis/UMKM Indonesia.
Layanan yang dijual:
{catalog_text()}
Platform: Instagram dan TikTok.
Hari pertama: {start.isoformat()}.
Buat satu post per hari per platform. Konten harus edukatif, praktis, natural, dan soft-selling.
Campur Reel, carousel, dan single image. Jangan mengarang studi kasus atau testimoni.
CTA mengarah ke WhatsApp secara umum tanpa menulis nomor telepon.
Return JSON only.
"""
    cfg=types.GenerateContentConfig(response_mime_type="application/json",response_json_schema=schema,max_output_tokens=7000)
    r=client.models.generate_content(model=MODEL,contents=prompt,config=cfg)
    return r.parsed if getattr(r,"parsed",None) else json.loads(r.text)

def push(rows):
    r=requests.post(SHEET_WEBHOOK_URL,json={"token":WEBHOOK_TOKEN,"action":"content_ingest","rows":rows},timeout=90)
    r.raise_for_status()
    data=r.json()
    if not data.get("ok"): raise RuntimeError(data.get("error","content ingest failed"))
    return data

data=generate()
posts=data["posts"] if isinstance(data,dict) else []
print(push(posts))
