# AI Prospecting Agency — Indonesia

Search:
TinyFish Search API

AI:
Gemini 3.6 Flash

Database:
Google Sheets via Apps Script Web App

Automation:
GitHub Actions

## GitHub Secrets

Existing:
- GEMINI_API_KEY
- SHEET_WEBHOOK_URL
- WEBHOOK_TOKEN

New:
- TINYFISH_API_KEY

## Volume

8 search queries per scheduled run.
4 scheduled runs per day.
Up to 100 candidates sent to Gemini per run.

The actual result depends on search results, duplicate filtering,
rate limits, and Gemini quota.

## Schedule (WIB)

02:00
08:00
14:00
20:00

## Search

Queries rotate through Indonesian cities and business niches,
with intent terms such as WhatsApp, booking, order, and link in bio.

The system does not log into Instagram and does not send DMs.
The output is for manual, relevant outreach.
