import os
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse

import requests

TINYFISH_API_KEY = os.environ["TINYFISH_API_KEY"]
SEARCH_URL = "https://api.search.tinyfish.ai"

HEADERS = {
    "X-API-Key": TINYFISH_API_KEY,
    "Accept": "application/json",
    "User-Agent": "AI-Prospecting-Agency/1.0",
}

CITIES = [
    "Jakarta", "Bandung", "Bekasi", "Depok", "Tangerang", "Bogor",
    "Cimahi", "Sukabumi", "Cianjur", "Karawang", "Purwakarta",
    "Cirebon", "Tasikmalaya", "Garut", "Serang", "Cilegon", "Tegal",
    "Pekalongan", "Semarang", "Solo", "Yogyakarta", "Magelang",
    "Kudus", "Purwokerto", "Surabaya", "Sidoarjo", "Malang", "Batu",
    "Kediri", "Blitar", "Madiun", "Jember", "Pasuruan", "Probolinggo",
    "Mojokerto", "Medan", "Binjai", "Padang", "Pekanbaru", "Batam",
    "Palembang", "Jambi", "Bengkulu", "Bandar Lampung", "Banda Aceh",
    "Banjarmasin", "Balikpapan", "Samarinda", "Pontianak",
    "Palangkaraya", "Banjarbaru", "Makassar", "Manado", "Palu",
    "Kendari", "Gorontalo", "Denpasar", "Badung", "Mataram", "Kupang",
    "Ambon", "Ternate", "Jayapura", "Sorong", "Manokwari"
]

NICHES = [
    "barbershop", "salon kecantikan", "klinik kecantikan", "gym fitness",
    "cafe", "restaurant", "bakery", "fashion", "property",
    "wedding organizer", "fotografi", "car detailing", "travel",
    "kursus bahasa", "dokter gigi", "interior design", "event organizer",
    "laundry", "florist", "coffee shop", "catering", "bengkel mobil",
    "bengkel motor", "les privat", "kursus komputer", "agency",
    "kontraktor", "arsitek", "notaris", "akuntan", "bimbel",
    "studio foto", "studio musik", "klinik hewan", "pet shop",
    "butik", "toko kue", "supplier", "distributor", "car wash",
    "jasa service AC", "dokter umum", "klinik", "kursus mengemudi",
    "travel agent", "kos", "villa", "hotel", "rental mobil"
]

BANNED_PATHS = {
    "accounts", "about", "developer", "direct", "directory",
    "explore", "legal", "privacy", "reels", "stories", "terms",
    "tv", "p", "web", "emails"
}

def normalize_profile(url: str):
    """Accept only a genuine Instagram PROFILE URL with one path segment."""
    if not url:
        return "", ""

    url = str(url).strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    p = urlparse(url)
    if "instagram.com" not in p.netloc.lower():
        return "", ""

    parts = [x for x in p.path.split("/") if x]

    # A profile is /username/. A reel/post is /reel/ABC/, /p/ABC/, etc.
    if len(parts) != 1:
        return "", ""

    username = parts[0].strip()

    if username.lower() in BANNED_PATHS:
        return "", ""

    if not re.fullmatch(r"[A-Za-z0-9._]{1,50}", username):
        return "", ""

    return username, f"https://www.instagram.com/{username}/"

def extract_profile_from_result(result: dict):
    """Extract only profile URLs; never convert /reel/ or /p/ into usernames."""
    candidates = [
        result.get("url"),
        result.get("link"),
    ]

    # Search all text fields for an Instagram PROFILE URL.
    blob = " ".join(
        str(result.get(k, ""))
        for k in ("title", "snippet", "description", "text")
    )

    candidates.append(blob)

    profile_regex = re.compile(
        r'https?://(?:www\.)?instagram\.com/[A-Za-z0-9._]{1,50}/?(?![A-Za-z0-9._/-])',
        re.I,
    )

    for candidate in candidates:
        if not candidate:
            continue

        candidate = str(candidate)

        matches = profile_regex.findall(candidate)

        if matches:
            for match in matches:
                username, profile_url = normalize_profile(match)
                if username:
                    return username, profile_url

        username, profile_url = normalize_profile(candidate)
        if username:
            return username, profile_url

    return "", ""

def search(query: str):
    r = requests.get(
        SEARCH_URL,
        params={
            "query": query,
            "location": "Indonesia",
            "language": "id",
        },
        headers=HEADERS,
        timeout=45,
    )

    if r.status_code == 401:
        raise RuntimeError("TINYFISH_API_KEY tidak valid.")

    if r.status_code == 403:
        raise RuntimeError("TinyFish mengembalikan 403.")

    if r.status_code == 429:
        raise RuntimeError("TinyFish rate limit 429.")

    r.raise_for_status()

    data = r.json()

    if isinstance(data, dict):
        return data.get("results", [])

    return []

def build_query_pool():
    pool = []

    # Broad + intent variants. Rotation prevents repeating the same searches.
    variants = [
        'site:instagram.com "{niche}" "{city}"',
        'site:instagram.com "{niche}" "{city}" "whatsapp"',
        'site:instagram.com "{niche}" "{city}" "booking"',
        'site:instagram.com "{niche}" "{city}" "order"',
    ]

    for city in CITIES:
        for niche in NICHES:
            for template in variants:
                pool.append(
                    template.format(
                        niche=niche,
                        city=city,
                    )
                )

    return pool


EMAIL_RE = re.compile(
    r"(?<![\w.+-])([A-Z0-9._%+-]+(?:\s*\[at\]\s*|\s*\(at\)\s*|@)"
    r"[A-Z0-9.-]+(?:\s*\[dot\]\s*|\s*\(dot\)\s*|\.)[A-Z]{2,})(?![\w.-])",
    re.I,
)
BLOCKED_EMAIL_PREFIXES = ("noreply@", "no-reply@", "donotreply@", "do-not-reply@")

def normalize_email(value: str) -> str:
    value = re.sub(r"\s+", "", str(value or "").strip().lower())
    return (
        value.replace("[at]", "@")
        .replace("(at)", "@")
        .replace("[dot]", ".")
        .replace("(dot)", ".")
    )

def extract_public_email(text: str) -> str:
    for match in EMAIL_RE.findall(text or ""):
        email = normalize_email(match)
        if "@" not in email or email.startswith(BLOCKED_EMAIL_PREFIXES):
            continue
        if email.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg")):
            continue
        return email
    return ""

def fetch_public_email(url: str) -> tuple[str, str]:
    if not url or "instagram.com" in url.lower():
        return "", ""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=12,
            allow_redirects=True,
        )
        html = response.text[:250000]
        email = extract_public_email(html)
        if email:
            return email, url

        parsed = urlparse(response.url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        for path in ("/contact", "/kontak", "/contact-us", "/kontak-kami"):
            page = root + path
            try:
                page_response = requests.get(
                    page,
                    headers=HEADERS,
                    timeout=10,
                    allow_redirects=True,
                )
                email = extract_public_email(page_response.text[:200000])
                if email:
                    return email, page
            except Exception:
                pass
    except Exception:
        pass
    return "", ""

def collect_prospects(
    queries_per_run=8,
    max_per_query=12,
):
    pool = build_query_pool()
    now = datetime.now(timezone(timedelta(hours=7)))
    slot = now.timetuple().tm_yday * 24 + now.hour
    start = (slot * queries_per_run) % len(pool)
    selected = [
        pool[(start + i) % len(pool)]
        for i in range(queries_per_run)
    ]

    found = {}
    web_checked = 0
    no_email = 0

    print(
        f"Nationwide TinyFish search | "
        f"{queries_per_run} queries/run | "
        f"email wajib | rotation={start}"
    )

    for index, query in enumerate(selected, start=1):
        try:
            results = search(query)
            added = 0

            for result in results:
                if not isinstance(result, dict):
                    continue

                url = result.get("url") or result.get("link") or ""
                title = str(result.get("title", ""))
                snippet = str(
                    result.get("snippet")
                    or result.get("description")
                    or result.get("text")
                    or ""
                )
                evidence = f"{title} {snippet}".strip()

                recipient_email = extract_public_email(evidence)
                email_source = url

                if not recipient_email and url and web_checked < 45:
                    recipient_email, email_source = fetch_public_email(url)
                    web_checked += 1

                if not recipient_email:
                    no_email += 1
                    continue

                key = recipient_email.lower()
                if key in found:
                    continue

                username = instagram_username(url)
                social_url = (
                    f"https://www.instagram.com/{username}/"
                    if username else ""
                )

                found[key] = {
                    "recipient_email": recipient_email,
                    "email_source_url": email_source or url,
                    "website_url": (
                        url if "instagram.com" not in url.lower() else ""
                    ),
                    "social_url": social_url,
                    "search_title": title,
                    "public_evidence": evidence[:1800],
                    "source_query": query,
                }
                added += 1

                if added >= max_per_query:
                    break

            print(
                f"Query {index}/{queries_per_run} | "
                f"{len(results)} results | "
                f"{added} prospek ber-email"
            )
        except Exception as exc:
            print(
                f"Query {index}/{queries_per_run} | FAILED | {exc}"
            )

        time.sleep(2)

    print(
        f"Prospek unik dengan email publik: {len(found)} | "
        f"tanpa email dibuang: {no_email} | "
        f"website dicek: {web_checked}"
    )

    return list(found.values())
