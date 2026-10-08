from __future__ import annotations
import os, sys, requests
from google import genai

EXPECTED_APPS_SCRIPT_VERSION = os.getenv("EXPECTED_APPS_SCRIPT_VERSION", "2026-10-08.2")

def need(name):
    value=os.getenv(name,"").strip()
    if not value:
        print("MISSING",name)
        return False
    print("OK",name)
    return True

ok=True
for name in ("GEMINI_API_KEY","SHEET_WEBHOOK_URL","WEBHOOK_TOKEN"):
    ok=need(name) and ok

if ok:
    try:
        r=requests.get(os.environ["SHEET_WEBHOOK_URL"],timeout=30)
        print("SHEET_HTTP",r.status_code,r.text[:500])
        if r.status_code>=300: ok=False
    except Exception as e:
        print("SHEET_ERROR",type(e).__name__,e)
        ok=False

    try:
        r=requests.post(
            os.environ["SHEET_WEBHOOK_URL"],
            json={"token":os.environ["WEBHOOK_TOKEN"],"action":"healthcheck"},
            timeout=30,
        )
        print("APPS_SCRIPT_HEALTH_HTTP",r.status_code,r.text[:800])
        data=r.json()
        if r.status_code>=300 or not data.get("ok"):
            ok=False
        elif data.get("version") != EXPECTED_APPS_SCRIPT_VERSION:
            print("APPS_SCRIPT_VERSION_MISMATCH",data.get("version"),"expected",EXPECTED_APPS_SCRIPT_VERSION)
            ok=False
    except Exception as e:
        print("APPS_SCRIPT_HEALTH_ERROR",type(e).__name__,e)
        ok=False

    try:
        client=genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response=client.models.generate_content(
            model=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite"),
            contents="Reply only OK"
        )
        print("GEMINI_TEST",str(response.text or "").strip()[:100])
    except Exception as e:
        print("GEMINI_ERROR",type(e).__name__,e)
        ok=False

    print("SOCIAL_AUTOMATION", "DISABLED_BY_DESIGN")

print("HEALTH", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
