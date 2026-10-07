from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

WIB = timezone(timedelta(hours=7))
SHEET_WEBHOOK_URL = os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]
AUTO_PUBLISH_PLATFORMS = [
    p.strip().lower()
    for p in os.getenv("AUTO_PUBLISH_PLATFORMS", "instagram,tiktok").split(",")
    if p.strip()
]
MANIFEST = Path(os.getenv("PUBLISH_MANIFEST", "publish_manifest.json"))


def today_wib() -> str:
    return datetime.now(WIB).date().isoformat()


def post_to_platform(item: dict, platform: str) -> dict:
    payload = {
        "token": WEBHOOK_TOKEN,
        "action": "publish_social",
        "platform": platform,
        "date": item["date"],
        "title": item.get("title", "Sonjaya"),
        "caption": item.get("caption", ""),
        "image_urls": item.get("image_urls", []),
    }
    last_error = None
    for attempt in range(1, 4):
        try:
            response = requests.post(SHEET_WEBHOOK_URL, json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return data
            last_error = data.get("error") or data
        except Exception as exc:
            last_error = str(exc)
        if attempt < 3:
            time.sleep(5 * attempt)
    raise RuntimeError(f"{platform} publish failed: {last_error}")


def main() -> int:
    if not MANIFEST.exists():
        raise SystemExit(f"Missing {MANIFEST}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    posts = manifest.get("posts") or []
    today = today_wib()
    item = next((p for p in posts if str(p.get("date", "")) == today), None)

    if not item:
        print(f"No content scheduled for {today}; nothing to publish.")
        return 0

    urls = [str(u).strip() for u in item.get("image_urls", []) if str(u).strip()]
    if len(urls) < 2:
        raise SystemExit("Today's publish item has fewer than 2 carousel images.")

    results = {}
    hard_failures = []
    for platform in AUTO_PUBLISH_PLATFORMS:
        try:
            results[platform] = post_to_platform(item, platform)
            print(f"{platform}: {json.dumps(results[platform], ensure_ascii=False)}")
        except Exception as exc:
            message = str(exc)
            results[platform] = {"ok": False, "error": message}
            print(f"{platform}: ERROR {message}")
            # Missing credentials or TikTok URL verification are expected setup blockers;
            # keep the daily workflow green until that channel is configured.
            expected_setup_blocker = any(
                needle in message
                for needle in (
                    "INSTAGRAM_ACCESS_TOKEN_NOT_CONFIGURED",
                    "IG_USER_ID_NOT_CONFIGURED",
                    "TIKTOK_ACCESS_TOKEN_NOT_CONFIGURED",
                    "url_ownership_unverified",
                    "scope_not_authorized",
                    "unaudited_client_can_only_post_to_private_accounts",
                )
            )
            if not expected_setup_blocker:
                hard_failures.append(platform)

    Path("publish_results.json").write_text(
        json.dumps(
            {"date": today, "results": results},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return 1 if hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
