"""Probe dashboard ingest auth with empty payloads only; never emits credentials."""
from __future__ import annotations
import os, sys, requests

URL = os.getenv("DASHBOARD_INGEST_URL", "https://aigrowth-owner-dashboard.reybyoo.workers.dev/api/ingest/scrape").strip()
TOKEN = os.getenv("INGEST_TOKEN", "").strip()
if not TOKEN:
    print("DIAG_ABORTED missing INGEST_TOKEN")
    sys.exit(2)

CASES = [
    ("authorization_bearer", {"Authorization": f"Bearer {TOKEN}"}, {"records": []}),
    ("authorization_raw", {"Authorization": TOKEN}, {"records": []}),
    ("x_ingest_token", {"X-INGEST-TOKEN": TOKEN}, {"records": []}),
    ("x_api_key", {"X-API-Key": TOKEN}, {"records": []}),
    ("x_auth_token", {"X-Auth-Token": TOKEN}, {"records": []}),
    ("x_ingest_key", {"X-Ingest-Key": TOKEN}, {"records": []}),
    ("x_dashboard_token", {"X-Dashboard-Token": TOKEN}, {"records": []}),
    ("x_webhook_token", {"X-Webhook-Token": TOKEN}, {"records": []}),
    ("body_token", {}, {"records": [], "token": TOKEN}),
    ("body_ingest_token", {}, {"records": [], "ingest_token": TOKEN}),
    ("body_auth_token", {}, {"records": [], "auth_token": TOKEN}),
    ("body_api_key", {}, {"records": [], "api_key": TOKEN}),
]
accepted = False
for label, auth_headers, payload in CASES:
    try:
        response = requests.post(
            URL,
            headers={**auth_headers, "Content-Type": "application/json", "Accept": "application/json"},
            json=payload,
            timeout=15,
        )
        body = (response.text or "").replace(TOKEN, "[REDACTED]")[:240].replace("\\n", " ")
        print(f"AUTH_PROBE mode={label} status={response.status_code} body={body!r}")
        if response.status_code not in (401, 403):
            accepted = response.status_code < 500
            break
    except Exception as exc:
        print(f"AUTH_PROBE mode={label} network_error={type(exc).__name__}")
print("AUTH_PROBE_RESULT", "AUTH_FORMAT_ACCEPTED" if accepted else "NO_TESTED_AUTH_FORMAT_ACCEPTED")
sys.exit(0 if accepted else 1)
