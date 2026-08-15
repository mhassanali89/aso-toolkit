# Premium ASO Toolkit completely Free

Research, audit, and validate an iOS/macOS app's App Store presence —
Title, Subtitle, Keywords — grounded in real data wherever real data
exists, and honest about it when it doesn't. A reusable
[Claude Code](https://claude.com/claude-code) skill drives the decision
process; the scripts underneath it do the actual data pulling.

**You don't need an App Store Connect account to get value from this.**
Keyword scoring, competitor research, and metadata validation run entirely
on Apple's public data — no credentials, no setup beyond `pip install`. If
you *do* connect your App Store Connect account, the same workflow gets
sharper: it audits against your app's actual live listing and real
download/subscription history instead of market research alone. Both modes
are real, complete, and yours to choose — see [Two ways to use this](#two-ways-to-use-this)
below.

This repo is read-only by design (it only ever pulls data, never writes to
your listing). Once you've decided what to change, the companion repo
[`appstore-connect-metadata-uploader`](https://github.com/mhassanali89/appstore-connect-metadata-uploader)
writes it — kept separate on purpose, so a tool that only reads your account
and a tool that writes to it are never the same install.

## What this README is for

This file exists to answer, in order: what problem this solves, the two
ways you can use it, whether it's safe to point at your own app, how to set
it up, and how the pieces fit together. Read top to bottom the first time;
after that, `scripts/README.md` is the day-to-day reference for command
syntax.

## The problem this solves

Most ASO advice is generic keyword theory, and most ASO tools ask for
account access before you've even decided if they're useful. This toolkit
instead:

- Works with **zero account access** for research and validation — score
  candidate keywords, pull real competitor apps, and check your
  Title/Subtitle/Keywords against Apple's limits, all before you've
  connected anything.
- When you do connect an account, pulls your app's **actual live**
  Title/Subtitle/Keywords from the API before proposing anything — planning
  docs and memory both drift from what's really live, often more than
  expected.
- Pulls **real download and subscription history** (Sales Reports API — full
  history from app launch, not just "starting from today").
- Distinguishes what Apple actually exposes from what it doesn't: there is
  **no per-keyword impression/ranking data available anywhere**, from any
  API or the web UI, for the organic Keywords field. Any tool claiming to
  show you that for your own app is estimating, not reporting — including
  this one's own keyword scoring, which is clearly labeled as an estimate
  every time it's shown.

## Two ways to use this

| | No credentials | With App Store Connect |
|---|---|---|
| **Keyword scoring** (popularity/difficulty/opportunity estimate) | ✅ | ✅ |
| **Competitor research** (real apps ranking for a term, right now) | ✅ | ✅ |
| **Title/Subtitle/Keywords validation** (limits, duplication) | ✅ | ✅ |
| **Audit against *your app's* actual live metadata** | — | ✅ |
| **Real download/subscription history**, back to launch | — | ✅ |
| **Setup required** | `pip install requests` | Above, plus an Admin-role API key |

Why ask for App Store Connect access at all, if the left column already
works? Accuracy. The no-credentials tier tells you about the market — what
terms are competitive, what similar apps are doing, whether a candidate
Title fits within Apple's limits. It cannot tell you whether *your specific
app* is already using its indexed space well, whether a keyword you're
about to add duplicates one already live, or whether your download/revenue
trend actually supports a change. That second half requires reading your
real account. If you don't want to grant that access, say so — the toolkit
(and the skill driving it) is built to keep working in the no-credentials
tier rather than stall out waiting for a key, and any recommendation it
gives will be clearly grounded in market research rather than presented as
if it came from your account.

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
- Read `.claude/skills/aso-audit/SKILL.md`'s "Important behavioral rules"
  section before relying on this for a real release — it's a concise list
  of what the audit must never do (invent evidence, fill fields with
  filler, assume Apple exposes data it doesn't).

## Setup

**No-credentials tier** — just the one dependency:

```bash
pip install requests
```

```bash
python3 scripts/keyword_research.py score "your,candidate,keywords" --country us
python3 scripts/keyword_research.py competitors "a search term" --country us
python3 scripts/keyword_research.py validate --title "..." --subtitle "..." --keywords "..."
```

**Full tier** — adds App Store Connect access:

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

| File | Purpose | Needs App Store Connect? |
|---|---|---|
| `scripts/keyword_research.py` | Keyword scoring, competitor lookup, and local Title/Subtitle/Keywords validation — all via Apple's public iTunes Search API plus local logic. | No |
| `scripts/asc_client.py` | Shared JWT auth + a thin API wrapper. Everything below imports this. | — |
| `scripts/pull_asc_analytics.py` | Impressions / product page views / conversion. **Forward-only — no historical backfill**, see script docstring. | Yes (Admin) |
| `scripts/pull_asc_sales.py` | Real download and subscription/revenue history, back to app launch. | Yes (Admin) |
| `.claude/skills/aso-audit/SKILL.md` | The full ASO methodology as a [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills), scoped specifically to Title/Subtitle/Keywords — covers both auditing an existing app's live metadata and building initial ASO for a brand-new listing, in both credential tiers. Drop this repo's `.claude/skills/` folder into your own project and Claude Code uses it automatically when asked to review ASO. Useful as a written methodology even if you don't use Claude Code. |

Ready to write the changes you've decided on? That's
[`appstore-connect-metadata-uploader`](https://github.com/mhassanali89/appstore-connect-metadata-uploader),
not this repo.

Full command reference and usage examples: [`scripts/README.md`](scripts/README.md).

## Contributing

Issues and PRs welcome — especially reports of new App Store Connect API
quirks (Apple's report types and states are not fully documented, and this
toolkit was built by hitting several of them directly).

## Disclaimer

Not affiliated with or endorsed by Apple. "App Store Connect" is a trademark
of Apple Inc. This repo only ever reads from your App Store Connect account
— see the companion uploader repo's disclaimer if you're using that one,
since that's the tool that writes. Keyword scoring is an estimate from
public search-result data, not a real Apple performance metric — see
`.claude/skills/aso-audit/SKILL.md` for why that distinction is treated as
important throughout this project.

## License

MIT — see [LICENSE](LICENSE).
