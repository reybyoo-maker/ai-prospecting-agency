from __future__ import annotations

import os
import sys
import requests
from google import genai

DASHBOARD_HOME = "https://aigrowth-owner-dashboard.reybyoo.workers.dev/"

def present(name: str) -> bool:
    value = os.getenv(name, "").strip()
    print(("OK " if value else "MISSING ") + name)
    return bool(value)

ok = True
for required in ("GEMINI_API_KEY", "INGEST_TOKEN", "DASHBOARD_INGEST_URL"):
    ok = present(required) and ok

try:
    response = requests.get(DASHBOARD_HOME, timeout=20)
    print("DASHBOARD_HOME_HTTP", response.status_code)
    if response.status_code >= 500:
        ok = False
except Exception as exc:
    print("DASHBOARD_HOME_ERROR", type(exc).__name__, str(exc)[:200])
    ok = False

smtp_configured = all(
    os.getenv(name, "").strip()
    for name in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM")
)
imap_configured = bool(
    (os.getenv("IMAP_HOST") or "imap.gmail.com").strip()
    and (os.getenv("IMAP_USERNAME") or os.getenv("SMTP_USERNAME", "")).strip()
    and (os.getenv("IMAP_PASSWORD") or os.getenv("SMTP_PASSWORD", "")).strip()
)
print("SMTP_CONFIGURED", smtp_configured)
print("IMAP_CONFIGURED", imap_configured)
print(
    "AUTO_EMAIL_ENABLED",
    os.getenv("ENABLE_AUTO_EMAIL", "false").strip().lower() in ("1", "true", "yes", "on"),
)
if not smtp_configured:
    print("NOTE Scraping can ingest records, but email remains queued until SMTP secrets are configured.")

if os.getenv("GEMINI_API_KEY", "").strip():
    try:
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            contents="Reply only OK",
        )
        print("GEMINI_TEST", str(response.text or "").strip()[:80])
    except Exception as exc:
        print("GEMINI_ERROR", type(exc).__name__, str(exc)[:200])
        ok = False

print("HEALTH", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
