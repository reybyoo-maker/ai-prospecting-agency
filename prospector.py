import re
import time
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

CITIES = [
    "Bandung", "Jakarta", "Bekasi", "Depok", "Tangerang", "Bogor",
    "Surabaya", "Semarang", "Yogyakarta", "Malang", "Medan", "Makassar"
]

NICHES = [
    "barbershop", "salon kecantikan", "klinik kecantikan", "gym fitness",
    "cafe", "restaurant", "bakery", "fashion", "property",
    "wedding organizer", "photography", "car detailing", "travel",
    "kursus bahasa", "dokter gigi", "interior design", "event organizer",
    "laundry", "florist"
]

def instagram_username(url: str) -> str:
    try:
        p = urlparse(url)
        host = p.netloc.lower().split(":")[0]
        if not host.endswith("instagram.com"):
            return ""
        parts = [x for x in p.path.split("/") if x]
        if not parts:
            return ""
        username = parts[0].strip()
        if username.lower() in {
            "accounts", "explore", "reels", "p", "tv", "direct",
            "about", "developer", "legal"
        }:
            return ""
        if not re.fullmatch(r"[A-Za-z0-9._]+", username):
            return ""
        return username
    except Exception:
        return ""

def normalize_href(href: str) -> str:
    if not href:
        return ""
    if href.startswith("//"):
        return "https:" + href

    p = urlparse(href)

    # Google / Bing style redirect parameters
    for key in ("q", "url", "u", "uddg"):
        value = parse_qs(p.query).get(key, [])
        if value and ("instagram.com" in value[0].lower()):
            return unquote(value[0])

    return href

def extract_instagram_links(html: str):
    soup = BeautifulSoup(html, "html.parser")
    candidates = []

    for a in soup.find_all("a", href=True):
        href = normalize_href(a.get("href", ""))
        if "instagram.com/" in href.lower():
            candidates.append((href, a.get_text(" ", strip=True)))

    # Catch direct URLs embedded in HTML.
    for m in re.finditer(
        r'https?://(?:www\.)?instagram\.com/[A-Za-z0-9._]+/?',
        html,
        flags=re.I,
    ):
        candidates.append((m.group(0), ""))

    results = []
    seen = set()

    for href, title in candidates:
        username = instagram_username(href)
        if not username:
            continue

        clean = f"https://www.instagram.com/{username}/"
        key = username.lower()

        if key not in seen:
            seen.add(key)
            results.append((clean, title))

    return results

def search_google(query: str, max_results: int = 10):
    r = requests.get(
        "https://www.google.com/search",
        params={"q": query, "num": max_results, "hl": "id"},
        headers=HEADERS,
        timeout=20,
    )
    r.raise_for_status()

    if "unusual traffic" in r.text.lower():
        raise RuntimeError("Google meminta verifikasi traffic")

    return extract_instagram_links(r.text)[:max_results]

def search_bing(query: str, max_results: int = 10):
    r = requests.get(
        "https://www.bing.com/search",
        params={"q": query, "count": max_results, "setlang": "id-id"},
        headers=HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    return extract_instagram_links(r.text)[:max_results]

def search_ddg(query: str, max_results: int = 10):
    r = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers=HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    return extract_instagram_links(r.text)[:max_results]

def search_any(query: str, max_results: int = 10):
    providers = [
        ("Google", search_google),
        ("Bing", search_bing),
        ("DuckDuckGo", search_ddg),
    ]

    errors = []

    for name, fn in providers:
        try:
            links = fn(query, max_results)
            if links:
                return name, links
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    raise RuntimeError("Semua mesin pencari gagal: " + " | ".join(errors))

def collect_prospects(max_per_query=5):
    found = {}
    successful_queries = 0

    queries = []

    # 30 query/run: cukup agresif untuk tes, tapi masih hemat.
    for city in CITIES:
        for niche in NICHES:
            queries.append(
                f'site:instagram.com "{niche}" "{city}" '
                f'("whatsapp" OR "booking" OR "order" OR "link in bio")'
            )

    queries = queries[:30]

    for idx, query in enumerate(queries, start=1):
        try:
            provider, links = search_any(query, max_results=max_per_query)

            if links:
                successful_queries += 1

            for profile_url, title in links:
                username = instagram_username(profile_url)
                if not username:
                    continue

                key = username.lower()

                if key not in found:
                    found[key] = {
                        "username": username,
                        "instagram_url": profile_url,
                        "search_title": title,
                        "public_evidence": (
                            f"Hasil profil publik dari {provider}. "
                            f"Query: {query}"
                        ),
                        "source_query": query,
                    }

            print(
                f"Query {idx}/{len(queries)} | "
                f"{provider} | {len(links)} profil Instagram"
            )
            time.sleep(1.5)

        except Exception as exc:
            print(f"Query {idx}/{len(queries)} | FAILED | {exc}")
            time.sleep(2)

    print(
        f"Query berhasil menemukan profil: "
        f"{successful_queries}/{len(queries)}"
    )
    print(f"Profil unik ditemukan: {len(found)}")

    if not found:
        raise RuntimeError(
            "0 prospek ditemukan. Lihat log Query FAILED untuk sumber masalah."
        )

    return list(found.values())
