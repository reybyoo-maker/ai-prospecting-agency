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
MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite")
SHEET_WEBHOOK_URL=os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN=os.environ["WEBHOOK_TOKEN"]
REPO=os.getenv("GITHUB_REPOSITORY","reybyoo-maker/ai-prospecting-agency")
BRANCH=os.getenv("GITHUB_REF_NAME","main")
TIKTOK_MEDIA_BASE_URL=os.getenv("TIKTOK_MEDIA_BASE_URL","").rstrip("/")

def font(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]:
        if Path(p).exists():
            return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def slugify(s):
    return re.sub(r"[^a-z0-9]+","-",str(s).lower()).strip("-")[:42] or "post"

def make_asset(post):
    date=str(post["date"])
    platform=str(post["platform"]).lower()
    slug=slugify(post["topic"])
    filename=f"{date}-{platform}-{slug}.png"
    path=Path("social_assets")/filename
    path.parent.mkdir(parents=True,exist_ok=True)

    img=Image.new("RGB",(1080,1350),"white")
    d=ImageDraw.Draw(img)
    d.text((80,70),"SONJAYA REMOTE BUSINESS",font=font(54),fill="black")

    hook=str(post["hook"]).replace("\n"," ").strip()
    d.text((80,210),"."+hook[:180],font=font(76),fill="black")

    body=str(post["caption"]).replace("\n"," ").strip()
    lines=textwrap.wrap(body,width=34)[:9]
    y=480
    for line in lines:
        d.text((80,y),line,font=font(37),fill="black")
        y+=56

    d.text((80,1110),"CTA: "+str(post["cta"])[:140],font=font(40),fill="black")
    d.text((80,1250),platform.upper()+" • Sonjaya Remote Business Services",font=font(27),fill="black")
    img.save(path,format="PNG",optimize=True)

    post["asset_path"]=str(path)
    post["asset_url"]=f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/social_assets/{filename}"
    post["tiktok_asset_url"]=(
        f"{TIKTOK_MEDIA_BASE_URL}/{filename}" if TIKTOK_MEDIA_BASE_URL else ""
    )
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
Campur Reel, carousel, dan single image, tetapi automated asset fallback memakai single image.
Jangan mengarang studi kasus, testimoni, omzet, angka, atau hasil.
CTA arahkan ke WhatsApp secara umum tanpa menulis nomor.
Return JSON only.
"""
    cfg=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=schema,
        max_output_tokens=7000
    )
    r=client.models.generate_content(model=MODEL,contents=prompt,config=cfg)
    return r.parsed if getattr(r,"parsed",None) else json.loads(r.text)

def push(rows):
    r=requests.post(
        SHEET_WEBHOOK_URL,
        json={"token":WEBHOOK_TOKEN,"action":"content_ingest","rows":rows},
        timeout=90
    )
    r.raise_for_status()
    data=r.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error","content ingest failed"))
    return data

data=generate()
posts=data["posts"] if isinstance(data,dict) else []
today=datetime.now(WIB).date().isoformat()
for p in posts:
    if str(p.get("date",""))==today:
        make_asset(p)

Path("social_publish_payload.json").write_text(
    json.dumps(posts,ensure_ascii=False,indent=2),
    encoding="utf-8"
)
print(push(posts))
print("PLANNED_POSTS",len(posts),"TODAY_ASSETS",sum(1 for p in posts if p.get("asset_url")))
