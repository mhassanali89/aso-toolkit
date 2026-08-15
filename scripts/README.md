# App Store Connect ASO scripts

Two scripts, one shared client, built from a real audit-and-fix pass on a live app
(see `.claude/skills/aso-audit/SKILL.md` for the full methodology). Reusable for any
app — nothing app-specific is hardcoded, everything comes from environment variables
or CLI arguments.

**Looking for the metadata upload script?** That's a separate repo:
[`appstore-connect-metadata-uploader`](https://github.com/mhassanali89/appstore-connect-metadata-uploader)
— writes Title/Subtitle/Keywords/etc. to App Store Connect from a CSV, with a
mandatory before/after diff and confirmation. This repo covers the *read* side:
pulling real performance data to inform what you'd put in that CSV.

## Setup

```bash
pip install pyjwt cryptography requests
```

Generate an App Store Connect API key: **App Store Connect → Users and Access →
Integrations → App Store Connect API → Generate**. **The key's role must be Admin.**
Narrower roles (Developer, Marketing, "Sales and Reports", etc.) will 403 on the
endpoints these scripts need — Sales/Analytics report requests both require Admin
specifically. Your own account being Admin doesn't matter; it's the role assigned
to the key itself.

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
- The Admin-role requirement is a real Apple constraint, not a script limitation —
  there's no narrower role that covers both Sales Reports and metadata writes.
