# Premium ASO Toolkit completely Free

Scripts and a reusable [Claude Code](https://claude.com/claude-code) skill for
**auditing** an iOS/macOS app's App Store Connect presence — pulling your
app's actual live Title/Subtitle/Keywords plus real download and subscription
history — so any ASO decision is based on **real App Store Connect data as
evidence**, not keyword-volume tools or guesswork.

This repo is read-only by design (it only ever pulls data, never writes to
your listing). Once you've decided what to change, the companion repo
[`appstore-connect-metadata-uploader`](https://github.com/mhassanali89/appstore-connect-metadata-uploader)
writes it — kept separate on purpose, so a tool that only reads your account
and a tool that writes to it are never the same install.

## What this README is for

This file exists to answer, in order: what problem this solves, whether it's
safe to point at your own app, how to set it up, and how the pieces fit
together. Read top to bottom the first time; after that, `scripts/README.md`
is the day-to-day reference for command syntax.

## The problem this solves

Most ASO advice is generic keyword theory. This toolkit instead:

- Pulls your app's **actual live** Title/Subtitle/Keywords from the API
  before proposing anything (planning docs and memory both drift from what's
  really live — this was learned the hard way, see the skill file).
- Pulls **real download and subscription history** (Sales Reports API — full
  history from app launch, not just "starting from today").
- Distinguishes what Apple actually exposes from what it doesn't: there is
  **no per-keyword impression/ranking data available anywhere**, from any
  API or the web UI, for the organic Keywords field. Any tool claiming to
  show you that for your own app is estimating, not reporting.

## Is this safe to use?

Yes — this repo only ever reads from your App Store Connect account, it
never writes to your listing (see the companion uploader repo for that, kept
separate so the two responsibilities can't be confused). Standard caveats
still apply:

- Nothing in this repo contains credentials, app IDs, or any
  account-specific data — every identifier is an environment variable or a
  CLI argument you supply.
- The API key this requires needs the **Admin** role. That's a real Apple
  constraint (Sales/Analytics report requests both require it), not
  something this toolkit imposes — treat that key with the same care as any
  other Admin credential.
- Read `.claude/skills/aso-audit/SKILL.md`'s "Mistakes already made" section
  before relying on this for a real release — it documents concrete errors
  made while building this (wrong report type, over-aggressive keyword
  removal) specifically so you don't repeat them.

## Setup

```bash
pip install pyjwt cryptography requests
```

Generate an App Store Connect API key: **App Store Connect → Users and
Access → Integrations → App Store Connect API → Generate**, role **Admin**.

```bash
export ASC_ISSUER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
export ASC_KEY_ID=XXXXXXXXXX
export ASC_PRIVATE_KEY_PATH=/path/to/AuthKey_XXXXXXXXXX.p8   # keep OUTSIDE any repo
export ASC_APP_ID=1234567890                                  # your app's numeric Apple ID
export ASC_VENDOR_NUMBER=12345678                              # Reports -> Sales and Trends (for pull_asc_sales.py only)
```

## What's included

| File | Purpose |
|---|---|
| `scripts/asc_client.py` | Shared JWT auth + a thin API wrapper. Everything else imports this. |
| `scripts/pull_asc_analytics.py` | Impressions / product page views / conversion. **Forward-only — no historical backfill**, see script docstring. |
| `scripts/pull_asc_sales.py` | Real download and subscription/revenue history, back to app launch. |
| `.claude/skills/aso-audit/SKILL.md` | The full audit methodology as a [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills) — drop this repo's `.claude/skills/` folder into your own project and Claude Code will use it automatically when asked to review ASO. Useful as a written methodology even if you don't use Claude Code. |

Ready to write the changes you've decided on? That's
[`appstore-connect-metadata-uploader`](https://github.com/mhassanali89/appstore-connect-metadata-uploader),
not this repo.

Full command reference and usage examples: [`scripts/README.md`](scripts/README.md).

## Contributing

Issues and PRs welcome — especially reports of new App Store Connect API
quirks (Apple's report types and states are not fully documented, and this
toolkit was built by hitting several of them directly).

## Disclaimer

Not affiliated with or endorsed by Apple. "App Store Connect" and "Apple
Search Ads" are trademarks of Apple Inc. Use at your own risk — this writes
to your live App Store Connect account when you tell it to.

## License

MIT — see [LICENSE](LICENSE).
