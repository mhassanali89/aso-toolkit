---
name: aso-audit
description: Audit and update an app's App Store Connect metadata (Title, Subtitle, Keywords, Promotional Text, Description) using real App Store Connect data as evidence rather than guessing. Use when the user asks to review/optimize ASO before shipping a build, asks for keyword or metadata suggestions, wants a new locale added, or is setting up a brand-new listing.
---

# ASO audit and metadata push

A methodology for App Store ASO decisions grounded in real data pulled from
the App Store Connect API, not keyword-volume tools, generic "best practice"
lists, or guesswork. Applies to an established app being audited before a
new release, a brand-new listing being set up for the first time, or a new
locale being added to an existing one — the "pull real data first, change
only with a defensible reason" posture holds in all three cases; only the
baseline you're comparing against differs (existing live copy vs. nothing
yet).

## The job is an audit, not a rewrite

For an app with existing live metadata, the default posture is **KEEP unless
there's a specific, defensible reason to change something.** Do not propose
a fresh keyword strategy from theory. Do not touch a field just because a
character budget has room left — an unused character costs nothing; a
wrong-intent keyword or a stem-duplicated word actively wastes indexed space
that a real term could have used.

Every change you propose must trace to one of:
1. A structural defect you can point to concretely (duplicate word-stem
   between Title and Subtitle, a malformed/garbled keyword entry, wrong
   script for the locale, a word from the wrong language sitting in a field,
   a keyword implying a feature the app doesn't have).
2. Real ASC data (downloads, subscriber events, territory concentration) —
   see below for what's actually retrievable and what isn't.
3. An objectively new fact with no possible historical precedent (e.g. a
   new platform launching this release — nobody could have searched for it
   before now, so the absence of historical evidence isn't evidence against it).

If none of the three apply, say "no defect found, KEEP" and move on. A
locale's keyword field sitting well under the character limit with no bad
terms in it is a finished result, not an unfinished one.

**For a brand-new listing or locale**, there's no existing copy to default
to keeping, so the bar shifts: every field needs to be earned from real
competitor research and verified app features, not filled to look complete.
Still pull whatever real data exists (competitor listings, category
conventions) rather than writing from pure instinct.

## Step 1 — pull real ground truth before doing anything

Never trust a prior planning doc, a "locked" table written earlier, or
memory of the app's metadata as if it were live. Pull the actual current
state from the API every time — planning docs and human memory both drift
from what's really live, sometimes substantially, and there's no way to
know how much until you check:

```bash
cd scripts
python3 - <<'PY'
from asc_client import Client
c = Client()
app_id = "<ASC_APP_ID>"

# Title/Subtitle (shared across platforms) — check EVERY appInfo record,
# there is usually a READY_FOR_SALE one (what's actually live) and a
# PREPARE_FOR_SUBMISSION one (the draft you'd edit for the next release).
for info in c.get(f"/apps/{app_id}/appInfos")["data"]:
    print(info["id"], info["attributes"]["appStoreState"])
    for loc in c.get(f"/appInfos/{info['id']}/appInfoLocalizations")["data"]:
        a = loc["attributes"]
        print(" ", a["locale"], repr(a["name"]), repr(a["subtitle"]))

# Keywords/Description/PromoText/WhatsNew — per platform version
for v in c.get(f"/apps/{app_id}/appStoreVersions", params={"limit": 50})["data"]:
    print(v["id"], v["attributes"]["platform"], v["attributes"]["versionString"],
          v["attributes"]["appStoreState"])
PY
```

Concretely, this check catches things a planning doc never will: a locale
whose Title/Subtitle is still an untranslated placeholder from setup, a
keyword field with garbled entries from a bad copy-paste, or metadata that
simply drifted from whatever was last "decided" weeks or months ago because
someone edited it directly in App Store Connect since. None of that is
visible without pulling live data first.

## Step 2 — real performance data: what you can and can't get

Two different APIs, with a critical difference in how far back they reach:

- **Analytics Reports API** (impressions, product page views, conversion
  rate) — `pull_asc_analytics.py`. This is an ONGOING subscription: it only
  captures data from the moment you first create the report request
  *forward*. **It does not backfill history**, not even a day of it. If
  this is the first time a report request has been created for the app, you
  have zero historical impression data available via API, full stop — say
  so plainly rather than working around it.
- **Sales Reports API** (downloads, revenue, subscriptions) —
  `pull_asc_sales.py`. This one has full history from app launch, because
  Apple generates these regardless of whether anyone asked. Needs
  `ASC_VENDOR_NUMBER` (App Store Connect → Reports → Sales and Trends, shown
  at the top of the page).

**A gotcha worth knowing before you go looking for revenue data:**
subscription/IAP revenue does **not** appear in the `SALES`/`SUMMARY` report
— only base-app unit downloads do. An empty result there is not evidence of
zero revenue; it's evidence of the wrong report. Use the `SUBSCRIBER` report
(daily-only, no weekly/monthly option) for real subscription events. If a
finding as significant as "this app has zero revenue" comes up, that's
exactly the moment to double-check via a second method before stating it as
fact.

**What Apple does not expose to anyone, in any channel:** per-keyword
impression or ranking data for the organic Keywords field. Not via API, not
via the App Store Connect UI. If asked to say which keyword is "close to
ranking well," say clearly that this specific number doesn't exist anywhere
— don't approximate it with a keyword-volume tool and present it as the
app's own performance data. Apple Search Ads "Search Popularity" is a demand
signal, not a performance number, and only covers paid-campaign search
terms, not the organic Keywords field.

## Step 3 — the actual audit, field by field

**Title.** Almost never worth changing on an established app. It's the
highest-weight search field and the most user-facing — a full rewrite risks
resetting accumulated ranking signal for a marginal keyword gain. Only touch
it for a concrete defect (untranslated placeholder, wrong script) or an
explicit repositioning request.

**Subtitle.** Check for stem-duplication with Title first (e.g. Title ends
in a word like "Notes," Subtitle contains the same stem again) — same
indexed stem, wasted space. Fix only that specific overlap; don't rewrite
the rest.

**Keywords.** This is where real defects hide, and they're mechanical, not
strategic:
- Redundant stems within the same field (two forms of the same root word)
  — keep one, not both.
- A phrase sliced into meaningless single-word fragments by stray commas —
  a multi-word phrase like "voice notes" accidentally split into "voice",
  "notes" as two separate list entries when it should have stayed one
  phrase (or vice versa: single words wrongly merged). Reconstruct what a
  person would actually type.
- Wrong script for the locale (e.g. Simplified characters under a
  Traditional Chinese field).
- A word from a different language entirely sitting in the field.
- Stray whitespace inside a term that breaks an exact brand match (a
  competitor's name with an accidental space in it won't match anyone
  searching the real name).
- Grammatical fragments, not real search terms (verb-conjugation endings or
  particles that no one would type into search on their own).
- A keyword implying a feature the app doesn't actually have — verify
  against the app's real feature set before adding anything, not just
  before removing something. A keyword that draws in the wrong searcher
  intent (someone looking for a feature this app doesn't do) converts
  worse than an unused character.

**Competitor names in Keywords — the correct lens.** Two opposite mistakes
are both easy to make here:
- *Too narrow:* dropping a competitor name because its core mechanism
  differs from this app's (e.g. a handwriting note-taking app kept out of
  the list for an app that does AI audio transcription). Wrong lens — if
  both apps are competing for the same "which app in this category do I
  install" decision in a searcher's head, they're the same race and the
  keyword is valid. Judge by the category the searcher is shopping in, not
  by feature-level mechanism matching.
- *Too aggressive:* dropping small/niche competitor names on the theory
  that their owner defends the exact-match term with paid search ads, so
  organic ranking under it has poor payback. This is a real, legitimate
  consideration for *new* keyword candidates you're deciding whether to add
  — but it's a guess about ad behavior that can't be verified, and applying
  it to remove long-standing live keywords with an actual track record
  violates the KEEP-bias rule. Absence of proof isn't proof of absence.
- A competitor name that can't be verified as a real app (no matching store
  listing found) is worth flagging, but don't remove it unilaterally if
  it's already live — you can't prove a negative, and removing a term that
  happens to work anyway is a real cost with no offsetting evidence.

**Promotional Text.** Free to edit any time, even on an already-live
version, no App Review needed. If it's empty, that's close to always worth
filling — unused real estate with essentially no downside. A platform
launch (new OS, new device class) is a good, low-risk, always-justified
reason to write one even with zero historical data, for the same
can't-have-evidence-for-a-thing-that-didn't-exist-yet reason platform
keywords are justified.

**Description.** Apple does not index this for search — only conversion.
Don't touch it without a specific, stated reason; "already comprehensive and
accurate" is a legitimate reason to leave it alone.

**Screenshots.** Can't be judged from data available via this API — no
impression/conversion breakdown by screenshot exists. Check
programmatically whether each locale *has* a screenshot set at all
(`GET /appStoreVersionLocalizations/{id}/appScreenshotSets` →
`.../{setId}/appScreenshots`) — a locale with zero screenshots is a hard
submission blocker you can catch this way, distinct from judging whether
existing screenshots are good.

## Step 4 — present findings, then push only with explicit confirmation

Show every proposed change as a before/after pair, grouped by locale, before
touching anything. The actual write is a separate tool on purpose — this
skill's scripts only ever read from App Store Connect. Use
[`push_aso_metadata.py`](https://github.com/mhassanali89/appstore-connect-metadata-uploader)
for the write step — it already enforces this: full diff first,
character-limit validation, explicit confirmation prompt (or `--yes` if the
user has said to just proceed).

Never invent a value to fill a blank field "for completeness" — leave it
blank and say what's missing (e.g. "no promo text drafted yet for these
locales") rather than writing something to make a report look more
finished.

## Common pitfalls

1. Trusting a "locked" table or planning doc as if it were live metadata,
   without pulling the real current state first. It frequently won't match
   — see Step 1.
2. Character-count errors from hand-tracing Unicode strings — always
   validate with `len()` in a script, never by eye, especially for
   CJK/Arabic/Vietnamese diacritics.
3. Concluding "zero revenue" (or any major finding) from a single query
   without checking whether it's actually the right report/endpoint for
   that data — see the Sales vs. Subscriber report gotcha in Step 2.
4. Removing a competitor keyword using too literal a definition of
   "competitor" — same search category and audience is the right test, not
   whether the underlying mechanism matches.
5. Adding a keyword that sounds plausible for the app's category without
   verifying it against the app's actual feature set — a keyword implying a
   feature the app doesn't have pulls in the wrong searcher intent, which
   converts worse than leaving the space unused.
6. Treating "fill every field to the character limit" as the goal. It
   isn't — a real, justified term left unused space is a better result than
   a filler term that used it. Character utilization is a byproduct of
   finding real terms, never a target to hit for its own sake.

## Scripts this skill uses

In this repo (read-only — pulls data, never writes):
- `scripts/asc_client.py` — shared JWT auth (requires an **Admin-role** API
  key — narrower roles 403 on report requests and metadata writes).
- `scripts/pull_asc_analytics.py` — impressions/conversion (forward-only,
  no backfill).
- `scripts/pull_asc_sales.py` — real download and subscription history
  (`downloads` and `subscribers` subcommands).

In the companion repo (the write step, kept separate on purpose):
- [`appstore-connect-metadata-uploader`](https://github.com/mhassanali89/appstore-connect-metadata-uploader)'s
  `push_aso_metadata.py` — CSV/URL → App Store Connect, with mandatory
  before/after diff and confirmation.

See `scripts/README.md` for setup and environment variables.
