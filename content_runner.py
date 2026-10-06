from __future__ import annotations
import json, os, re, textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
from service_catalog import catalog_text

WIB=timezone(timedelta(hours=7))
KEY=os.environ["GEMINI_API_KEY"]
MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite")
SHEET_WEBHOOK_URL=os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN=os.environ["WEBHOOK_TOKEN"]
REPO=os.getenv("GITHUB_REPOSITORY","reybyoo-maker/ai-prospecting-agency")
BRANCH=os.getenv("GITHUB_REF_NAME","main")

def font(size):
    candidates=[
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def make_asset(post):
    date=str(post["date"])
    platform=str(post["platform"]).lower()
    slug=re.sub(r"[^a-z0-9]+","-",post["topic"].lower())[:42].strip("-") or "post"
    filename=f"{date}-{platform}-{slug}.png"
    path=Path("social_assets")/filename
    path.parent.mkdir(parents=True,exist_ok=True)

    img=Image.new("RGB",(1080,1350),"white")
    d=ImageDraw.Draw(img)
    title_font=font(56)
    hook_font=font(80)
    body_font=font(38)
    cta_font=font(42)

    d.text((80,70),"SONJAYA REMOTE BUSINESS",font=title_font,fill="black")
    d.text((80,220),"."+str(post["hook"])[:180],font=hook_font,fill="black")
    body=post["caption"].replace("\n"," ").strip()
    body_lines=textwrap.wrap(body,width=34)[:9]
    y=470
    for line in body_lines:
        d.text((80,y),line,font=body_font,fill="black")
        y+=58
    d.text((80,1110),"CTA: "+str(post["cta"])[:140],font=cta_font,fill="black")
    d.text((80,1250),"Instagram / TikTok • "+platform.upper(),font=font(28),fill="black")
    img.save(path,format="PNG",optimize=True)
    raw=f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/social_assets/{filename}"
    post["asset_path"]=str(path)
    post["asset_url"]=raw
    return post

def generate():
    client=genai.Client(api_key=KEY)
    start=datetime.now(WIB).date()
    schema={"type":"object","properties":{"posts":{"type":"array","items":{"type":"object","properties":{
      "date":{"type":"string"},"platform":{"type":"string"},"format":{"type":"string"},"topic":{"type":"string"},
      "hook":{"type":"string"},"caption":{"type":"string"},"cta":{"type":"string"},"visual_prompt":{"type":"string"}
    },"required":["date","platform","format","topic","hook","caption","cta","visual_prompt"]}}},"required":["posts"]}
    prompt=f"""
Buat kalender konten 7 hari untuk Sonjaya Remote Business Services.
Target: pemilik bisnis/UMKM Indonesia.
Layanan:
{catalog_text()}
Platform: Instagram dan TikTok.
Hari pertama: {start.isoformat()}.
Buat satu post per hari per platform. Konten harus edukatif, praktis, natural, soft-selling.
Campur Reel, carousel, dan single image, tetapi asset automation hanya akan membuat single-image fallback.
Jangan mengarang studi kasus/testimoni/angka.
CTA arahkan ke WhatsApp secara umum tanpa menulis nomor.
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
for p in posts:
    make_asset(p)

Path("social_publish_payload.json").write_text(json.dumps(posts,ensure_ascii=False,indent=2),encoding="utf-8")
print(push(posts))
print("ASSETS",len([p for p in posts if p.get("asset_url")]))
