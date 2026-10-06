from __future__ import annotations

import json
import os
import re
import textwrap
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
from service_catalog import catalog_text

WIB = timezone(timedelta(hours=7))
KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
SHEET_WEBHOOK_URL = os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]
REPO = os.getenv("GITHUB_REPOSITORY", "reybyoo-maker/ai-prospecting-agency")
BRANCH = os.getenv("GITHUB_REF_NAME", "main")

CAROUSEL_DIR = Path("carousels")
SLIDE_COUNT = 7
PLAN_DAYS = 7


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")[:55] or "carousel"


def hex_color(value: str, fallback: str) -> str:
    value = str(value or "").strip()
    return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else fallback


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int, max_lines: int = 8):
    words = str(text or "").split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if draw.textbbox((0, 0), candidate, font=fnt)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines]


def generate_plan() -> list[dict]:
    client = genai.Client(api_key=KEY)
    start = datetime.now(WIB).date().isoformat()
    schema = {
        "type": "object",
        "properties": {
            "posts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "objective": {"type": "string"},
                        "topic": {"type": "string"},
                        "hook": {"type": "string"},
                        "caption": {"type": "string"},
                        "cta": {"type": "string"},
                        "slides": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "body": {"type": "string"},
                                    "visual_direction": {"type": "string"}
                                },
                                "required": ["title", "body", "visual_direction"]
                            },
                            "minItems": SLIDE_COUNT,
                            "maxItems": SLIDE_COUNT
                        }
                    },
                    "required": ["date", "objective", "topic", "hook", "caption", "cta", "slides"]
                }
            }
        },
        "required": ["posts"]
    }
    prompt = f"""
Kamu adalah AI content strategist + carousel art director khusus konten bisnis Indonesia.
Layanan Sonjaya:
{catalog_text()}

Buat CONTENT PLANNING {PLAN_DAYS} hari mulai {start}.
Setiap hari = tepat 1 carousel Instagram yang juga bisa dipakai sebagai TikTok photo post.
Setiap carousel = tepat {SLIDE_COUNT} slide dengan alur:
1. COVER/hook yang menghentikan scroll
2. masalah/konteks
3. insight utama
4. langkah praktis
5. contoh penerapan
6. kesalahan yang harus dihindari
7. CTA yang ringan

Gaya:
- clean, premium, modern, rapi, mudah dipindai di HP
- bahasa Indonesia natural, bukan tulisan AI kaku
- satu ide utama per slide
- body tiap slide singkat, maksimal sekitar 30-45 kata
- jangan mengarang testimoni, omzet, data, hasil, klien, atau angka tanpa sumber
- soft selling; jangan hard sell di setiap slide
- visual_direction harus menjelaskan ilustrasi/diagram/ikon/foto konseptual yang cocok
- jangan memerintahkan upload atau publish otomatis
Return JSON only.
"""
    cfg = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=schema,
        temperature=0.35,
        max_output_tokens=9000,
    )
    response = client.models.generate_content(model=MODEL, contents=prompt, config=cfg)
    data = response.parsed if getattr(response, "parsed", None) else json.loads(response.text)
    posts = data.get("posts", []) if isinstance(data, dict) else []
    by_date = {}
    for p in posts:
        d = str(p.get("date") or "").strip()
        if d and d not in by_date:
            by_date[d] = p

    start_date = datetime.now(WIB).date()
    cleaned = []
    for offset in range(PLAN_DAYS):
        target_date = start_date + timedelta(days=offset)
        target_iso = target_date.isoformat()
        p = by_date.get(target_iso) or (posts[offset] if offset < len(posts) else {}) or {}
        slides = list(p.get("slides") or [])[:SLIDE_COUNT]
        while len(slides) < SLIDE_COUNT:
            slides.append({
                "title": "Catatan penting",
                "body": "Gunakan langkah yang paling relevan dengan kondisi bisnis kamu.",
                "visual_direction": "Ikon checklist minimalis."
            })
        cleaned.append({
            "date": target_iso,
            "objective": str(p.get("objective") or "Edukasi"),
            "topic": str(p.get("topic") or ("Tips operasional bisnis hari "+str(offset+1))),
            "hook": str(p.get("hook") or "Bisnis kamu masih melakukan ini manual?"),
            "caption": str(p.get("caption") or "Insight praktis untuk pemilik bisnis Indonesia."),
            "cta": str(p.get("cta") or "Simpan post ini dan bagikan ke tim."),
            "slides": slides,
        })
    return cleaned


def render_slide(slide: dict, index: int, total: int, topic: str, cover: bool = False) -> Image.Image:
    W, H = 1080, 1350
    bg = "#F7F4EE"
    ink = "#16202A"
    accent = "#FF6B35"
    muted = "#66717C"
    card = "#FFFFFF"

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Decorative system: clean editorial grid, consistent across a carousel.
    draw.rounded_rectangle((62, 62, W - 62, H - 62), radius=42, outline="#D7D0C5", width=3)
    draw.ellipse((W - 255, 72, W - 82, 245), fill=accent)
    draw.ellipse((W - 150, 137, W - 96, 191), fill=bg)

    draw.text((88, 86), "SONJAYA", font=font(34, True), fill=ink)
    draw.text((W - 205, 93), f"{index}/{total}", font=font(30, True), fill=bg)

    title = str(slide.get("title") or "").strip()
    body = str(slide.get("body") or "").strip()
    visual = str(slide.get("visual_direction") or "").strip()

    if cover:
        draw.text((88, 215), "CONTENT CAROUSEL", font=font(26, True), fill=accent)
        title_lines = wrap_lines(draw, title, font(76, True), 760, 4)
        y = 305
        for line in title_lines:
            draw.text((88, y), line, font=font(76, True), fill=ink)
            y += 92
        draw.rounded_rectangle((88, 770, W - 88, 970), radius=30, fill=ink)
        blines = wrap_lines(draw, body, font(34), 830, 4)
        y = 808
        for line in blines:
            draw.text((126, y), line, font=font(34), fill=bg)
            y += 48
        draw.text((88, 1060), topic[:80], font=font(28, True), fill=muted)
    else:
        draw.text((88, 220), f"SLIDE {index}", font=font(28, True), fill=accent)
        title_lines = wrap_lines(draw, title, font(61, True), 820, 4)
        y = 300
        for line in title_lines:
            draw.text((88, y), line, font=font(61, True), fill=ink)
            y += 75

        draw.rounded_rectangle((88, 620, W - 88, 950), radius=34, fill=card)
        body_lines = wrap_lines(draw, body, font(40), 820, 6)
        y = 674
        for line in body_lines:
            draw.text((128, y), line, font=font(40), fill=ink)
            y += 58

        draw.rounded_rectangle((88, 1010, W - 88, 1160), radius=26, fill="#EEE8DD")
        visual_lines = wrap_lines(draw, "Visual: " + visual, font(25), 820, 3)
        y = 1042
        for line in visual_lines:
            draw.text((124, y), line, font=font(25), fill=muted)
            y += 34

    draw.text((88, 1230), "Save • Share • Implement", font=font(24, True), fill=muted)
    return img


def build_carousel(post: dict) -> dict:
    day = str(post["date"])
    slug = slugify(post["topic"])
    folder = CAROUSEL_DIR / f"{day}-{slug}"
    folder.mkdir(parents=True, exist_ok=True)

    slides = []
    for idx, slide in enumerate(post["slides"], start=1):
        image = render_slide(
            slide,
            idx,
            SLIDE_COUNT,
            post["topic"],
            cover=(idx == 1),
        )
        slide_path = folder / f"{idx:02d}.png"
        image.save(slide_path, format="PNG", optimize=True)
        slides.append(slide_path)

    pdf_path = CAROUSEL_DIR / f"{day}-{slug}.pdf"
    first, rest = slides[0], slides[1:]
    Image.open(first).convert("RGB").save(
        pdf_path,
        "PDF",
        resolution=100.0,
        save_all=True,
        append_images=[Image.open(p).convert("RGB") for p in rest],
    )

    encoded_dir = f"carousels/{day}-{slug}"
    encoded_pdf = f"carousels/{day}-{slug}.pdf"
    cover_rel = f"{encoded_dir}/01.png"
    post["carousel_pdf_url"] = f"https://github.com/{REPO}/blob/{BRANCH}/{encoded_pdf}"
    post["carousel_cover_url"] = f"https://github.com/{REPO}/blob/{BRANCH}/{cover_rel}"
    post["slides_json"] = json.dumps(
        [
            {
                "slide": i + 1,
                "url": f"https://github.com/{REPO}/blob/{BRANCH}/{encoded_dir}/{i+1:02d}.png",
                "title": str(s.get("title") or ""),
            }
            for i, s in enumerate(post["slides"])
        ],
        ensure_ascii=False,
    )
    return post


def push_plans(posts: list[dict]) -> dict:
    rows = []
    for p in posts:
        rows.append({
            "date": p["date"],
            "platform": "Instagram / TikTok",
            "format": "CAROUSEL_7_SLIDES",
            "objective": p["objective"],
            "topic": p["topic"],
            "hook": p["hook"],
            "caption": p["caption"],
            "cta": p["cta"],
            "slide_count": SLIDE_COUNT,
            "carousel_pdf_url": p.get("carousel_pdf_url", ""),
            "carousel_cover_url": p.get("carousel_cover_url", ""),
            "slides_json": p.get("slides_json", ""),
            "status": "PLANNED",
            "publish_mode": "PLANNING_ONLY",
            "catatan": "Planning + carousel dibuat otomatis. Tidak diupload otomatis.",
        })
    response = requests.post(
        SHEET_WEBHOOK_URL,
        json={"token": WEBHOOK_TOKEN, "action": "content_ingest", "rows": rows},
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "content ingest failed"))
    return data


if __name__ == "__main__":
    plans = generate_plan()
    for post in plans:
        build_carousel(post)
    print("CONTENT_PLANS", len(plans))
    print("SHEET", json.dumps(push_plans(plans), ensure_ascii=False))
    print("CAROUSELS", sum(1 for p in plans if p.get("carousel_pdf_url")))
