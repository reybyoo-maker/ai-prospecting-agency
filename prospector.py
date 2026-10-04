import os
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse

import requests

TINYFISH_API_KEY = os.environ["TINYFISH_API_KEY"]
SEARCH_URL = "https://api.search.tinyfish.ai"

CITIES = [
    "Jakarta", "Bandung", "Bekasi", "Depok", "Tangerang", "Bogor",
    "Cimahi", "Sukabumi", "Cianjur", "Karawang", "Purwakarta",
    "Cirebon", "Tasikmalaya", "Garut", "Serang", "Cilegon", "Tegal",
    "Pekalongan", "Semarang", "Solo", "Yogyakarta", "Magelang",
    "Kudus", "Purwokerto", "Surabaya", "Sidoarjo", "Malang", "Batu",
    "Kediri", "Blitar", "Madiun", "Jember", "Pasuruan", "Probolinggo",
    "Mojokerto", "Medan", "Binjai", "Padang", "Pekanbaru", "Batam",
    "Palembang", "Jambi", "Bengkulu", "Bandar Lampung", "Banda Aceh",
    "Lhokseumawe", "Banjarmasin", "Balikpapan", "Samarinda",
    "Pontianak", "Palangkaraya", "Banjarbaru", "Makassar", "Manado",
    "Palu", "Kendari", "Gorontalo", "Denpasar", "Badung", "Singaraja",
    "Mataram", "Kupang", "Ambon", "Ternate", "Jayapura", "Sorong",
    "Manokwari", "Metro", "Prabumulih", "Lubuklinggau", "Dumai",
    "Siak", "Bukittinggi", "Padangsidimpuan", "Pematangsiantar",
    "Tanjungpinang", "Mamuju", "Palopo", "Parepare", "Bitung",
    "Tomohon", "Baubau", "Lhokseumawe", "Langsa", "Sabang"
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
    "travel agent", "kos", "villa", "hotel", "coffee roastery",
    "event organizer", "rental mobil", "rental motor", "jasa wedding"
]

def normalize_profile(url):
    if not url:
        return "", ""
    u = str(url).strip()

    if not u.startswith(("http://", "https://")):
        u = "https://" + u

    p = urlparse(u)
    host = p.netloc.lower()

    if "instagram.com" not in host:
        return "", ""

    parts = [x for x in p.path.split("/") if x]
    if not parts:
        return "", ""

    banned = {
        "accounts", "about", "developer", "direct", "directory",
        "explore", "legal", "privacy", "reels", "stories", "terms",
        "tv", "p", "web", "emails"
    }

    username = parts[0].strip()

    if username.lower() in banned:
        return "", ""

    if not re.fullmatch(r"[A-Za-z0-9._]{1,50}", username):
        return "", ""

    return username, f"https://www.instagram.com/{username}/"

def extract_profiles(results):
    found = []

    for result in results:
        if not isinstance(result, dict):
            continue

        url_candidates = [
            result.get("url"),
            result.get("link"),
        ]

        text_blob = " ".join([
            str(result.get("title", "")),
            str(result.get("snippet", "")),
            str(result.get("description", "")),
        ])

        # Try result URL first.
        username = ""
        profile_url = ""

        for candidate in url_candidates:
            username, profile_url = normalize_profile(candidate)
            if username:
                break

        # Then search any Instagram URL embedded in title/snippet.
        if not username:
            m = re.search(
                r'https?://(?:www\.)?instagram\.com/[A-Za-z0-9._]{1,50}/?',
                text_blob,
                flags=re.I,
            )
            if m:
                username, profile_url = normalize_profile(m.group(0))

        if not username:
            continue

        evidence = re.sub(r"\s+", " ", text_blob).strip()

        found.append({
            "username": username,
            "instagram_url": profile_url,
            "search_title": str(result.get("title", "")),
            "public_evidence": evidence[:1800],
        })

    return found

def search(query):
    response = requests.get(
        SEARCH_URL,
        params={
            "query": query,
            "location": "Indonesia",
            "language": "id",
        },
        headers={
            "X-API-Key": TINYFISH_API_KEY,
            "Accept": "application/json",
        },
        timeout=45,
    )

    if response.status_code == 401:
        raise RuntimeError("TINYFISH_API_KEY salah/tidak aktif.")
    if response.status_code == 403:
        raise RuntimeError("TinyFish menolak request (403).")
    if response.status_code == 429:
        raise RuntimeError("TinyFish rate limit (429).")

    response.raise_for_status()

    data = response.json()

    # Support a couple of response shapes.
    results = data.get("results", [])
    if not results and isinstance(data.get("web"), dict):
        results = data["web"].get("results", [])

    return results

def build_query_pool():
    pool = []

    # Broad variants help capture different business profiles.
    intent_terms = [
        '"whatsapp" "link in bio"',
        '"booking" "link in bio"',
        '"order" "whatsapp"',
        '"contact" "whatsapp"',
    ]

    for city in CITIES:
        for niche in NICHES:
            for intent in intent_terms:
                pool.append(
                    f'site:instagram.com "{niche}" "{city}" {intent}'
                )

    return pool

def collect_prospects(queries_per_run=8, max_per_query=10):
    pool = build_query_pool()

    now = datetime.now(timezone(timedelta(hours=7)))

    # 4 runs/day × 8 queries = 32 search requests/day.
    # Rotation changes by day + 6-hour slot, avoiding same queries.
    slot = now.hour // 6
    day_index = now.timetuple().tm_yday

    start = (day_index * 4 + slot) * queries_per_run
    start %= len(pool)

    selected = [
        pool[(start + i) % len(pool)]
        for i in range(queries_per_run)
    ]

    print(
        f"Nationwide TinyFish search | "
        f"{queries_per_run} queries/run | index={start}"
    )

    found = {}

    for idx, query in enumerate(selected, start=1):
        try:
            results = search(query)

            profiles = extract_profiles(results)

            for profile in profiles[:max_per_query]:
                key = profile["username"].lower()

                if key not in found:
                    found[key] = {
                        **profile,
                        "source_query": query,
                    }

            print(
                f"Query {idx}/{queries_per_run} | "
                f"{len(results)} results | "
                f"{len(profiles)} Instagram profiles"
            )

        except Exception as exc:
            print(
                f"Query {idx}/{queries_per_run} | FAILED | {exc}"
            )

        # Keep comfortably under TinyFish's published 30 requests/minute.
        time.sleep(3)

    print(f"Profil unik kandidat: {len(found)}")

    if not found:
        raise RuntimeError(
            "0 kandidat Instagram ditemukan. "
            "Periksa TINYFISH_API_KEY atau log search."
        )

    return list(found.values())[:100]
