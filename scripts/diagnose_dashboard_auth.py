"""Probe dashboard ingest auth using an empty records list; never emits credentials."""
from __future__ import annotations

import os
import sys
import requests

URL = os.getenv(
    "DASHBOARD_INGEST_URL",
    "https://aigrowth-owner-dashboard.reybyoo.workers.dev/api/ingest/scrape",
).strip()
TOKEN = os.getenv("INGEST_TOKEN", "").strip()
if not TOKEN:
    print("DIAG_ABORTED missing INGEST_TOKEN")
    sys.exit(2)

CASES = [
    ("authorization_bearer", {"Authorization": f"Bearer {TOKEN}"}),
    ("authorization_raw", {"Authorization": TOKEN}),
    ("x_ingest_token", {"X-INGEST-TOKEN": TOKEN}),
    ("x_api_key", {"X-API-Key": TOKEN}),
    ("x_auth_token", {"X-Auth-Token": TOKEN}),
    ("x_ingest_key", {"X-Ingest-Key": TOKEN}),
    ("x_dashboard_token", {"X-Dashboard-Token": TOKEN}),
    ("x_webhook_token", {"X-Webhook-Token": TOKEN}),
]
accepted = False
for label, auth_headers in CASES:
    try:
        response = requests.post(
            URL,
            headers={
                **auth_headers,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={"records": []},
            timeout=15,
        )
        body = (response.text or "").replace(TOKEN, "[REDACTED]")[:240].replace("\\n", " ")
        print(f"AUTH_PROBE mode={label} status={response.status_code} body={body!r}")
        # 401/403 indicate auth rejection. Stop on another response so an empty test
        # payload cannot be retried more than needed after auth was accepted.
        if response.status_code not in (401, 403):
            accepted = response.status_code < 500
            break
    except Exception as exc:
        print(f"AUTH_PROBE mode={label} network_error={type(exc).__name__}")
print("AUTH_PROBE_RESULT", "AUTH_FORMAT_ACCEPTED" if accepted else "NO_TESTED_HEADER_ACCEPTED")
sys.exit(0 if accepted else 1)
