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

def collect_prospects(
    queries_per_run: int = 8,
    max_per_query: int = 12,
):
    pool = build_query_pool()

    now = datetime.now(
        timezone(timedelta(hours=7))
    )

    slot = now.hour // 6
    day = now.timetuple().tm_yday

    start = (
        (day * 4 + slot)
        * queries_per_run
    ) % len(pool)

    selected = [
        pool[
            (start + i) % len(pool)
        ]
        for i in range(queries_per_run)
    ]

    print(
        f"Nationwide TinyFish search | "
        f"{queries_per_run} queries/run | "
        f"rotation={start}"
    )

    found = {}

    for index, query in enumerate(
        selected,
        start=1,
    ):
        try:
            results = search(query)

            added = 0

            for result in results:
                if not isinstance(result, dict):
                    continue

                username, profile_url = (
                    extract_profile_from_result(
                        result
                    )
                )

                if not username:
                    continue

                key = username.lower()

                if key not in found:
                    evidence = " ".join(
                        str(result.get(k, ""))
                        for k in (
                            "title",
                            "snippet",
                            "description",
                        )
                        if result.get(k)
                    )

                    found[key] = {
                        "username": username,
                        "instagram_url": profile_url,
                        "search_title": str(
                            result.get(
                                "title",
                                ""
                            )
                        ),
                        "public_evidence": (
                            evidence[:1600]
                        ),
                        "source_query": query,
                    }
                    added += 1

                if added >= max_per_query:
                    break

            print(
                f"Query {index}/{queries_per_run} | "
                f"{len(results)} results | "
                f"{added} new profiles"
            )

        except Exception as exc:
            print(
                f"Query {index}/{queries_per_run} | "
                f"FAILED | {exc}"
            )

        # Keep below a conservative search request pace.
        time.sleep(3)

    print(
        f"Profil Instagram valid unik: "
        f"{len(found)}"
    )

    if not found:
        raise RuntimeError(
            "Tidak menemukan profil Instagram valid."
        )

    return list(found.values())[:100]
