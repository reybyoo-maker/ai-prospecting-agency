# Sales Engine

## Objective
Run prospect discovery and outbound sales on a fixed 2-hour cadence without manual sending.

## Runtime flow
1. GitHub Actions starts every 2 hours.
2. `prospecting_engine.py` discovers public business emails, enriches evidence, scores each candidate with Gemini, and ingests only valid leads into Google Sheets.
3. The same workflow calls Apps Script `sales_cycle`.
4. Apps Script first scans inbound replies so replied leads are excluded from later follow-ups.
5. Apps Script sends up to 30 new `READY` initial emails, highest score first.
6. Apps Script processes due follow-ups with the remaining email quota.
7. The state is recorded in `Prospects`.

## Lead lifecycle
`READY -> SENT -> FOLLOWUP_1 -> FOLLOWUP_2 -> FOLLOWUP_3 -> FOLLOWUP_DONE`

Reply:
`SENT/FOLLOWUP_* -> WA_HANDOFF`

Opt-out:
`any active status -> OPTOUT`

## Sending safeguards
- Public email required.
- Duplicate email suppressed at ingestion.
- `UNSUBSCRIBE` stops future follow-ups.
- Per-row attempts are bounded.
- Document lock protects concurrent sends.
- Subject contains a stable Lead ID.
- MailApp remaining quota is checked before sending.
- A run never intentionally bypasses Google sending limits.

## Cadence
GitHub Actions uses POSIX cron for the 2-hour schedule. Scheduled runs can be delayed by GitHub during high system load; the cadence is therefore a target interval, not a second-precise guarantee.

## Google account capacity
The system targets 30 initial outreach emails per cycle. Actual volume is capped by the Google account's remaining MailApp quota. Consumer Apps Script accounts currently have 100 email recipients/day; Google Workspace currently has 1,500 recipients/day. These quotas are platform limits and can change.
