import os
import random
import smtplib
import ssl
import time
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

import requests

WIB = timezone(timedelta(hours=7))
SHEET_WEBHOOK_URL = os.environ["SHEET_WEBHOOK_URL"]
WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
AGENCY_NAME = os.getenv("AGENCY_NAME", "Sonjaya AI Sales Engine").strip()

DAILY_SEND_LIMIT = int(os.getenv("DAILY_SEND_LIMIT", "20"))
MAX_SEND_PER_RUN = int(os.getenv("MAX_SEND_PER_RUN", "6"))
SEND_DELAY_MIN = float(os.getenv("SEND_DELAY_MIN", "20"))
SEND_DELAY_MAX = float(os.getenv("SEND_DELAY_MAX", "45"))

def sheet_call(payload):
    response = requests.post(
        SHEET_WEBHOOK_URL,
        json={"token": WEBHOOK_TOKEN, **payload},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "Google Sheets action gagal."))
    return data

def send_one(smtp, lead):
    message = EmailMessage()
    message["From"] = f"{AGENCY_NAME} <{GMAIL_ADDRESS}>"
    message["To"] = lead["recipient_email"]
    message["Subject"] = lead["subject"]
    message["Reply-To"] = GMAIL_ADDRESS
    message.set_content(lead["body"])
    smtp.send_message(message)

def send_pending():
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "GMAIL_ADDRESS dan GMAIL_APP_PASSWORD belum dipasang di GitHub Secrets."
        )

    meta = sheet_call({"action": "queue", "limit": MAX_SEND_PER_RUN})
    sent_today = int(meta.get("sent_today", 0) or 0)
    remaining = max(0, DAILY_SEND_LIMIT - sent_today)

    if remaining <= 0:
        print(f"Daily send limit tercapai: {sent_today}/{DAILY_SEND_LIMIT}")
        return {"sent": 0, "remaining": 0}

    queue = meta.get("leads", [])[:min(MAX_SEND_PER_RUN, remaining)]
    if not queue:
        print("Tidak ada prospect READY ber-email.")
        return {"sent": 0, "remaining": remaining}

    context = ssl.create_default_context()
    sent = 0

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        context=context,
        timeout=45,
    ) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)

        for lead in queue:
            lead_id = lead.get("id", "")
            try:
                send_one(smtp, lead)
                sheet_call({
                    "action": "mark_sent",
                    "id": lead_id,
                    "sent_at": datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"),
                })
                sent += 1
                print(f"SENT {sent}/{len(queue)} -> {lead['recipient_email']}")
            except Exception as exc:
                print(f"ERROR -> {lead.get('recipient_email')}: {exc}")
                try:
                    sheet_call({
                        "action": "mark_error",
                        "id": lead_id,
                        "error": str(exc)[:500],
                    })
                except Exception as mark_exc:
                    print(f"Gagal menandai error: {mark_exc}")

            if sent < len(queue):
                time.sleep(random.uniform(SEND_DELAY_MIN, SEND_DELAY_MAX))

    return {
        "sent": sent,
        "remaining": max(0, DAILY_SEND_LIMIT - sent_today - sent),
    }

if __name__ == "__main__":
    print(send_pending())
