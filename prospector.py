import re
import time
from urllib.parse import urljoin, urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131 Safari/537.36"
    )
}

CITIES = [
    "Bandung", "Jakarta", "Bekasi", "Depok", "Tangerang", "Bogor",
    "Surabaya", "Semarang", "Yogyakarta", "Malang", "Medan", "Makassar"
]

NICHES = [
    "barbershop", "salon kecantikan", "klinik kecantikan", "gym fitness",
    "cafe", "restaurant", "bakery", "fashion", "property",
    "wedding organizer", "photography", "car detailing", "travel",
    "kursus bahasa", "dentist", "interior design", "event organizer",
    "laundry", "florist"
]

def clean_ddg_url(href: str) -> str:
    if not href:
        return ""
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc:
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href

def instagram_username(url: str) -> str:
    try:
        p = urlparse(url)
        if "instagram.com" not in p.netloc.lower():
            return ""
        parts = [x for x in p.path.split("/") if x]
        if not parts:
            return ""
        username = parts[0].strip()
        if username.lower() in {"accounts", "explore", "reels", "p", "tv"}:
            return ""
        if not re.fullmatch(r"[A-Za-z0-9._]+", username):
            return ""
        return username
    except Exception:
        return ""

def search_ddg(query: str, max_results: int = 12):
    url = "https://html.duckduckgo.com/html/"
    r = requests.get(url, params={"q": query}, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for item in soup.select(".result"):
        a = item.select_one(".result__a")
        snip = item.select_one(".result__snippet")
        if not a:
            continue
        href = clean_ddg_url(a.get("href", ""))
        title = a.get_text(" ", strip=True)
        snippet = snip.get_text(" ", strip=True) if snip else ""
        rows.append({
            "title": title,
            "snippet": snippet,
            "url": href,
            "username": instagram_username(href)
        })
        if len(rows) >= max_results:
            break
    return rows

def collect_prospects(max_per_query=5):
    found = {}
    # Kombinasi query dibuat fokus pada bisnis publik dan akun bisnis.
    queries = []
    for city in CITIES:
        for niche in NICHES[:8]:
            queries.append(
                f'site:instagram.com "{niche}" "{city}" '
                f'(wa OR whatsapp OR booking OR order OR "link in bio")'
            )

    # Batasi jumlah query per run agar tetap ramah terhadap free tier.
    queries = queries[:36]

    for q in queries:
        try:
            for row in search_ddg(q, max_results=max_per_query):
                u = row["username"].lower()
                if not u:
                    continue
                # Hindari URL post/reel individual. Kita hanya butuh profil.
                profile_url = f"https://www.instagram.com/{row['username']}/"
                if u not in found:
                    found[u] = {
                        "username": row["username"],
                        "instagram_url": profile_url,
                        "search_title": row["title"],
                        "public_evidence": row["snippet"],
                        "source_query": q,
                    }
            time.sleep(1.2)
        except Exception:
            # Satu query gagal tidak boleh mematikan seluruh agent.
            continue

    return list(found.values())
