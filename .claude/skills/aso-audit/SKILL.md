---
name: aso-audit
description: Audit and update this app's App Store Connect metadata (Title, Subtitle, Keywords, Promotional Text, Description) for a new release, using real App Store Connect data as evidence rather than guessing. Use when the user asks to review/optimize ASO before shipping a build, asks for keyword or metadata suggestions, or wants a new locale added.
---

# ASO audit and metadata push

This skill exists because we already ran this process once, by hand, and hit
real mistakes worth not repeating. Read the whole thing before starting — the
"Mistakes already made" section at the end is not optional reading, it's the
reason half these rules exist.

## The job is an audit, not a rewrite

The user already has a live app with real history. The default posture is
**KEEP unless there's a specific, defensible reason to change something.**
Do not propose a fresh keyword strategy from theory or "best practice" lists.
Do not touch a field just because a character budget has room left — an
unused character costs nothing; a wrong-intent keyword or a stem-duplicated
word actively wastes indexed space that a real term could have used.

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
locale's keyword field sitting at 65/100 with no bad terms in it is a
finished result, not an unfinished one.

## Step 1 — pull real ground truth before doing anything

Never trust a prior planning doc, a "locked" table someone wrote earlier, or
your own memory of the app's metadata as if it were live. Pull the actual
current state from the API every time:

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

**What actually happened the one time we skipped this:** an earlier planning
document claimed 14 locales' Title/Subtitle were "locked" and ready. None of
it matched what was actually live — the real app had a completely different
title in nearly every locale, two locales (one Traditional Chinese, one
English variant) were showing an untranslated placeholder, and the real
Mac-draft keyword field had bugs (wrong script, garbled entries, a stray
French word in a Spanish field) that no planning doc could have caught
because no one had looked at the live data. An hour of confident-sounding
work was thrown out once the real pull happened. Pull first.

## Step 2 — real performance data: what you can and can't get

Two different APIs, with a critical difference in how far back they reach:

- **Analytics Reports API** (impressions, product page views, conversion
  rate) — `pull_asc_sales.py`'s sibling, `pull_asc_analytics.py`. This is an
  ONGOING subscription: it only captures data from the moment you first
  create the report request *forward*. **It does not backfill history**, not
  even a day of it. If this is the first time a report request has been
  created for the app, you have zero historical impression data available
  via API, full stop — say so plainly rather than working around it.
- **Sales Reports API** (downloads, revenue, subscriptions) —
  `pull_asc_sales.py`. This one has full history from app launch, because
  Apple generates these regardless of whether anyone asked. Needs
  `ASC_VENDOR_NUMBER` (App Store Connect → Reports → Sales and Trends, shown
  at the top of the page).

**The mistake to not repeat:** subscription/IAP revenue does **not** appear
in the `SALES`/`SUMMARY` report — only base-app unit downloads do. Querying
that report and finding zero subscription-product rows is not evidence of
zero revenue; it's evidence you queried the wrong report. Use the
`SUBSCRIBER` report (daily-only, no weekly/monthly option) for real
subscription events. We reported "$0 revenue, probably a broken paywall" to
the user based on the wrong report, and had to walk it back after the user
pushed back — real revenue existed the whole time. Check both report types,
and if a finding as significant as "zero revenue" comes up, that's exactly
the moment to double-check via a second method before saying it out loud.

**What Apple does not expose to anyone, in any channel:** per-keyword
impression or ranking data for the organic Keywords field. Not via API, not
via the App Store Connect UI. If the user's brief assumes you can tell them
"keyword X is close to ranking well," say clearly that this specific number
doesn't exist anywhere — don't approximate it with a keyword-volume tool and
present it as if it were the app's own performance data. Apple Search Ads
"Search Popularity" is a demand signal, not a performance number, and only
covers paid-campaign search terms, not the organic Keywords field.

## Step 3 — the actual audit, field by field

**Title.** Almost never worth changing. It's the highest-weight search field
and the most user-facing — a full rewrite risks resetting a year of
accumulated ranking signal for a marginal keyword gain. Only touch it for a
concrete defect (untranslated placeholder, wrong script) or if the user
explicitly asks for a repositioning.

**Subtitle.** Check for stem-duplication with Title first (e.g. Title ends
in "Note Taker", Subtitle contains "Notes" — same indexed stem, wasted
space). Fix only that specific overlap; don't rewrite the rest.

**Keywords.** This is where real defects hide, and they're mechanical, not
strategic:
- Redundant stems within the same field (`Summarize` + `Summarizer`,
  `Notiz` + `Notizen`) — keep one, not both.
- A phrase that got sliced into meaningless single-word fragments by stray
  commas (`Not,Alma,Sesli,Sesi,Notlar,Notu` was actually three real Turkish
  phrases — `Not Alma`, `Sesli Notlar`, `Metinden Sese` — before someone
  split them wrong). Rejoin into what a person would actually type.
- Wrong script for the locale (Simplified characters under a Traditional
  Chinese field).
- A word from a different language entirely sitting in the field (French
  "Réunion" found inside a Spanish keyword list).
- Stray whitespace inside a term that breaks an exact brand match
  (`Notebook lm` doesn't match anyone searching `NotebookLM`).
- Grammatical fragments, not real search terms (Japanese verb-conjugation
  endings like `を文字化` aren't things anyone types into search).

**Competitor names in Keywords — the correct lens.** Two real, opposite
mistakes happened here in the same session, in both directions:
- *Too narrow:* dropping a competitor name because its core mechanism
  differs (e.g. a handwriting note-taking app, when this app does AI audio
  transcription). Wrong lens — if both apps are competing for the same
  "which note-taking app do I install" decision in a searcher's head, they're
  the same race and the keyword is valid. Judge by the category the searcher
  is shopping in, not by feature-level mechanism matching.
- *Too aggressive:* dropping small/niche competitor names on the theory that
  their owner defends the exact-match term with paid Apple Search Ads, so
  organic ranking under it has poor payback. This is a real, legitimate
  consideration, but it is a *guess* about ad behavior we cannot verify —
  applying it to remove long-standing live keywords with an actual track
  record violates the KEEP-bias rule. It's fine reasoning for *new* keyword
  candidates you're deciding whether to add; it is not sufficient reason
  to remove something that's already there and already performing
  (even "performing" in the loose sense of "has been live a year and the
  app still gets downloads" — absence of proof isn't proof of absence).
- A name you can't verify is a real app (no matching App Store listing found
  in research) is worth flagging to the user, but don't remove it
  unilaterally if it's already live — you can't prove a negative, and
  removing a term that happens to work anyway is a real cost with no
  offsetting evidence.

**Promotional Text.** Free to edit any time, even on an already-live
version, no App Review needed. If it's empty, that's close to always worth
filling — it's unused real estate with essentially no downside. A platform
launch (new OS, new device class) is a good, low-risk, always-justified
reason to write one even with zero historical data, for the same "can't have
historical evidence for a thing that didn't exist yet" reason platform
keywords are justified.

**Description.** Apple does not index this for search — only conversion.
Don't touch it without a specific, stated reason; "already comprehensive and
accurate" is a legitimate reason to leave it alone.

**Screenshots.** Can't be judged from data you have access to as an agent —
no impression/conversion breakdown by screenshot exists via this API. Check
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
user has told you to just proceed).

Never invent a value to fill a blank field "for completeness" — leave it
blank and say what's missing (e.g. "no promo text drafted yet for these 6
locales") rather than writing something to make a report look more finished.

## Mistakes already made in this exact workflow — don't repeat these

1. Built 14 locales of Title/Subtitle/Keywords from a planning doc's "locked"
   table without ever pulling the real live data first. None of it matched.
2. Character-count errors from hand-tracing Unicode strings — always
   validate with `len()` in a script, never by eye, especially for
   CJK/Arabic/Vietnamese diacritics.
3. Reported "$0 subscription revenue" from the wrong report type (`SALES`
   instead of `SUBSCRIBER`), and had to retract it after the user (who had
   direct knowledge the subscriptions were live) pushed back.
4. Removed a competitor keyword for being "the wrong category" using too
   literal a definition of competitor — corrected by the user: same search
   race, same audience, valid keyword regardless of underlying mechanism.
5. Added "call" and "dictation" as keywords assuming they matched app
   features, without checking — the app explicitly doesn't do call-joining
   (stated as a selling point: "no bot joining your calls"), and doesn't do
   live dictation (it transcribes recordings after the fact, a different
   user intent). Both were pure filler dressed up as data-driven.
6. Pushed hard toward "fill every field to 98-100 characters" before the
   user clarified that wasn't actually the goal — a real, justified term
   left unused space; a fake one filled it. Character utilization is a
   byproduct of finding real terms, not a target to hit by itself.

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
