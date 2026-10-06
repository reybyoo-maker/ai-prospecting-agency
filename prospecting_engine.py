from __future__ import annotations
import hashlib, os, re, time, json
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from google import genai
from google.genai import types
from service_catalog import catalog_text, SERVICES

WIB = timezone(timedelta(hours=7))
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
SHEET_WEBHOOK_URL = os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]
MAX_PER_RUN = int(os.getenv("MAX_PER_RUN", "60"))
MAX_AI_PER_RUN = int(os.getenv("MAX_AI_PER_RUN", "40"))
SEND_LIMIT = int(os.getenv("SEND_LIMIT", "20"))
SEARCH_BACKENDS = os.getenv("SEARCH_BACKENDS", "google,brave,bing,duckduckgo").strip()
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "25"))
QUERY_PAUSE = float(os.getenv("QUERY_PAUSE", "0.6"))
CONTACT_PATHS = (
    "/contact", "/kontak", "/hubungi-kami", "/hubungi",
    "/about", "/tentang-kami", "/tentang"
)


CITIES = [
    "Jakarta","Bandung","Bekasi","Depok","Tangerang","Bogor","Semarang","Yogyakarta",
    "Surabaya","Malang","Medan","Makassar","Denpasar","Palembang","Pekanbaru","Batam",
    "Balikpapan","Samarinda","Pontianak","Banjarmasin","Cimahi","Cirebon","Karawang",
    "Tasikmalaya","Garut","Solo","Sidoarjo","Kediri","Madiun","Jember","Padang",
    "Banda Aceh","Lampung","Mataram","Kupang","Manado","Palu"
]

NICHES = [
    "agency","property","real estate","clinic","dental clinic","beauty clinic","gym",
    "fitness","salon","barbershop","restaurant","cafe","bakery","catering","fashion",
    "hotel","villa","travel","wedding organizer","event organizer","photography",
    "car rental","car workshop","contractor","architect","interior design","education",
    "course","tutor","pet shop","veterinary","florist","retail","distributor","supplier",
    "online shop","local business","law firm","accounting firm","consultant","manufacturer",
    "wholesaler","restaurant group","school","university","studio","spa","laundry"
]

SOURCE_TEMPLATES = [
    '"{n}" "{c}" email',
    '"{n}" "{c}" "hubungi kami"',
    '"{n}" "{c}" "contact us"',
    '"{n}" "{c}" "kontak"',
    '"{n}" "{c}" "gmail.com"',
    '"{n}" "{c}" "admin@"',
    '"{n}" "{c}" "info@"',
    '"{n}" "{c}" "marketing@"',
    '"{n}" "{c}" "sales@"',
    '"{n}" "{c}" "whatsapp"',
    '"{n}" "{c}" "{n}" "email"',
    '"{n}" "{c}" company profile',
    '"{n}" "{c}" business profile',
    '"{n}" "{c}" website contact'
]

EMAIL_RE = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+\s*(?:@|\[at\]|\(at\))\s*"
    r"[A-Za-z0-9.-]+\s*(?:\.|\[dot\]|\(dot\))\s*[A-Za-z]{2,}(?![\w.-])", re.I
)
BLOCKED = ("noreply@","no-reply@","donotreply@","do-not-reply@","example@")
SERVICE_KEYS={x["key"] for x in SERVICES}

def fallback_city(lead):
    q=str(lead.get("source_query",""))
    for city in CITIES:
        if city.lower() in q.lower():
            return city
    return ""

def fallback_niche(lead):
    q=(str(lead.get("source_query",""))+" "+str(lead.get("public_evidence",""))).lower()
    for niche in sorted(NICHES,key=len,reverse=True):
        if niche.lower() in q:
            return niche
    return ""

def fallback_service(evidence):
    low=str(evidence or "").lower()
    best=None
    best_score=0
    for s in SERVICES:
        score=sum(1 for sig in s["signals"] if sig.lower() in low)
        if score>best_score:
            best_score=score
            best=s
    return best or SERVICES[0]

def clean_ai_result(ai, lead):
    ai=dict(ai or {})
    service_key=str(ai.get("recommended_service") or "").strip()
    service=fallback_service(lead.get("public_evidence","")) if service_key not in SERVICE_KEYS else next(x for x in SERVICES if x["key"]==service_key)
    business=str(ai.get("business_name") or "").strip()
    if not business:
        business=norm(lead.get("search_title")) or norm(lead.get("recipient_email","").split("@")[0]).replace("."," ").title()
    city=str(ai.get("city") or "").strip() or fallback_city(lead)
    niche=str(ai.get("niche") or "").strip() or fallback_niche(lead)
    need=str(ai.get("detected_need") or "").strip()
    pain=str(ai.get("pain_point") or "").strip()
    hook=str(ai.get("personal_hook") or "").strip()
    subject=str(ai.get("subject") or "").strip()
    body=str(ai.get("body") or "").strip()
    if not need:
        need="Kebutuhan belum dapat dipastikan sepenuhnya dari bukti publik yang tersedia."
    if not pain:
        pain="Belum ada pain point internal yang dapat dipastikan dari sumber publik."
    if not hook:
        hook="Kami melihat aktivitas/informasi publik yang relevan dengan area "+service["name"].lower()+"."
    if not subject:
        subject="Bantuan remote untuk "+business+" — "+service["name"]
    if not body:
        body=("Halo tim "+business+",\n\n"
              "Saya melihat ada area yang mungkin bisa dibantu secara remote, yaitu "+service["pitch"]+"\n\n"
              "Kalau relevan, saya bisa kirim contoh alur kerja singkat untuk dipertimbangkan.\n\n"
              "Jika email ini tidak relevan, balas UNSUBSCRIBE dan kami tidak akan menghubungi lagi.\n\n"
              "Salam,\nRey\nSonjaya Remote Business Services")
    return {
        "business_name":business,"city":city,"niche":niche,
        "score":max(0,min(100,int(ai.get("score") or 0))),
        "priority":str(ai.get("priority") or ""),
        "detected_need":need,"recommended_service":service["key"],
        "pain_point":pain,"personal_hook":hook,"subject":subject[:220],"body":body
    }


def norm(s):
    return re.sub(r"\s+"," ",str(s or "")).strip()

def normalize_email(s):
    s=re.sub(r"\s+","",str(s or "").lower().strip())
    return s.replace("[at]","@").replace("(at)","@").replace("[dot]",".").replace("(dot)",".")

def extract_email(text):
    for x in EMAIL_RE.findall(text or ""):
        e=normalize_email(x)
        if "@" in e and not e.startswith(BLOCKED):
            return e
    return ""

def is_social_url(url):
    low=(url or "").lower()
    return any(x in low for x in ("instagram.com","facebook.com","tiktok.com","linkedin.com"))

def fetch(url):
    if not url.startswith(("http://","https://")):
        return ""
    try:
        r=requests.get(
            url,
            headers={"User-Agent":"Mozilla/5.0 SonjayaAI/2.1"},
            timeout=12,
            allow_redirects=True
        )
        r.raise_for_status()
        return r.text[:300000]
    except Exception:
        return ""

def page_evidence(url):
    html=fetch(url)
    if not html:
        return "", ""
    soup=BeautifulSoup(html,"html.parser")
    text=norm(soup.get_text(" ",strip=True))[:9000]
    return text, extract_email(text+" "+html)

def extract_social(text):
    m=re.search(
        r'https?://(?:www\.)?(?:instagram\.com|tiktok\.com|linkedin\.com|facebook\.com)/[^\s<>"]+',
        str(text or ""),
        re.I
    )
    return m.group(0) if m else ""

def search_queries():
    now=datetime.now(WIB)
    slot=(now.timetuple().tm_yday*24+now.hour)//2
    pool=[
        template.format(n=n,c=c)
        for c in CITIES
        for n in NICHES
        for template in SOURCE_TEMPLATES
    ]
    count=int(os.getenv("QUERIES_PER_RUN","24"))
    start=(slot*count)%len(pool)
    return [pool[(start+i)%len(pool)] for i in range(count)]

def candidate_urls(url):
    if not url or is_social_url(url):
        return []
    parsed=urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return []
    base=f"{parsed.scheme}://{parsed.netloc}"
    return [url, *[base+p for p in CONTACT_PATHS]]

def enrich_candidate(url, evidence):
    combined=norm(evidence)
    found_email=extract_email(combined)
    best_url=url
    if found_email:
        return combined, found_email, best_url
    for target in candidate_urls(url):
        page_text,page_email=page_evidence(target)
        if page_text:
            combined=norm(f"{combined} {page_text[:5000]}")
        if page_email:
            return combined, page_email, target
        time.sleep(0.15)
    return combined, "", best_url

def search_with_fallback(ddgs, query):
    backends=[x.strip() for x in SEARCH_BACKENDS.split(",") if x.strip()]
    last_error=None
    for backend in backends:
        try:
            results=ddgs.text(
                query,
                region="id-id",
                safesearch="moderate",
                max_results=10,
                backend=backend,
            )
            if results:
                return results, backend
        except Exception as e:
            last_error=e
            print("BACKEND_ERROR",backend,type(e).__name__,e)
    if last_error:
        raise last_error
    return [], "none"

def discover():
    found={}
    queries=search_queries()
    stats={"queries":len(queries),"query_errors":0,"backend_successes":0,"candidates":0,"emails":0}
    with DDGS(timeout=SEARCH_TIMEOUT) as ddgs:
        for qi,q in enumerate(queries,1):
            try:
                results,backend=search_with_fallback(ddgs,q)
                stats["backend_successes"]+=1
                for r in results:
                    stats["candidates"]+=1
                    url=norm(r.get("href") or r.get("url") or r.get("link"))
                    title=norm(r.get("title"))
                    snippet=norm(r.get("body") or r.get("snippet") or r.get("description"))
                    if not url:
                        continue

                    evidence=norm(f"{title} {snippet}")
                    evidence,email,email_url=enrich_candidate(url,evidence)
                    if not email:
                        continue
                    stats["emails"]+=1
                    key=email.lower()
                    if key in found:
                        continue

                    social=extract_social(evidence)
                    found[key]={
                        "recipient_email":email,
                        "email_source_url":email_url or url,
                        "website_url":"" if is_social_url(url) else url,
                        "social_url":social,
                        "search_title":title,
                        "public_evidence":evidence[:7000],
                        "source_query":q,
                        "search_backend":backend,
                    }
                    if len(found)>=MAX_PER_RUN:
                        print("DISCOVERY_STATS",json.dumps(stats,ensure_ascii=False))
                        return list(found.values())
            except Exception as e:
                stats["query_errors"]+=1
                print("SEARCH_ERROR",qi,type(e).__name__,e)
            time.sleep(QUERY_PAUSE)
    print("DISCOVERY_STATS",json.dumps(stats,ensure_ascii=False))
    return list(found.values())

def score_one(lead):
    client=genai.Client(api_key=GEMINI_API_KEY)
    schema={"type":"object","properties":{
      "business_name":{"type":"string"},"city":{"type":"string"},"niche":{"type":"string"},
      "score":{"type":"integer","minimum":0,"maximum":100},"priority":{"type":"string"},
      "detected_need":{"type":"string"},"recommended_service":{"type":"string"},
      "pain_point":{"type":"string"},"personal_hook":{"type":"string"},
      "subject":{"type":"string"},"body":{"type":"string"}
    },"required":[
      "business_name","city","niche","score","priority","detected_need","recommended_service",
      "pain_point","personal_hook","subject","body"
    ]}
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
- Buat email cold outreach bahasa Indonesia yang singkat, personal, sopan, dan relevan.
- Nyatakan bahwa pekerjaan dapat dilakukan remote oleh tim kecil yang memakai AI sebagai alat bantu dan tetap diawasi manusia.
- Minta langkah kecil seperti membalas email untuk melihat contoh.
- Sertakan kalimat opt-out persis: "Jika email ini tidak relevan, balas UNSUBSCRIBE dan kami tidak akan menghubungi lagi."
- Jangan menyebut crawler, scraping, atau teknik discovery sebagai alasan menghubungi mereka.
- Jangan menjanjikan hasil bisnis.
Return JSON only.
"""
    cfg=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=schema,
        temperature=0.25,
        max_output_tokens=1500
    )
    last=None
    for attempt in range(3):
        try:
            r=client.models.generate_content(model=GEMINI_MODEL,contents=prompt,config=cfg)
            if getattr(r,"parsed",None):
                return dict(r.parsed)
            return json.loads(r.text)
        except Exception as e:
            last=e
            time.sleep(3*(attempt+1))
    raise RuntimeError(str(last))

def sheet_call(action,**payload):
    last_error=None
    for attempt in range(3):
        try:
            r=requests.post(
                SHEET_WEBHOOK_URL,
                json={"token":WEBHOOK_TOKEN,"action":action,**payload},
                timeout=90
            )
            if r.status_code == 404:
                raise RuntimeError(
                    "SHEET_WEBHOOK_404: Google Apps Script Web App URL in GitHub Secret "
                    "is unavailable. Update SHEET_WEBHOOK_URL with the current /exec deployment URL."
                )
            if r.status_code in (429,500,502,503,504):
                last_error=RuntimeError(f"Sheets HTTP {r.status_code}")
                time.sleep(2*(attempt+1))
                continue
            r.raise_for_status()
            data=r.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("error","Sheets action failed"))
            return data
        except Exception as e:
            last_error=e
            if attempt < 2:
                time.sleep(2*(attempt+1))
                continue
            raise last_error

def make_id(email):
    return hashlib.sha1(email.lower().encode()).hexdigest()[:12]

def run():
    leads=discover()
    print("DISCOVERY",len(leads))
    rows=[]
    for i,lead in enumerate(leads[:MAX_AI_PER_RUN]):
        try:
            ai=clean_ai_result(score_one(lead),lead)
            score=int(ai["score"])
            rows.append({
              "lead_id":make_id(lead["recipient_email"]),
              "tanggal_ditemukan":datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"),
              "nama_bisnis":ai["business_name"],
              "recipient_email":lead["recipient_email"],
              "email_source_url":lead["email_source_url"],
              "website_url":lead["website_url"],
              "social_url":lead["social_url"],
              "kota":ai["city"] or fallback_city(lead) or "Tidak diketahui dari evidence publik",
              "kategori":ai["niche"] or fallback_niche(lead) or "Tidak diketahui dari evidence publik",
              "bukti_publik":lead["public_evidence"],
              "skor":score,
              "alasan":ai["personal_hook"],
              "pain_point":ai["pain_point"],
              "detected_need":ai["detected_need"],
              "recommended_service":ai["recommended_service"],
              "subject":f"[SJ-{make_id(lead['recipient_email'])}] {ai['subject']}"[:245],
              "body":ai["body"],
              "status":"READY" if score>=75 else "REVIEW",
              "catatan":"public business email; source="+lead.get("search_backend","unknown")+"; initial email requires MANUAL SEND"
            })
        except Exception as e:
            print("AI_ERROR",i,type(e).__name__,e)
    if rows:
        print("INGEST",sheet_call("ingest",rows=rows))
    print("SEND", "DISABLED — initial email is manual only in Google Sheets")
    try:
        print("REPLIES",sheet_call("scan_replies",limit=20))
    except Exception as e:
        print("REPLY_ERROR",e)
    try:
        print("FOLLOWUPS",sheet_call("process_followups",limit=5))
    except Exception as e:
        print("FOLLOWUP_ERROR",e)

if __name__=="__main__":
    run()
