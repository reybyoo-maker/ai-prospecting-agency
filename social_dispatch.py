from __future__ import annotations
import json, os, requests
from datetime import datetime, timezone, timedelta

WIB=timezone(timedelta(hours=7))
WEBHOOK_URL=os.environ["SHEET_WEBHOOK_URL"]
TOKEN=os.environ["WEBHOOK_TOKEN"]

def call(platform,image_url,caption):
    r=requests.post(
        WEBHOOK_URL,
        json={
            "token":TOKEN,
            "action":"publish_social",
            "platform":platform,
            "image_url":image_url,
            "caption":caption[:2200]
        },
        timeout=120
    )
    r.raise_for_status()
    return r.json()

def main():
    with open("social_publish_payload.json","r",encoding="utf-8") as f:
        posts=json.load(f)

    today=datetime.now(WIB).date().isoformat()
    selected=[p for p in posts if str(p.get("date",""))==today and p.get("asset_url")]
    if not selected:
        print("No social posts due today.")
        return

    for p in selected:
        platform=str(p.get("platform","")).lower()
        image_url=p["asset_url"]
        if platform=="tiktok":
            image_url=p.get("tiktok_asset_url","").strip()
            if not image_url:
                print("TikTok skipped: TIKTOK_MEDIA_BASE_URL is not configured with a verified URL prefix.")
                continue
        data=call(platform,image_url,str(p.get("caption","")))
        print(platform,data)
        if not data.get("ok") and data.get("error") not in (
            "INSTAGRAM_NOT_CONFIGURED",
            "TIKTOK_REFRESH_NOT_CONFIGURED",
        ):
            raise RuntimeError(data)

if __name__=="__main__":
    main()
