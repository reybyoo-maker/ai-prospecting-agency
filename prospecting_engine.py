from __future__ import annotations
import hashlib, os, re, time, json
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from google import genai
from google.genai import types
from service_catalog import catalog_text

WIB = timezone(timedelta(hours=7))
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
SHEET_WEBHOOK_URL = os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]
MAX_PER_RUN = int(os.getenv("MAX_PER_RUN", "60"))
MAX_AI_PER_RUN = int(os.getenv("MAX_AI_PER_RUN", "40"))
SEND_LIMIT = int(os.getenv("SEND_LIMIT", "20"))

CITIES = ["Jakarta","Bandung","Bekasi","Depok","Tangerang","Bogor","Semarang","Yogyakarta","Surabaya","Malang","Medan","Makassar","Denpasar","Palembang","Pekanbaru","Batam","Balikpapan","Samarinda","Pontianak","Banjarmasin"]
NICHES = ["agency","property","clinic","dental clinic","beauty clinic","gym","fitness","salon","barbershop","restaurant","cafe","bakery","catering","fashion","hotel","villa","travel","wedding organizer","event organizer","photography","car rental","car workshop","contractor","architect","interior design","education","course","tutor","pet shop","veterinary","florist","retail","distributor","supplier","online shop","local business"]

EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+\s*(?:@|\[at\]|\(at\))\s*[A-Za-z0-9.-]+\s*(?:\.|\[dot\]|\(dot\))\s*[A-Za-z]{2,}(?![\w.-])", re.I)
BLOCKED = ("noreply@","no-reply@","donotreply@","do-not-reply@","example@")

def norm(s): return re.sub(r"\s+"," ",str(s or "")).strip()
def normalize_email(s):
    s=re.sub(r"\s+","",str(s or "").lower().strip())
    return s.replace("[at]","@").replace("(at)","@").replace("[dot]",".").replace("(dot)",".")
def extract_email(text):
    for x in EMAIL_RE.findall(text or ""):
        e=normalize_email(x)
        if "@" in e and not e.startswith(BLOCKED): return e
    return ""

def fetch(url):
    if not url.startswith(("http://","https://")): return ""
    try:
        r=requests.get(url,headers={"User-Agent":"Mozilla/5.0 SonjayaAI/2.0"},timeout=12,allow_redirects=True)
        r.raise_for_status()
        return r.text[:300000]
    except Exception: return ""

def page_evidence(url):
    html=fetch(url)
    if not html: return "", ""
    soup=BeautifulSoup(html,"html.parser")
    text=norm(soup.get_text(" ",strip=True))[:9000]
    return text, extract_email(text+" "+html)

def extract_social(text):
    m=re.search(r"https?://(?:www\.)?(?:instagram\.com|tiktok\.com)/[^\s<>"]+",str(text or ""),re.I)
    return m.group(0) if m else ""

def search_queries():
    now=datetime.now(WIB)
    slot=(now.timetuple().tm_yday*24+now.hour)//2
    pool=[f'"{n}" "{c}" business contact email' for c in CITIES for n in NICHES]
    return [pool[(slot*12+i)%len(pool)] for i in range(12)]

def discover():
    found={}
    with DDGS(timeout=20) as ddgs:
        for qi,q in enumerate(search_queries(),1):
            try:
                for r in ddgs.text(q,region="id-id",safesearch="moderate",max_results=8):
                    url=norm(r.get("href") or r.get("url") or r.get("link"))
                    title=norm(r.get("title"))
                    snippet=norm(r.get("body") or r.get("snippet") or r.get("description"))
                    if not url or any(x in url.lower() for x in ("instagram.com","facebook.com","tiktok.com","linkedin.com")): continue
                    page_text,email=page_evidence(url)
                    evidence=norm(f"{title} {snippet} {page_text[:4000]}")
                    if not email: email=extract_email(evidence)
                    if not email: continue
                    if email.lower() in found: continue
                    found[email.lower()]={
                        "recipient_email":email,
                        "email_source_url":url,
                        "website_url":url,
                        "social_url":extract_social(page_text),
                        "search_title":title,
                        "public_evidence":evidence[:7000],
                        "source_query":q,
                    }
                    if len(found)>=MAX_PER_RUN: return list(found.values())
            except Exception as e:
                print("SEARCH_ERROR",qi,type(e).__name__,e)
            time.sleep(1.5)
    return list(found.values())

def score_one(lead):
    client=genai.Client(api_key=GEMINI_API_KEY)
    schema={"type":"object","properties":{
      "business_name":{"type":"string"},"city":{"type":"string"},"niche":{"type":"string"},
      "score":{"type":"integer","minimum":0,"maximum":100},"priority":{"type":"string"},
      "detected_need":{"type":"string"},"recommended_service":{"type":"string"},
      "pain_point":{"type":"string"},"personal_hook":{"type":"string"},
      "subject":{"type":"string"},"body":{"type":"string"}
    },"required":["business_name","city","niche","score","priority","detected_need","recommended_service","pain_point","personal_hook","subject","body"]}
    prompt=f"""
Kamu adalah sales-research AI untuk Sonjaya Remote Business Services.
Tujuan: menawarkan pekerjaan remote yang nyata kepada bisnis Indonesia berdasarkan bukti publik.

Service catalog:
{catalog_text()}

Lead:
{json.dumps(lead,ensure_ascii=False)}

Aturan:
- Temukan kebutuhan yang terlihat dari evidence sebelum memilih layanan.
- Jangan mengarang karyawan, omzet, pelanggan, harga, followers, masalah internal, atau fakta lain.
- recommended_service HARUS satu service key dari katalog.
- Buat email cold outreach bahasa Indonesia yang singkat, personal, sopan, dan tidak berlebihan.
- Nyatakan bahwa pekerjaan dapat dilakukan remote oleh tim kecil yang memakai AI sebagai alat bantu dan tetap diawasi manusia.
- Minta langkah kecil seperti membalas email untuk melihat contoh.
- Sertakan kalimat opt-out persis: "Jika email ini tidak relevan, balas UNSUBSCRIBE dan kami tidak akan menghubungi lagi."
- Jangan menyebut sistem crawler, scraping, atau "AI agent" sebagai alasan menghubungi mereka.
Return JSON only.
"""
    cfg=types.GenerateContentConfig(response_mime_type="application/json",response_json_schema=schema,temperature=0.25,max_output_tokens=1500)
    last=None
    for attempt in range(3):
        try:
            r=client.models.generate_content(model=GEMINI_MODEL,contents=prompt,config=cfg)
            if getattr(r,"parsed",None): return dict(r.parsed)
            return json.loads(r.text)
        except Exception as e:
            last=e
            time.sleep(3*(attempt+1))
    raise RuntimeError(str(last))

def sheet_call(action, **payload):
    r=requests.post(SHEET_WEBHOOK_URL,json={"token":WEBHOOK_TOKEN,"action":action,**payload},timeout=90)
    r.raise_for_status()
    data=r.json()
    if not data.get("ok"): raise RuntimeError(data.get("error","Sheets action failed"))
    return data

def make_id(email): return hashlib.sha1(email.lower().encode()).hexdigest()[:12]

def run():
    leads=discover()
    print("DISCOVERY",len(leads))
    rows=[]
    for i,lead in enumerate(leads[:MAX_AI_PER_RUN]):
        try:
            ai=score_one(lead)
            score=int(ai["score"])
            rows.append({
              "lead_id":make_id(lead["recipient_email"]),
              "tanggal_ditemukan":datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"),
              "nama_bisnis":ai["business_name"],
              "recipient_email":lead["recipient_email"],
              "email_source_url":lead["email_source_url"],
              "website_url":lead["website_url"],
              "social_url":lead["social_url"],
              "kota":ai["city"],"kategori":ai["niche"],
              "bukti_publik":lead["public_evidence"],
              "skor":score,"alasan":ai["personal_hook"],
              "pain_point":ai["pain_point"],
              "detected_need":ai["detected_need"],
              "recommended_service":ai["recommended_service"],
              "subject":f"[SJ-{make_id(lead['recipient_email'])}] {ai['subject']}",
              "body":ai["body"],
              "status":"READY" if score>=75 else "REVIEW",
              "catatan":"public business email"
            })
        except Exception as e:
            print("AI_ERROR",i,type(e).__name__,e)
    if rows: print("INGEST",sheet_call("ingest",rows=rows))
    try: print("SEND",sheet_call("send_queue",limit=SEND_LIMIT))
    except Exception as e: print("SEND_ERROR",e)
    try: print("REPLIES",sheet_call("scan_replies",limit=20))
    except Exception as e: print("REPLY_ERROR",e)

if __name__=="__main__": run()
