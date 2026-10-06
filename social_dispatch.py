from __future__ import annotations
import json, os, requests
from datetime import datetime, timezone, timedelta

WIB=timezone(timedelta(hours=7))
WEBHOOK_URL=os.environ["SHEET_WEBHOOK_URL"]
TOKEN=os.environ["WEBHOOK_TOKEN"]

def main():
    with open("social_publish_payload.json","r",encoding="utf-8") as f:
        posts=json.load(f)
    today=datetime.now(WIB).date().isoformat()
    selected=[p for p in posts if str(p.get("date",""))==today and p.get("asset_url")]
    if not selected:
        print("No social posts due today.")
        return
    for p in selected:
        payload={
            "token":TOKEN,
            "action":"publish_social",
            "platform":str(p.get("platform","")).lower(),
            "image_url":p["asset_url"],
            "caption":str(p.get("caption",""))[:2200]
        }
        r=requests.post(WEBHOOK_URL,json=payload,timeout=120)
        r.raise_for_status()
        data=r.json()
        print(p.get("platform"),data)
        if not data.get("ok") and data.get("error") not in ("INSTAGRAM_NOT_CONFIGURED","TIKTOK_REFRESH_NOT_CONFIGURED","TIKTOK_ACCESS_NOT_CONFIGURED"):
            raise RuntimeError(data)
if __name__=="__main__":
    main()
