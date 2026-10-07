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

CONTENT_PILLARS = [
    "Lead Generation & Prospecting",
    "Sales Follow-up & Conversion",
    "Customer Support & WhatsApp",
    "Social Media & Content Operations",
    "Admin & Back-office Automation",
    "Research, Data & Reporting",
    "Appointment Setting & Retention",
]

BLUE = "#0B5FFF"
NAVY = "#073B8C"
BLUE_2 = "#2F80ED"
LIGHT_BLUE = "#DCEBFF"
PALE_BLUE = "#F4F8FF"
INK = "#10233B"
MUTED = "#607080"
WHITE = "#FFFFFF"
CYAN = "#8FD3FF"

DESIGN_STYLES = ["BOLD_EDITORIAL","SPLIT_SCREEN","DASHBOARD","FLOW_DIAGRAM","CARD_STACK","TYPE_POSTER","MINIMAL_TECH"]
CONTENT_ANGLES = ["framework 3-5 langkah yang bisa langsung diterapkan","myth vs reality yang membongkar miskonsepsi","audit checklist untuk menemukan bottleneck","decision guide yang membantu memilih cara A atau B","workflow end-to-end yang realistis","mistake breakdown + perbaikan praktis","quick wins yang bisa dikerjakan dalam 30 menit"]


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
                        "pillar": {"type": "string"},
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
                                    "role": {"type": "string"},
                                    "title": {"type": "string"},
                                    "body": {"type": "string"},
                                    "visual_direction": {"type": "string"},
                        "design_notes": {"type": "string"}
                                },
                                "required": ["role", "title", "body", "visual_direction", "design_notes"]
                            },
                            "minItems": SLIDE_COUNT,
                            "maxItems": SLIDE_COUNT
                        }
                    },
                    "required": ["date", "pillar", "objective", "topic", "hook", "caption", "cta", "slides"]
                }
            }
        },
        "required": ["posts"]
    }
    prompt = f"""
Kamu adalah CONTENT DIRECTOR senior untuk Sonjaya Remote Business Services.
Target utama: owner/manager UMKM Indonesia yang punya masalah operasional, penjualan, follow-up,
customer support, konten, admin, data, atau appointment.
Buat CONTENT PLANNING 7 hari mulai {start} untuk feed Sonjaya.
Setiap hari = tepat 1 carousel feed 1080x1350, tepat 7 slide.
Pilar wajib per hari:
Hari 1: Lead Generation & Prospecting
Hari 2: Sales Follow-up & Conversion
Hari 3: Customer Support & WhatsApp
Hari 4: Social Media & Content Operations
Hari 5: Admin & Back-office Automation
Hari 6: Research, Data & Reporting
Hari 7: Appointment Setting & Retention

STRUKTUR CERITA WAJIB:
Slide 1 = HOOK. Berhenti-scroll: satu kalimat tajam dan spesifik.
Slide 2 = PROBLEM. Situasi nyata + konsekuensi tanpa mengarang angka.
Slide 3 = INSIGHT. Satu pemikiran yang mengubah sudut pandang.
Slide 4 = FRAMEWORK. Langkah/kerangka yang bisa langsung dipakai.
Slide 5 = EXAMPLE. Contoh operasional realistis untuk bisnis Indonesia.
Slide 6 = MISTAKE. Kesalahan/keberatan umum + perbaikannya.
Slide 7 = CTA. Ajakan ringan untuk save/share/DM/WhatsApp.

BRAND:
- Palet hanya biru, biru muda, putih, navy.
- Kesan premium, modern, smart, human; bukan template AI generik.
- 7 hari wajib 7 design family berbeda: BOLD_EDITORIAL, SPLIT_SCREEN, DASHBOARD, FLOW_DIAGRAM, CARD_STACK, TYPE_POSTER, MINIMAL_TECH.
- Gunakan robot/maskot Sonjaya 1-2 kali per carousel dengan posisi berbeda.
- Gunakan hierarchy typography yang kuat, grid rapi, rounded cards, numbered markers, diagram, dan white space.
- Setiap slide wajib punya visual device yang benar-benar berguna: flow, checklist, comparison, matrix, timeline, dashboard, chat, cards, atau diagram.
- visual_direction harus menjelaskan apa yang digambar.
- design_notes harus menjelaskan komposisi/focal point.

COPY QUALITY BAR:
- Bahasa Indonesia natural, tajam, praktis, tidak sok AI.
- Judul slide 4-12 kata ideal.
- Body 18-45 kata ideal.
- Satu gagasan utama per slide.
- Hindari "di era digital", "AI mengubah segalanya", "jangan ketinggalan", "wajib tahu".
- Jangan bikin clickbait murahan.
- Jangan mengarang testimoni, omzet, klien, statistik, hasil, harga, atau angka performa.
- Angka hanya untuk contoh ilustratif dan harus jelas sebagai contoh.
- Soft selling maksimum 1 slide.
- CTA bervariasi.
- Jangan menyebut crawler, scraping, GitHub, atau pipeline internal.
- Tidak ada auto-upload; semua asset disiapkan untuk upload manual.
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
        fallback_roles = ["HOOK","PROBLEM","INSIGHT","FRAMEWORK","EXAMPLE","MISTAKE","CTA"]
        while len(slides) < SLIDE_COUNT:
            slides.append({
                "role": fallback_roles[len(slides)],
                "title": "Langkah yang paling relevan",
                "body": "Pilih satu tindakan yang bisa langsung dicoba pada proses bisnis yang sedang bermasalah.",
                "visual_direction": "Kartu checklist dengan satu focal point.",
                "design_notes": "Gunakan whitespace luas dan satu aksen visual."
            })
        cleaned.append({
            "date": target_iso,
            "pillar": str(p.get("pillar") or CONTENT_PILLARS[offset % len(CONTENT_PILLARS)]),
            "objective": str(p.get("objective") or "Edukasi"),
            "topic": str(p.get("topic") or ("Tips operasional bisnis hari "+str(offset+1))),
            "hook": str(p.get("hook") or "Bisnis kamu masih melakukan ini manual?"),
            "caption": str(p.get("caption") or "Insight praktis untuk pemilik bisnis Indonesia."),
            "cta": str(p.get("cta") or "Simpan post ini dan bagikan ke tim."),
            "slides": slides,
            "design_style": DESIGN_STYLES[offset % len(DESIGN_STYLES)],
            "content_angle": CONTENT_ANGLES[offset % len(CONTENT_ANGLES)],
        })
    return cleaned

    validate_content_plan(cleaned)
    return cleaned

def validate_content_plan(posts: list[dict]) -> None:
    errors = []
    required_roles = ["HOOK","PROBLEM","INSIGHT","FRAMEWORK","EXAMPLE","MISTAKE","CTA"]
    seen_topics = set()
    if len(posts) != PLAN_DAYS:
        errors.append(f"Expected {PLAN_DAYS} posts, got {len(posts)}.")
    for day, post in enumerate(posts, start=1):
        topic = str(post.get("topic") or "").strip()
        if not topic:
            errors.append(f"Day {day}: missing topic.")
        elif topic.lower() in seen_topics:
            errors.append(f"Day {day}: duplicate topic.")
        seen_topics.add(topic.lower())
        if not str(post.get("pillar") or "").strip():
            errors.append(f"Day {day}: missing content pillar.")
        slides = post.get("slides") or []
        if len(slides) != SLIDE_COUNT:
            errors.append(f"Day {day}: expected {SLIDE_COUNT} slides.")
            continue
        roles = [str(s.get("role") or "").upper().strip() for s in slides]
        if roles != required_roles:
            errors.append(f"Day {day}: invalid slide role sequence {roles}.")
        for slide_no, slide in enumerate(slides, start=1):
            title = str(slide.get("title") or "").strip()
            body = str(slide.get("body") or "").strip()
            visual = str(slide.get("visual_direction") or "").strip()
            if not title or not body or not visual:
                errors.append(f"Day {day} slide {slide_no}: missing content.")
            if not 3 <= len(title.split()) <= 14:
                errors.append(f"Day {day} slide {slide_no}: title length out of range.")
            if not 10 <= len(body.split()) <= 60:
                errors.append(f"Day {day} slide {slide_no}: body length out of range.")
        if len(str(post.get("hook") or "").strip()) < 18:
            errors.append(f"Day {day}: hook too weak.")
        if len(str(post.get("cta") or "").strip()) < 10:
            errors.append(f"Day {day}: CTA too weak.")
    if errors:
        raise ValueError("CONTENT_QUALITY_GATE_FAILED | " + " | ".join(errors[:20]))


def draw_robot(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, pose: int = 0, invert: bool = False):
    s=float(scale)
    outline=NAVY
    face=BLUE if invert else LIGHT_BLUE
    body=WHITE if invert else PALE_BLUE
    accent=CYAN if invert else BLUE_2
    def b(a,b,c,d): return (int(x+a*s),int(y+b*s),int(x+c*s),int(y+d*s))
    draw.rounded_rectangle(b(22,78,178,232),radius=int(28*s),fill=body,outline=outline,width=max(2,int(5*s)))
    draw.rounded_rectangle(b(43,40,157,120),radius=int(24*s),fill=face,outline=outline,width=max(2,int(5*s)))
    draw.line((int(x+100*s),int(y+40*s),int(x+100*s),int(y+10*s)),fill=outline,width=max(2,int(5*s)))
    draw.ellipse(b(94,1,106,13),fill=accent,outline=outline,width=max(1,int(3*s)))
    draw.ellipse(b(67,68,81,82),fill=outline)
    draw.ellipse(b(119,68,133,82),fill=outline)
    draw.rounded_rectangle(b(70,91,130,106),radius=int(7*s),fill=WHITE,outline=outline,width=max(1,int(2*s)))
    draw.rounded_rectangle(b(58,140,142,192),radius=int(12*s),fill=face,outline=outline,width=max(2,int(3*s)))
    draw.rounded_rectangle(b(76,151,124,175),radius=int(7*s),fill=WHITE)
    draw.line((int(x+86*s),int(y+163*s),int(x+114*s),int(y+163*s)),fill=BLUE,width=max(2,int(4*s)))
    p=pose%4
    if p==0:
        draw.line((int(x+22*s),int(y+143*s),int(x-10*s),int(y+110*s)),fill=outline,width=max(2,int(7*s)))
        draw.line((int(x+178*s),int(y+143*s),int(x+208*s),int(y+165*s)),fill=outline,width=max(2,int(7*s)))
    elif p==1:
        draw.line((int(x+22*s),int(y+145*s),int(x-12*s),int(y+145*s)),fill=outline,width=max(2,int(7*s)))
        draw.line((int(x+178*s),int(y+145*s),int(x+208*s),int(y+112*s)),fill=outline,width=max(2,int(7*s)))
    elif p==2:
        draw.line((int(x+30*s),int(y+140*s),int(x-4*s),int(y+80*s)),fill=outline,width=max(2,int(7*s)))
        draw.line((int(x+170*s),int(y+140*s),int(x+204*s),int(y+82*s)),fill=outline,width=max(2,int(7*s)))
    else:
        draw.line((int(x+25*s),int(y+148*s),int(x-4*s),int(y+180*s)),fill=outline,width=max(2,int(7*s)))
        draw.line((int(x+175*s),int(y+148*s),int(x+204*s),int(y+180*s)),fill=outline,width=max(2,int(7*s)))


def add_header(draw, index: int, total: int):
    draw.text((68,48),"SONJAYA",font=font(28,True),fill=NAVY)
    draw.text((860,48),f"{index:02d}/{total:02d}",font=font(24,True),fill=MUTED)
    draw.rounded_rectangle((68,94,250,108),radius=7,fill=LIGHT_BLUE)
    draw.rounded_rectangle((68,94,118+index*18,108),radius=7,fill=BLUE)


def draw_title(draw, text, x, y, max_width, size, fill=INK, max_lines=4):
    fnt=font(size,True)
    for line in wrap_lines(draw,text,fnt,max_width,max_lines):
        draw.text((x,y),line,font=fnt,fill=fill)
        y += int(size*1.16)
    return y


def draw_body(draw, text, x, y, max_width, size=31, fill=MUTED, max_lines=6):
    fnt=font(size)
    for line in wrap_lines(draw,text,fnt,max_width,max_lines):
        draw.text((x,y),line,font=fnt,fill=fill)
        y += int(size*1.42)
    return y


def render_slide(slide: dict, index: int, total: int, topic: str, cover: bool = False, style: str = "BOLD_EDITORIAL", post_day: int = 0) -> Image.Image:
    W,H=1080,1350
    img=Image.new("RGB",(W,H),PALE_BLUE)
    draw=ImageDraw.Draw(img)
    title=str(slide.get("title") or "").strip()
    body=str(slide.get("body") or "").strip()
    visual=str(slide.get("visual_direction") or "").strip()
    notes=str(slide.get("design_notes") or "").strip()

    draw.rounded_rectangle((36,36,W-36,H-36),radius=42,outline=LIGHT_BLUE,width=3)
    add_header(draw,index,total)

    if cover:
        if style=="SPLIT_SCREEN":
            draw.rounded_rectangle((58,158,630,1190),radius=38,fill=WHITE)
            draw.rounded_rectangle((610,158,W-58,1190),radius=38,fill=BLUE)
            draw_robot(draw,710,300,1.16,(post_day+index)%4,True)
            draw.text((92,214),"AI × BUSINESS",font=font(23,True),fill=BLUE)
            draw_title(draw,title,92,275,470,60,INK,5)
            draw_body(draw,body,92,700,460,30,MUTED,6)
        elif style=="DASHBOARD":
            draw.rounded_rectangle((70,165,W-70,1185),radius=40,fill=WHITE)
            draw.rounded_rectangle((102,203,370,267),radius=18,fill=LIGHT_BLUE)
            draw.text((128,222),"PLAYBOOK",font=font(25,True),fill=NAVY)
            draw_robot(draw,805,190,0.82,(post_day+index)%4)
            draw_title(draw,title,110,315,740,57,INK,4)
            draw.rounded_rectangle((110,690,900,990),radius=28,fill=BLUE)
            draw_body(draw,body,150,740,710,32,WHITE,6)
        elif style=="FLOW_DIAGRAM":
            draw.text((92,205),"WORKFLOW",font=font(22,True),fill=BLUE)
            draw_robot(draw,815,195,0.72,(post_day+index)%4)
            draw_title(draw,title,92,275,690,58,INK,4)
            labels=["INPUT","PROCESS","OUTPUT"]
            xs=[110,380,650]
            for k,(x,label) in enumerate(zip(xs,labels)):
                draw.rounded_rectangle((x,700,x+200,790),radius=20,fill=WHITE,outline=LIGHT_BLUE,width=3)
                draw.text((x+34,728),label,font=font(22,True),fill=NAVY)
                if k<2:
                    draw.line((x+200,745,xs[k+1]-20,745),fill=BLUE_2,width=7)
            draw_body(draw,body,115,875,820,30,MUTED,5)
        elif style=="CARD_STACK":
            draw.rounded_rectangle((120,245,930,895),radius=32,fill=LIGHT_BLUE)
            draw.rounded_rectangle((98,220,908,870),radius=32,fill=WHITE,outline=LIGHT_BLUE,width=3)
            draw.rounded_rectangle((76,195,886,845),radius=32,fill=WHITE,outline=LIGHT_BLUE,width=3)
            draw_robot(draw,790,255,0.60,(post_day+index)%4)
            draw.text((122,265),f"CARD {index-1}",font=font(22,True),fill=BLUE)
            draw_title(draw,title,122,335,650,56,INK,4)
            draw_body(draw,body,122,620,700,30,MUTED,6)
        elif style=="TYPE_POSTER":
            draw.text((90,190),"THE SONJAYA NOTE",font=font(22,True),fill=BLUE)
            draw.text((850,188),f"0{index}",font=font(34,True),fill=LIGHT_BLUE)
            draw_robot(draw,770,260,0.72,(post_day+index)%4)
            draw_title(draw,title,90,300,860,68,INK,4)
            draw.rectangle((90,705,260,718),fill=BLUE)
            draw_body(draw,body,90,790,790,31,MUTED,6)
        elif style=="MINIMAL_TECH":
            draw.line((120,205,120,1060),fill=BLUE,width=8)
            for cy in (300,520,740,960):
                draw.ellipse((95,cy,145,cy+50),fill=LIGHT_BLUE,outline=BLUE,width=2)
            draw_robot(draw,780,220,0.66,(post_day+index)%4)
            draw_title(draw,title,180,240,720,58,INK,4)
            draw_body(draw,body,180,610,720,31,MUTED,7)
        else:
            draw.rounded_rectangle((60,155,335,1195),radius=42,fill=BLUE)
            draw_robot(draw,112,760,0.92,(post_day+index)%4,True)
            draw.text((95,210),"AI OPS",font=font(24,True),fill=WHITE)
            draw.text((370,225),"INSIGHT",font=font(22,True),fill=BLUE)
            draw_title(draw,title,370,290,620,60,INK,5)
            draw.rounded_rectangle((370,715,940,1015),radius=30,fill=WHITE,outline=LIGHT_BLUE,width=3)
            draw_body(draw,body,410,765,490,31,INK,7)
    else:
        if style=="SPLIT_SCREEN":
            draw.rounded_rectangle((74,190,610,1170),radius=34,fill=BLUE)
            draw.rounded_rectangle((590,190,1006,1170),radius=34,fill=WHITE,outline=LIGHT_BLUE,width=3)
            draw_robot(draw,690,330,0.72,(post_day+index)%4)
            draw_title(draw,title,105,250,430,54,WHITE,5)
            draw_body(draw,body,105,640,390,29,WHITE,8)
        elif style=="DASHBOARD":
            draw.rounded_rectangle((74,185,1006,1170),radius=34,fill=WHITE)
            draw.text((108,225),"FIELD NOTE",font=font(22,True),fill=BLUE)
            draw_robot(draw,825,220,0.58,(post_day+index)%4)
            draw_title(draw,title,108,310,760,56,INK,4)
            draw.line((108,625,930,625),fill=LIGHT_BLUE,width=5)
            draw_body(draw,body,108,680,790,31,INK,7)
            draw.rounded_rectangle((108,1010,500,1100),radius=18,fill=PALE_BLUE,outline=LIGHT_BLUE,width=2)
            draw.text((135,1038),"Visual cue",font=font(19,True),fill=BLUE)
        elif style=="FLOW_DIAGRAM":
            draw.rounded_rectangle((74,185,1006,1170),radius=34,fill=WHITE)
            draw.text((108,225),"WORKFLOW",font=font(22,True),fill=BLUE)
            draw_robot(draw,820,215,0.58,(post_day+index)%4)
            draw_title(draw,title,108,300,720,55,INK,4)
            lines=wrap_lines(draw,body,font(30),760,7)
            y=650
            for n,line in enumerate(lines,1):
                draw.rounded_rectangle((110,y-4,165,y+44),radius=13,fill=BLUE)
                draw.text((128,y+5),str(n),font=font(20,True),fill=WHITE)
                draw.text((190,y+1),line,font=font(29),fill=INK)
                y+=52
        elif style=="CARD_STACK":
            draw.rounded_rectangle((120,260,930,920),radius=32,fill=LIGHT_BLUE)
            draw.rounded_rectangle((96,235,906,895),radius=32,fill=WHITE,outline=LIGHT_BLUE,width=3)
            draw.rounded_rectangle((72,210,882,870),radius=32,fill=WHITE,outline=LIGHT_BLUE,width=3)
            draw_robot(draw,785,265,0.58,(post_day+index)%4)
            draw_title(draw,title,118,350,660,55,INK,4)
            draw_body(draw,body,118,650,700,30,MUTED,7)
        elif style=="TYPE_POSTER":
            draw.text((100,210),f"0{index}",font=font(31,True),fill=BLUE)
            draw_title(draw,title,100,285,850,60,INK,4)
            draw.rectangle((100,650,280,664),fill=BLUE)
            draw_body(draw,body,100,730,790,31,MUTED,7)
            draw_robot(draw,790,930,0.60,(post_day+index)%4,True)
        elif style=="MINIMAL_TECH":
            draw.line((120,210,120,1070),fill=BLUE,width=8)
            draw_robot(draw,790,215,0.58,(post_day+index)%4)
            draw_title(draw,title,185,250,720,56,INK,4)
            draw_body(draw,body,185,620,700,30,MUTED,8)
        else:
            draw.rounded_rectangle((74,185,1006,1170),radius=34,fill=WHITE,outline=LIGHT_BLUE,width=3)
            draw.text((110,225),"INSIGHT",font=font(22,True),fill=BLUE)
            draw_robot(draw,805,210,0.58,(post_day+index)%4)
            draw_title(draw,title,110,330,760,58,INK,4)
            draw.rounded_rectangle((110,720,930,1030),radius=28,fill=BLUE)
            draw_body(draw,body,150,765,730,31,WHITE,7)

    # Footer changes across slide positions so the deck feels designed, not repeated.
    footer_text = ["SWIPE →","SAVE THIS","TRY IT TODAY","CHECKLIST","EXAMPLE","AVOID THIS","COMMENT / DM"][min(index-1,6)]
    draw.rounded_rectangle((74,1195,1006,1230),radius=16,fill=BLUE)
    draw.text((98,1202),footer_text,font=font(17,True),fill=WHITE)
    draw.text((68,1265),"SONJAYA • AI-POWERED REMOTE BUSINESS SUPPORT",font=font(19,True),fill=MUTED)
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
            style=post.get("design_style","BOLD_EDITORIAL"),
            post_day=idx,
        )
        slide_path = folder / f"{idx:02d}.png"
        image.save(slide_path, format="PNG", optimize=True)
        publish_path = folder / f"{idx:02d}.jpg"
        image.convert("RGB").save(publish_path, format="JPEG", quality=92, optimize=True, progressive=True)
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
    post["publish_image_urls"] = [
        f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{encoded_dir}/{i+1:02d}.jpg"
        for i, _ in enumerate(post["slides"])
    ]
    post["slides_json"] = json.dumps(
        [
            {
                "slide": i + 1,
                "url": f"https://github.com/{REPO}/blob/{BRANCH}/{encoded_dir}/{i+1:02d}.png",
                "publish_url": f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{encoded_dir}/{i+1:02d}.jpg",
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
            "platform": "Instagram",
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
            "status": "READY_FOR_MANUAL_UPLOAD",
            "publish_mode": "MANUAL_UPLOAD",
            "content_pillar": p.get("pillar", ""),
            "script": "\n\n".join(
                [
                    f"Slide {i+1} [{s.get('role','')}]\nJudul: {s.get('title','')}\nIsi: {s.get('body','')}\nVisual: {s.get('visual_direction','')}\nCatatan desain: {s.get('design_notes','')}"
                    for i, s in enumerate(p.get("slides", [])[:SLIDE_COUNT])
                ]
            ),
            "slide_urls": p.get("publish_image_urls", []),
            "catatan": "Content Studio | asset dan script siap untuk upload manual.",
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


def write_publish_manifest(posts: list[dict]) -> None:
    manifest = {
        "generated_at": datetime.now(WIB).isoformat(),
        "posts": [
            {
                "date": p["date"],
                "manual_upload_platforms": ["instagram", "tiktok"],
                "title": p["topic"],
                "caption": p["caption"],
                "image_urls": p.get("publish_image_urls", []),
                "topic": p["topic"],
            }
            for p in posts
        ],
    }
    Path("publish_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    plans = generate_plan()
    for post in plans:
        build_carousel(post)
    write_publish_manifest(plans)
    print("CONTENT_PLANS", len(plans))
    print("SHEET", json.dumps(push_plans(plans), ensure_ascii=False))
    print("CAROUSELS", sum(1 for p in plans if p.get("carousel_pdf_url")))
