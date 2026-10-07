# Content Studio

## Objective
Create high-quality feed content for manual upload. No social API publishing is part of this flow.

## Runtime flow
`Gemini strategy -> 7-day plan -> 7-slide scripts -> visual rendering -> PNG/JPG/PDF -> GitHub assets -> Google Sheets`

## Content standard
Each day has:
- one clear audience problem,
- one strong hook,
- one central insight,
- one practical framework,
- one realistic business example,
- one mistake/objection section,
- one actionable CTA.

The seven-day plan rotates content pillars:
1. Lead Generation & Prospecting
2. Sales Follow-up & Conversion
3. Customer Support & WhatsApp
4. Social Media & Content Operations
5. Admin & Back-office Automation
6. Research, Data & Reporting
7. Appointment Setting & Retention

## Design standard
- 1080x1350 feed canvas.
- Blue, light blue, white, navy palette.
- Seven visual families so the week does not look repetitive.
- Strong typography hierarchy.
- Generous whitespace.
- Robot/mascot used as a recognizable brand element, not as decoration on every corner.
- Every slide has a clear visual role and a functional visual device.
- No walls of text.

## Quality gate
The generator fails the run rather than silently accepting weak output when:
- the seven-day set is incomplete,
- topics repeat,
- slide roles are wrong,
- slide text is too short/long,
- hook or CTA is missing,
- required visual direction is missing.

This prevents low-quality content from being presented as ready.

## Spreadsheet output
`Content Planning` stores:
- topic/pillar
- hook
- caption
- CTA
- full slide script
- PDF
- cover
- Slide 1-7 image URLs
- status
- manual-upload mode

Status:
`READY_FOR_MANUAL_UPLOAD`

## Manual publishing
The content team downloads/opens the prepared assets and uploads them manually to Instagram/TikTok. The repository has no active auto-publish workflow.
