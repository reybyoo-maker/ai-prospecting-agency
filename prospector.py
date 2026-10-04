import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import requests

# Jina Reader can fetch public web pages and return clean text/links.
# No Jina key is required for the 20 RPM reader limit.
JINA_READER = "https://r.jina.ai/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

CITIES = [
    # Jabodetabek + Jawa
    "Jakarta", "Bandung", "Bekasi", "Depok", "Tangerang", "Bogor",
    "Cimahi", "Sukabumi", "Cianjur", "Karawang", "Purwakarta",
    "Cirebon", "Tasikmalaya", "Garut", "Serang", "Cilegon", "Tegal",
    "Pekalongan", "Semarang", "Solo", "Yogyakarta", "Magelang",
    "Kudus", "Purwokerto", "Surabaya", "Sidoarjo", "Malang", "Batu",
    "Kediri", "Blitar", "Madiun", "Jember", "Pasuruan", "Probolinggo",
    "Mojokerto",

    # Sumatra
    "Medan", "Binjai", "Pematangsiantar", "Padang", "Pekanbaru",
    "Batam", "Palembang", "Jambi", "Bengkulu", "Bandar Lampung",
    "Banda Aceh", "Lhokseumawe",

    # Kalimantan
    "Banjarmasin", "Balikpapan", "Samarinda", "Pontianak",
    "Palangkaraya", "Banjarbaru",

    # Sulawesi
    "Makassar", "Manado", "Palu", "Kendari", "Gorontalo",
    "Parepare",

    # Bali + NTB + NTT
    "Denpasar", "Badung", "Singaraja", "Mataram", "Kupang",

    # Maluku + Papua
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
    "travel agent", "kos", "apartemen", "villa", "hotel"
]

def indonesia_now():
    return datetime.now(timezone(timedelta(hours=7)))

def extract_instagram_profiles(text: str):
    # Matches only profile-style URLs, not post/reel/promo links.
    pattern = re.compile(
        r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]{1,50})/?',
        re.I,
    )

    results = []
    seen = set()

    banned = {
        "accounts", "about", "developer", "direct", "directory",
        "explore", "legal", "privacy", "reels", "stories", "terms",
        "tv", "p", "web", "emails"
    }

    for m in pattern.finditer(text):
        username = m.group(1).strip()
        if username.lower() in banned:
            continue

        key = username.lower()
        if key in seen:
            continue

        seen.add(key)
        start = max(0, m.start() - 450)
        end = min(len(text), m.end() + 450)

        # Keep nearby text as evidence for Gemini.
        evidence = re.sub(r"\s+", " ", text[start:end]).strip()

        results.append({
            "username": username,
            "instagram_url": f"https://www.instagram.com/{username}/",
            "public_evidence": evidence[:1400],
        })

    return results

def jina_fetch_search(target_url: str):
    # Example:
    # https://r.jina.ai/http://www.google.com/search?q=...
    reader_url = JINA_READER + target_url
    r = requests.get(
        reader_url,
        headers=HEADERS,
        timeout=40,
    )
    r.raise_for_status()

    if not r.text.strip():
        raise RuntimeError("Jina Reader mengembalikan halaman kosong.")

    return r.text

def search_with_jina(engine: str, query: str, count: int = 20):
    if engine == "google":
        target = (
            "https://www.google.com/search?"
            + urlencode({
                "q": query,
                "num": count,
                "hl": "id",
                "filter": "0",
            })
        )
    else:
        target = (
            "https://www.bing.com/search?"
            + urlencode({
                "q": query,
                "count": count,
                "setlang": "id-id",
            })
        )

    text = jina_fetch_search(target)
    return extract_instagram_profiles(text)

def build_queries():
    pairs = []

    # Build a large nationwide pool.
    for city in CITIES:
        for niche in NICHES:
            q = (
                f'site:instagram.com "{niche}" "{city}" '
                f'("whatsapp" OR "booking" OR "order" OR "link in bio")'
            )
            pairs.append(q)

    return pairs

def collect_prospects(max_per_query=12, queries_per_run=12):
    pool = build_queries()

    now = indonesia_now()

    # Rotate the query window each run, so the system does not repeatedly
    # search the same city/niche combinations.
    run_slot = (now.hour // 6)
    day_index = now.timetuple().tm_yday
    start = (day_index * 4 + run_slot * queries_per_run) % len(pool)
    selected = [
        pool[(start + i) % len(pool)]
        for i in range(queries_per_run)
    ]

    found = {}
    print(
        f"Nationwide search | {queries_per_run} queries/run | "
        f"rotation index {start}"
    )

    # Jina Reader without a key is limited to 20 RPM, so spacing requests
    # keeps us well below that ceiling.
    for i, query in enumerate(selected, start=1):
        success = False

        for engine in ("google", "bing"):
            try:
                profiles = search_with_jina(
                    engine,
                    query,
                    count=max_per_query * 2
                )

                if profiles:
                    success = True

                    for profile in profiles[:max_per_query]:
                        key = profile["username"].lower()

                        if key not in found:
                            found[key] = {
                                "username": profile["username"],
                                "instagram_url": profile["instagram_url"],
                                "search_title": "",
                                "public_evidence": profile["public_evidence"],
                                "source_query": query,
                            }

                    print(
                        f"Query {i}/{queries_per_run} | "
                        f"{engine} | {len(profiles)} profil"
                    )
                    break

            except Exception as exc:
                print(
                    f"Query {i}/{queries_per_run} | "
                    f"{engine} gagal: {exc}"
                )

        if not success:
            print(f"Query {i}/{queries_per_run} | tidak menemukan profil.")

        # Stay under Jina Reader's no-key rate limit.
        time.sleep(4)

    print(f"Profil unik kandidat: {len(found)}")

    if not found:
        raise RuntimeError(
            "Tidak ada kandidat Instagram ditemukan. "
            "Search layer tidak menghasilkan profil publik."
        )

    # Limit candidate volume before Gemini.
    return list(found.values())[:100]
