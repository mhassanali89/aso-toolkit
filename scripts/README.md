# App Store Connect ASO scripts

Three scripts, one shared client, built from a real audit-and-fix pass on a live app
(see `.claude/skills/aso-audit/SKILL.md` for the full methodology). Reusable for any
app — nothing app-specific is hardcoded, everything comes from environment variables
or CLI arguments. One of the three (`keyword_research.py`) needs no App Store Connect
access at all — see its own section below before assuming you need an API key to get
started.

**Looking for the metadata upload script?** That's a separate repo:
[`appstore-connect-metadata-uploader`](https://github.com/mhassanali89/appstore-connect-metadata-uploader)
— writes Title/Subtitle/Keywords/etc. to App Store Connect from a CSV, with a
mandatory before/after diff and confirmation. This repo covers the *read* side:
pulling real performance data to inform what you'd put in that CSV.

## `keyword_research.py` — keyword scoring, competitors, validation (no credentials)

Runs entirely against Apple's public, unauthenticated iTunes Search API plus local
logic — nothing here touches your App Store Connect account, so there's no API key
to set up for this one.

```bash
pip install requests

# Score candidate keywords (popularity/difficulty/opportunity — see the script's
# docstring for exactly how these are computed; they're estimates, not real
# Apple performance data for any specific app)
python3 keyword_research.py score "voice notes,note taking,transcription" --country us

# Real apps currently ranking for a search term
python3 keyword_research.py competitors "note taking app" --country us --limit 10

# Character limits + cross-field word-stem duplication — pure local check,
# no network call at all
python3 keyword_research.py validate --title "..." --subtitle "..." --keywords "..."
```

The scoring formula is an original implementation, not a port of any
third-party tool's algorithm — see the script's docstring for the exact
signals it uses (result count, top-10 average rating count, exact-title
match ratio) and why.

## Setup (for the two scripts below — App Store Connect access required)

```bash
pip install pyjwt cryptography requests
```

Generate an App Store Connect API key: **App Store Connect → Users and Access →
Integrations → App Store Connect API → Generate**. **Give it access to Sales and
Analytics reporting** (Apple calls this tier "Admin" in the role picker). Narrower
roles (Developer, Marketing, "Sales and Reports," etc.) will 403 on the endpoints
these scripts need — Sales and Analytics report requests specifically require that
tier. Your own account's role doesn't matter here; it's the role assigned to the
key itself that gates these calls.

Set environment variables (never commit the `.p8` file):

```bash
export ASC_ISSUER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx   # shown next to your keys
export ASC_KEY_ID=XXXXXXXXXX                                  # the key's ID
export ASC_PRIVATE_KEY_PATH=/path/to/AuthKey_XXXXXXXXXX.p8    # keep this OUTSIDE the repo
export ASC_APP_ID=1234567890                                  # your app's numeric Apple ID
export ASC_VENDOR_NUMBER=12345678                              # Reports -> Sales and Trends, top of page (only needed for pull_asc_sales.py)
```

## `pull_asc_analytics.py` — impressions, page views, conversion

Creates (or reuses) an ONGOING analytics report request and downloads the ASO-relevant
report segments as TSV. **Important limitation:** this only captures data going
*forward* from when the request is first created — Apple does not backfill history
through this endpoint. If you want a full history of impressions/conversion, you'll
need to wait for this to accumulate, or pull it from the App Store Connect web UI's
Analytics/Trends export (no API for that).

```bash
python3 pull_asc_analytics.py
```

## `pull_asc_sales.py` — real download & subscription history

A *different* API (Sales Reports) that, unlike the one above, has full history from
day one — Apple generates a report for every past day regardless of when you first
ask for it.

```bash
# Monthly download/unit history
python3 pull_asc_sales.py downloads --from 2025-08 --to 2026-07

# Daily subscription events (trial starts, conversions, renewals, refunds)
# — slow: Apple only exposes this report one day at a time, no batching.
python3 pull_asc_sales.py subscribers --from 2025-08-13 --to 2026-08-13
```

**Gotcha we hit for real:** subscription/IAP revenue does **not** show up in the
`SALES`/`SUMMARY` report at all — only base-app unit downloads do. Querying that
report and finding zero subscription rows does **not** mean zero revenue; it means
you queried the wrong report. Use the `SUBSCRIBER` report (`subscribers` subcommand)
for actual subscription/IAP activity.

## Notes for reuse in other apps / a public repo

- Nothing here hardcodes an app name, bundle ID, or Apple ID — every identifier comes
  from env vars or `--app-id`.
- `.gitignore` already excludes `scripts/*.p8` and `scripts/asc_reports/` — keep it
  that way if you fork this.
- Needing access to Sales and Analytics reporting is a real Apple constraint, not
  a script limitation — there's no narrower key role that covers both report
  types these scripts pull.
