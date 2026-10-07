# Social Automation

The social layer is native API based; no ManyChat dependency.

## Instagram
The Apps Script handler supports:
- inbound Instagram DM auto-reply
- comment keyword detection (`REY MAU`)
- private DM reply to matching comments
- public comment reply
- 7-slide carousel auto-publishing

Required Apps Script properties:
- `IG_USER_ID`
- `IG_ACCESS_TOKEN`
- `IG_API_VERSION` (default `v26.0`)
- `IG_MESSAGING_HOST` (default `https://graph.instagram.com`)
- `META_VERIFY_TOKEN`
- `IG_COMMENT_KEYWORD` (default `REY MAU`)
- `IG_PUBLIC_COMMENT_REPLY` (default `Siap! 👋 Cek DM ya.`)

The Meta app needs the current Instagram Login scopes `instagram_business_basic`, `instagram_business_manage_messages`, `instagram_business_manage_comments`, and `instagram_business_content_publish`.

The Instagram webhook callback is the deployed Apps Script web app URL. The app must be configured to receive the relevant `messages` and `comments` events.

## TikTok
The Apps Script handler supports:
- inbound Business Messaging DM auto-reply
- `REY MAU` comment matching
- comment -> DM
- public comment reply
- 7-image TikTok photo-mode auto-publishing

Required Apps Script properties:
- `TIKTOK_ACCESS_TOKEN`
- `TIKTOK_COMMENT_KEYWORD` (default `REY MAU`)
- `TIKTOK_PUBLIC_COMMENT_REPLY` (default `Siap! 👋 Cek DM ya.`)

TikTok direct photo posting uses the current Content Posting API v2. The photo URLs must be public and the URL prefix/domain must be verified by TikTok. Public visibility also depends on the app/account authorization and audit state.

## Daily auto-posting
`.github/workflows/content-daily.yml` runs daily at 08:47 WIB. It:
1. generates the 7-day plan,
2. renders 7-slide JPEG carousel assets,
3. pushes the public assets to GitHub,
4. publishes today's carousel to Instagram and TikTok through Apps Script,
5. records publish results in `Content Planning`.

Only today's content is published on each run. The other six days remain scheduled/planned.

## Live deployment
After updating `apps-script/Code.gs`, deploy the new Apps Script version as a Web App. The expected version is `2026-10-07.7`.

Never put access tokens, client secrets, or refresh tokens in GitHub source files or chat messages.

