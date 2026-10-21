from __future__ import annotations
import base64, email, hashlib, hmac, imaplib, json, os, re, smtplib, ssl, time
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from email.policy import default
from email.utils import formataddr, make_msgid, parsedate_to_datetime, parseaddr
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet, InvalidToken
from ddgs import DDGS
from google import genai
from google.genai import types
from service_catalog import catalog_text, SERVICES

WIB = timezone(timedelta(hours=7))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
DASHBOARD_INGEST_URL = os.getenv(
    "DASHBOARD_INGEST_URL",
    "https://aigrowth-owner-dashboard.reybyoo.workers.dev/api/ingest/scrape",
).strip()
INGEST_TOKEN = os.getenv("INGEST_TOKEN", "").strip()
MAX_PER_RUN = int(os.getenv("MAX_PER_RUN") or "80")
MAX_AI_PER_RUN = int(os.getenv("MAX_AI_PER_RUN") or "60")
MAX_DAILY_SENDS = int(os.getenv("MAX_DAILY_SENDS") or "20")
MAX_SENDS_PER_RUN = int(os.getenv("MAX_SENDS_PER_RUN") or "20")
MIN_SCORE_TO_SEND = int(os.getenv("MIN_SCORE_TO_SEND") or "75")
ENABLE_AUTO_EMAIL = os.getenv("ENABLE_AUTO_EMAIL", "false").strip().lower() in ("1", "true", "yes", "on")
CAMPAIGN_NAME = os.getenv("CAMPAIGN_NAME", "aigrowth-prospecting").strip()
STATE_PATH = Path(os.getenv("PROSPECTING_STATE_PATH", "runtime/prospecting-state.enc"))
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT") or "465")
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = (os.getenv("SMTP_FROM") or SMTP_USERNAME).strip()
SMTP_REPLY_TO = (os.getenv("SMTP_REPLY_TO") or SMTP_FROM).strip()
IMAP_HOST = (os.getenv("IMAP_HOST") or "imap.gmail.com").strip()
IMAP_PORT = int(os.getenv("IMAP_PORT") or "993")
IMAP_USERNAME = (os.getenv("IMAP_USERNAME") or SMTP_USERNAME).strip()
IMAP_PASSWORD = (os.getenv("IMAP_PASSWORD") or SMTP_PASSWORD).strip()
AGENCY_NAME = "Sonjaya Remote Business Services"
SEARCH_BACKENDS = os.getenv("SEARCH_BACKENDS", "google,brave,bing,duckduckgo").strip()
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT") or "25")
QUERY_PAUSE = float(os.getenv("QUERY_PAUSE") or "0.6")
CONTACT_PATHS = ("/contact", "/kontak", "/hubungi-kami", "/hubungi", "/about", "/tentang-kami", "/tentang")
MAX_CRAWL_PER_QUERY = int(os.getenv("MAX_CRAWL_PER_QUERY") or "2")
MAX_EMAIL_RESULTS_PER_QUERY = int(os.getenv("MAX_EMAIL_RESULTS_PER_QUERY") or "6")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?62|0)(?:[\s().-]*\d){8,14}(?!\w)")


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
PORTFOLIO_URL = "https://agencyai.reybyoo.workers.dev/"
AUTOMATION_OFFER = "Saya menawarkan jasa pembuatan otomasi workflow menggunakan n8n yang dirancang berjalan 24/7 sesuai kebutuhan operasional bisnis."

def add_portfolio_offer(body):
    body = str(body or "").strip()
    if not re.search(r"\bn8n\b", body, re.I) or not re.search(r"24\s*/\s*7", body):
        body = (body + "\n\n" if body else "") + AUTOMATION_OFFER
    if PORTFOLIO_URL not in body:
        body = (body + "\n\n" if body else "") + "Silakan cek portofolio saya di: " + PORTFOLIO_URL
    return body

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
    body = add_portfolio_offer(body)
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
            timeout=8,
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

def extract_phone(text):
    """Extract a likely public business phone number from scraped evidence."""
    for match in PHONE_RE.findall(str(text or "")):
        digits = re.sub(r"\D", "", match)
        if digits.startswith("62") and len(digits) >= 10:
            return "+" + digits
        if digits.startswith("0") and 9 <= len(digits) <= 14:
            return digits
    return ""


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
    return [url, *[base+p for p in CONTACT_PATHS[:2]]]

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

def direct_html_search(query):
    """Fallback search using public HTML pages when DDGS providers return no results."""
    providers = [
        ("bing_html", "https://www.bing.com/search", {"q": query, "count": 10, "setlang": "id-id"}),
        ("duckduckgo_html", "https://html.duckduckgo.com/html/", {"q": query}),
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/150 Safari/537.36"}
    for backend, endpoint, params in providers:
        try:
            r=requests.get(endpoint, params=params, headers=headers, timeout=SEARCH_TIMEOUT, allow_redirects=True)
            if r.status_code >= 400:
                continue
            soup=BeautifulSoup(r.text,"html.parser")
            results=[]
            if backend=="bing_html":
                for item in soup.select("li.b_algo")[:10]:
                    a=item.select_one("h2 a")
                    if not a or not a.get("href"): continue
                    sn=item.select_one(".b_caption p")
                    results.append({"title":norm(a.get_text(" ",strip=True)),"href":a.get("href"),"body":norm(sn.get_text(" ",strip=True) if sn else "")})
            else:
                for item in soup.select(".result")[:10]:
                    a=item.select_one(".result__a")
                    if not a or not a.get("href"): continue
                    sn=item.select_one(".result__snippet")
                    results.append({"title":norm(a.get_text(" ",strip=True)),"href":a.get("href"),"body":norm(sn.get_text(" ",strip=True) if sn else "")})
            if results:
                return results, backend
        except Exception as e:
            print("DIRECT_SEARCH_ERROR",backend,type(e).__name__,e)
    return [], "none"

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
    direct_results,direct_backend=direct_html_search(query)
    if direct_results:
        return direct_results,direct_backend
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
                crawl_count=0
                email_results=0
                for r in results:
                    stats["candidates"]+=1
                    url=norm(r.get("href") or r.get("url") or r.get("link"))
                    title=norm(r.get("title"))
                    snippet=norm(r.get("body") or r.get("snippet") or r.get("description"))
                    if not url:
                        continue

                    evidence=norm(f"{title} {snippet}")
                    email=extract_email(evidence)
                    email_url=url
                    if not email and crawl_count < MAX_CRAWL_PER_QUERY and not is_social_url(url):
                        crawl_count+=1
                        evidence,email,email_url=enrich_candidate(url,evidence)
                    if not email:
                        continue
                    stats["emails"]+=1
                    email_results+=1
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
                    if email_results >= MAX_EMAIL_RESULTS_PER_QUERY:
                        break
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
- recommended_service HARUS satu service key dari katalog; jangan menawarkan layanan lain di luar katalog.
- Fokus layanan yang dijual adalah otomasi workflow menggunakan n8n yang dirancang berjalan 24/7 sesuai kebutuhan operasional bisnis.
- Buat email cold outreach bahasa Indonesia yang singkat, personal, sopan, dan relevan.
- Jelaskan manfaat otomasi hanya sejauh didukung evidence; jangan menjanjikan hasil atau uptime 100%.
- Minta penerima mengecek portofolio di {PORTFOLIO_URL} dan mengundang mereka membalas email bila tertarik.
- Sertakan kalimat layanan otomasi n8n 24/7 dan URL portofolio yang tepat.
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

def make_id(email_address):
    """Stable opaque ID: HMAC prevents exposing a raw email in dashboard IDs."""
    if not INGEST_TOKEN or INGEST_TOKEN == "INGEST_TOKEN":
        raise RuntimeError("Set a real INGEST_TOKEN in GitHub Actions Secrets.")
    digest = hmac.new(
        INGEST_TOKEN.encode("utf-8"),
        str(email_address).strip().lower().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]
    return "web-" + digest


def _state_cipher():
    if not INGEST_TOKEN or INGEST_TOKEN == "INGEST_TOKEN":
        raise RuntimeError("INGEST_TOKEN is required to encrypt the local state.")
    material = hashlib.sha256(
        b"aigrowth-prospecting-state-v1:" + INGEST_TOKEN.encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(material))


def _today_wib():
    return datetime.now(WIB).date().isoformat()


def load_state():
    state = {
        "version": 1,
        "send_day_wib": _today_wib(),
        "sent_today": 0,
        "records": {},
        "pending_sync": {},
        "processed_reply_uids": [],
    }
    if STATE_PATH.exists():
        try:
            encrypted = STATE_PATH.read_bytes()
            loaded = json.loads(_state_cipher().decrypt(encrypted).decode("utf-8"))
            if not isinstance(loaded, dict) or loaded.get("version") != 1:
                raise RuntimeError("Unsupported encrypted state format.")
            state.update(loaded)
        except InvalidToken as exc:
            raise RuntimeError(
                "Cannot decrypt runtime/prospecting-state.enc. Keep INGEST_TOKEN stable; "
                "sending is stopped to avoid duplicates."
            ) from exc
        except (ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError("Encrypted prospecting state is unreadable; no sends attempted.") from exc

    state.setdefault("records", {})
    state.setdefault("pending_sync", {})
    state.setdefault("processed_reply_uids", [])
    if state.get("send_day_wib") != _today_wib():
        state["send_day_wib"] = _today_wib()
        state["sent_today"] = 0
    state["sent_today"] = max(0, int(state.get("sent_today") or 0))
    return state


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        state, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    STATE_PATH.write_bytes(_state_cipher().encrypt(payload))


def dashboard_record(entry):
    record = dict(entry.get("record") or {})
    record["status"] = str(entry.get("status") or "queued").lower()
    record["sent_at"] = entry.get("sent_at")
    record["replied_at"] = entry.get("replied_at")
    record["error"] = (str(entry.get("error") or "")[:400] or None)
    if record["status"] in ("replied", "blocked") and entry.get("reply_preview"):
        record["message_preview"] = str(entry["reply_preview"])[:500]
    elif entry.get("last_message_preview"):
        record["message_preview"] = str(entry["last_message_preview"])[:500]
    else:
        record["message_preview"] = str(record.get("message_preview") or "")[:500]
    return record


def queue_dashboard_sync(state, lead_id):
    state["pending_sync"][lead_id] = dashboard_record(state["records"][lead_id])
    save_state(state)


def dashboard_post_records(records):
    if not records:
        return
    if not INGEST_TOKEN:
        raise RuntimeError("Missing INGEST_TOKEN.")
    headers = {
        "Authorization": "Bearer " + INGEST_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    for start in range(0, len(records), 50):
        batch = records[start:start + 50]
        last_error = None
        for attempt in range(3):
            try:
                response = requests.post(
                    DASHBOARD_INGEST_URL,
                    headers=headers,
                    json={"records": batch},
                    timeout=30,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = RuntimeError("Dashboard ingest HTTP " + str(response.status_code))
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))
                        continue
                    raise last_error
                response.raise_for_status()
                try:
                    data = response.json()
                except ValueError:
                    data = {}
                if isinstance(data, dict) and data.get("ok") is False:
                    raise RuntimeError("Dashboard rejected a scraping batch.")
                print("DASHBOARD_INGEST_OK", len(batch), "HTTP", response.status_code)
                break
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(
                    "Dashboard ingest failed after retries: "
                    + type(last_error).__name__ + ": " + str(last_error)
                ) from last_error


def sync_pending(state):
    pending = state.get("pending_sync") or {}
    if not pending:
        return 0
    items = list(pending.items())
    synced = 0
    for start in range(0, len(items), 50):
        batch_items = items[start:start + 50]
        dashboard_post_records([row for _, row in batch_items])
        for lead_id, _ in batch_items:
            state["pending_sync"].pop(lead_id, None)
            synced += 1
        save_state(state)
    return synced


def _platform_and_handle(social_url, website_url):
    selected = social_url or website_url or ""
    host = urlparse(selected).netloc.lower().split("@")[-1].split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    platform = "website"
    for domain, label in (
        ("instagram.com", "instagram"),
        ("facebook.com", "facebook"),
        ("tiktok.com", "tiktok"),
        ("linkedin.com", "linkedin"),
        ("youtube.com", "youtube"),
        ("x.com", "x"),
        ("twitter.com", "x"),
    ):
        if host == domain or host.endswith("." + domain):
            platform = label
            break
    if social_url:
        parts = [part for part in urlparse(social_url).path.split("/") if part]
        ignored = {"p", "reel", "reels", "stories", "company", "in", "user", "profile"}
        candidate = next((part for part in parts if part.lower() not in ignored), "")
        handle = "@" + candidate.lstrip("@") if candidate else ("@" + host if host else "")
        return platform, handle
    return platform, host or ""


def _smtp_configured():
    return bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD and SMTP_FROM)


def _imap_configured():
    return bool(IMAP_HOST and IMAP_USERNAME and IMAP_PASSWORD)


def _send_email(entry, subject, body):
    if not _smtp_configured():
        raise RuntimeError("SMTP credentials are not configured.")
    lead_id = entry["record"]["id"]
    message = EmailMessage()
    message["Subject"] = ("[AG-" + lead_id + "] " + str(subject or "Tindak lanjut"))[:250]
    message["From"] = formataddr((AGENCY_NAME, SMTP_FROM))
    message["To"] = entry["record"]["contact"]
    message["Reply-To"] = SMTP_REPLY_TO or SMTP_FROM
    message["Message-ID"] = make_msgid()
    message.set_content(str(body or "").strip())

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(
            SMTP_HOST, SMTP_PORT, timeout=30,
            context=ssl.create_default_context()
        ) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
    return str(message["Message-ID"])


def _decode_message_text(message):
    chunks = []
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.get_content_type() != "text/plain" or part.get_content_disposition() == "attachment":
            continue
        try:
            content = part.get_payload(decode=True)
            if content is None:
                content = str(part.get_payload() or "").encode("utf-8", errors="replace")
            chunks.append(content.decode(part.get_content_charset() or "utf-8", errors="replace"))
        except Exception:
            continue
    text = "\n".join(chunks).strip()
    for separator in (
        "\nOn ", "\nPada ", "\nFrom:", "\n-----Original Message-----",
        "\nDari:", "\n> ",
    ):
        if separator in text:
            text = text.split(separator, 1)[0]
    return re.sub(r"\s+", " ", text).strip()[:1200]


def _message_lead_id(message, state):
    subject = str(message.get("Subject") or "")
    match = re.search(r"\[AG-(web-[0-9a-f]{24})\]", subject, re.I)
    if match and match.group(1) in state.get("records", {}):
        lead_id = match.group(1)
    else:
        lead_id = ""
    if not lead_id:
        references = " ".join((
            str(message.get("In-Reply-To") or ""),
            str(message.get("References") or ""),
        ))
        if references:
            for candidate_id, entry in state.get("records", {}).items():
                message_id = str(entry.get("last_message_id") or "")
                if message_id and message_id in references:
                    lead_id = candidate_id
                    break
    if not lead_id:
        return ""
    sender = parseaddr(str(message.get("From") or ""))[1].strip().lower()
    expected = str(state["records"][lead_id].get("record", {}).get("contact") or "").strip().lower()
    if not sender or sender != expected:
        return ""
    return lead_id


def scan_replies(state):
    """Return True only if the IMAP inbox scan succeeds."""
    if not _imap_configured():
        print("REPLY_SCAN_DISABLED", "IMAP credentials not configured")
        return False
    mailbox = None
    try:
        mailbox = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mailbox.login(IMAP_USERNAME, IMAP_PASSWORD)
        status, _ = mailbox.select("INBOX")
        if status != "OK":
            raise RuntimeError("Could not open IMAP INBOX.")
        since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%d-%b-%Y")
        status, search_data = mailbox.uid("search", None, "SINCE", since)
        if status != "OK":
            raise RuntimeError("IMAP message search failed.")
        uids = (search_data[0] or b"").split()[-500:]
        processed = set(str(uid) for uid in state.get("processed_reply_uids", []))
        replies_found = 0
        for uid in uids:
            uid_text = uid.decode("ascii", errors="ignore")
            if uid_text in processed:
                continue
            status, fetched = mailbox.uid("fetch", uid, "(RFC822)")
            if status != "OK" or not fetched:
                continue
            raw = next(
                (part[1] for part in fetched if isinstance(part, tuple) and isinstance(part[1], bytes)),
                None,
            )
            if not raw:
                continue
            message = email.message_from_bytes(raw, policy=default)
            lead_id = _message_lead_id(message, state)
            if not lead_id:
                continue
            entry = state["records"][lead_id]
            if entry.get("status") in ("replied", "blocked"):
                mailbox.uid("store", uid, "+FLAGS", r"(\Seen)")
                processed.add(uid_text)
                continue

            preview = _decode_message_text(message) or "(Balasan email diterima)"
            try:
                received = parsedate_to_datetime(str(message.get("Date") or ""))
                if received.tzinfo is None:
                    received = received.replace(tzinfo=timezone.utc)
                date_value = received.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            except Exception:
                date_value = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            entry["reply_preview"] = preview[:500]
            entry["error"] = None
            if re.search(r"\b(unsubscribe|stop|jangan hubungi|berhenti kirim|hapus kontak)\b", preview, re.I):
                entry["status"] = "blocked"
                entry["replied_at"] = None
                entry["blocked_at"] = date_value
                entry["last_message_preview"] = preview[:500]
                print("OPT_OUT_RECEIVED", lead_id)
            else:
                entry["status"] = "replied"
                entry["replied_at"] = date_value
                entry["last_message_preview"] = preview[:500]
                print("REPLY_RECEIVED", lead_id)
            queue_dashboard_sync(state, lead_id)
            mailbox.uid("store", uid, "+FLAGS", r"(\Seen)")
            processed.add(uid_text)
            replies_found += 1
        state["processed_reply_uids"] = list(processed)[-3000:]
        save_state(state)
        sync_pending(state)
        print("REPLY_SCAN_OK", "matched", replies_found)
        return True
    except Exception as exc:
        print("REPLY_SCAN_ERROR", type(exc).__name__, str(exc)[:250])
        return False
    finally:
        if mailbox is not None:
            try:
                mailbox.logout()
            except Exception:
                pass


def _utc_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _followup_due(entry, now):
    count = int(entry.get("followup_count") or 0)
    if count >= 3 or entry.get("status") != "sent":
        return False
    first = _utc_datetime(entry.get("first_sent_at"))
    last = _utc_datetime(entry.get("last_sent_at"))
    if first is None:
        return False
    target_days = (2, 5, 9)
    target = first + timedelta(days=target_days[count])
    minimum_gap = (0, 3, 4)[count]
    if last is not None and minimum_gap:
        target = max(target, last + timedelta(days=minimum_gap))
    return now >= target


def _followup_copy(entry, stage):
    name = str(entry.get("record", {}).get("name") or "tim")
    if stage == 0:
        opening = "Saya menindaklanjuti email sebelumnya tentang kemungkinan otomasi workflow untuk membantu proses operasional yang berulang."
    elif stage == 1:
        opening = "Saya ingin memastikan email sebelumnya tidak terlewat. Jika relevan, saya bisa mengirim contoh alur otomasi singkat yang sesuai dengan kebutuhan bisnis."
    else:
        opening = "Ini tindak lanjut terakhir dari saya. Jika saat ini belum dibutuhkan, tidak masalah dan saya tidak akan mengirim tindak lanjut berikutnya."
    return (
        "Halo " + name + ",\n\n" + opening + "\n\n"
        + AUTOMATION_OFFER + "\n\n"
        + "Portofolio: " + PORTFOLIO_URL + "\n\n"
        + "Jika email ini tidak relevan, balas UNSUBSCRIBE dan kami tidak akan menghubungi lagi.\n\n"
        + "Salam,\nRey\nSonjaya Remote Business Services"
    )


def _send_entry(entry, state, subject, body, is_followup=False):
    lead_id = entry["record"]["id"]
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    message_id = _send_email(entry, subject, body)
    entry["last_message_id"] = message_id
    entry["last_sent_at"] = now
    entry["last_message_preview"] = str(body or "")[:500]
    entry["error"] = None
    entry["status"] = "sent"
    if not entry.get("first_sent_at"):
        entry["first_sent_at"] = now
        entry["sent_at"] = now
        entry["followup_count"] = 0
    elif is_followup:
        entry["followup_count"] = int(entry.get("followup_count") or 0) + 1
    state["sent_today"] = int(state.get("sent_today") or 0) + 1
    state["send_day_wib"] = _today_wib()
    # Save successful SMTP acceptance and counter before syncing dashboard.
    queue_dashboard_sync(state, lead_id)
    save_state(state)
    sync_pending(state)
    print("EMAIL_SENT", lead_id, "followup", int(entry.get("followup_count") or 0), "daily_total", state["sent_today"])


def _attempt_send(entry, state, subject, body, is_followup=False):
    if state.get("send_day_wib") != _today_wib():
        state["send_day_wib"] = _today_wib()
        state["sent_today"] = 0
    if int(state.get("sent_today") or 0) >= MAX_DAILY_SENDS:
        return False
    if not ENABLE_AUTO_EMAIL or not _smtp_configured():
        return False
    if entry.get("status") in ("replied", "blocked") or entry.get("blocked"):
        return False
    try:
        _send_entry(entry, state, subject, body, is_followup)
        return True
    except Exception as exc:
        # If SMTP succeeded but dashboard sync failed, preserve SENT and retry only the dashboard sync.
        if entry.get("status") == "sent" and entry.get("last_message_id"):
            queue_dashboard_sync(state, entry["record"]["id"])
            save_state(state)
            print("DASHBOARD_SYNC_DEFERRED", entry["record"]["id"], type(exc).__name__)
            return False
        entry["attempts"] = int(entry.get("attempts") or 0) + 1
        entry["error"] = (type(exc).__name__ + ": " + str(exc))[:400]
        entry["status"] = "failed" if entry["attempts"] >= 3 else "queued"
        queue_dashboard_sync(state, entry["record"]["id"])
        save_state(state)
        try:
            sync_pending(state)
        except Exception as sync_exc:
            print("DASHBOARD_SYNC_DEFERRED", entry["record"]["id"], type(sync_exc).__name__)
        print("EMAIL_SEND_ERROR", entry["record"]["id"], entry["attempts"], type(exc).__name__)
        return False


def _send_due_followups(state, mailbox_ready, max_to_send):
    if not mailbox_ready or not ENABLE_AUTO_EMAIL or not _smtp_configured():
        return 0
    now = datetime.now(timezone.utc)
    due = [
        entry for entry in state["records"].values()
        if _followup_due(entry, now) and int(entry.get("attempts") or 0) < 3
    ]
    due.sort(key=lambda item: item.get("first_sent_at") or "")
    sent = 0
    for entry in due:
        if sent >= max_to_send or int(state.get("sent_today") or 0) >= MAX_DAILY_SENDS:
            break
        if state.get("pending_sync"):
            break
        stage = int(entry.get("followup_count") or 0)
        if _attempt_send(
            entry, state, entry.get("subject") or "Tindak lanjut otomasi workflow",
            _followup_copy(entry, stage), True
        ):
            sent += 1
    return sent


def _send_queued_initial_emails(state, max_to_send):
    if not ENABLE_AUTO_EMAIL or not _smtp_configured():
        print("AUTO_EMAIL_PAUSED", "Set SMTP secrets and ENABLE_AUTO_EMAIL=true to send queued emails.")
        return 0
    candidates = [
        entry for entry in state["records"].values()
        if entry.get("status") in ("queued", "failed")
        and not entry.get("sent_at")
        and not entry.get("blocked")
        and int(entry.get("score") or 0) >= MIN_SCORE_TO_SEND
        and int(entry.get("attempts") or 0) < 3
    ]
    candidates.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
    sent = 0
    for entry in candidates:
        if sent >= max_to_send or int(state.get("sent_today") or 0) >= MAX_DAILY_SENDS:
            break
        if state.get("pending_sync"):
            break
        if _attempt_send(entry, state, entry.get("subject") or "Otomasi workflow untuk bisnis Anda", entry.get("body") or ""):
            sent += 1
    return sent


def _make_entry(lead, ai, score):
    email_address = str(lead.get("recipient_email") or "").strip().lower()
    lead_id = make_id(email_address)
    website_url = str(lead.get("website_url") or lead.get("email_source_url") or "").strip()
    social_url = str(lead.get("social_url") or "").strip()
    platform, handle = _platform_and_handle(social_url, website_url)
    business_name = str(ai.get("business_name") or lead.get("search_title") or email_address.split("@")[0]).strip()
    city = str(ai.get("city") or fallback_city(lead) or "Tidak diketahui dari evidence publik")
    category = str(ai.get("niche") or fallback_niche(lead) or "Tidak diketahui dari evidence publik")
    preview = str(ai.get("body") or "").strip()[:500]
    record = {
        "id": lead_id,
        "platform": platform,
        "name": business_name[:200],
        "handle": handle[:200],
        "contact": email_address,
        "phone": extract_phone(lead.get("public_evidence", "")),
        "url": website_url[:1000],
        "category": category[:120],
        "city": city[:120],
        "campaign": CAMPAIGN_NAME[:120],
        "message_preview": preview,
        "status": "queued",
        "sent_at": None,
        "replied_at": None,
        "error": None,
    }
    subject = str(ai.get("subject") or ("Otomasi workflow untuk " + business_name))[:220]
    body = str(ai.get("body") or "").strip()
    return lead_id, {
        "record": record,
        "score": int(score),
        "subject": subject,
        "body": body,
        "status": "queued",
        "sent_at": None,
        "first_sent_at": None,
        "last_sent_at": None,
        "last_message_id": None,
        "last_message_preview": preview,
        "reply_preview": None,
        "replied_at": None,
        "error": None,
        "attempts": 0,
        "followup_count": 0,
        "blocked": False,
    }


def run():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY.")
    if not INGEST_TOKEN or INGEST_TOKEN == "INGEST_TOKEN":
        raise RuntimeError("Set the real dashboard INGEST_TOKEN in GitHub Actions Secrets.")

    state = load_state()
    # A pending row sync is retried before new scraping or any outbound send.
    sync_pending(state)
    leads = discover()
    print("DISCOVERY_COUNT", len(leads))
    new_count = 0

    for index, lead in enumerate(leads[:MAX_AI_PER_RUN]):
        try:
            ai = clean_ai_result(score_one(lead), lead)
            score = int(ai["score"])
            lead_id, new_entry = _make_entry(lead, ai, score)
            previous = state["records"].get(lead_id)
            if previous:
                # Do not overwrite an outreach history or an opt-out with a fresh scrape.
                if previous.get("status") in ("sent", "replied", "blocked") or previous.get("sent_at"):
                    continue
                new_entry["attempts"] = int(previous.get("attempts") or 0)
                new_entry["followup_count"] = int(previous.get("followup_count") or 0)
                if new_entry["attempts"] >= 3:
                    new_entry["status"] = "failed"
                    new_entry["error"] = previous.get("error")
                state["records"][lead_id] = new_entry
            else:
                state["records"][lead_id] = new_entry
                new_count += 1
            queue_dashboard_sync(state, lead_id)
        except Exception as exc:
            print("AI_OR_RECORD_ERROR", index, type(exc).__name__, str(exc)[:250])

    save_state(state)
    sync_pending(state)
    mailbox_ready = scan_replies(state)

    if state.get("pending_sync"):
        print("SEND_PAUSED", "Dashboard status updates remain pending.")
        save_state(state)
        return

    sent = _send_due_followups(state, mailbox_ready, MAX_SENDS_PER_RUN)
    remaining_run_quota = max(0, MAX_SENDS_PER_RUN - sent)
    sent += _send_queued_initial_emails(state, remaining_run_quota)
    save_state(state)
    print(
        "SCRAPE_CYCLE_COMPLETE",
        json.dumps({
            "new_records": new_count,
            "tracked_records": len(state.get("records", {})),
            "sent_this_run": sent,
            "sent_today_wib": state.get("sent_today", 0),
            "daily_limit": MAX_DAILY_SENDS,
            "followup_scan_enabled": mailbox_ready,
            "auto_email_enabled": bool(ENABLE_AUTO_EMAIL and _smtp_configured()),
            "dashboard_url": DASHBOARD_INGEST_URL,
        }, ensure_ascii=False),
    )


if __name__ == "__main__":
    run()
