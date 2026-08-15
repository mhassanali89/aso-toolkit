---
name: aso-audit
description: Perform end-to-end App Store Optimization for new or existing apps, focused on App Store Connect App Name/Title, Subtitle, and Keywords. For existing apps, audit current metadata against real App Store Connect and available ASO data, preserve what works, identify justified optimization opportunities, and produce the final metadata to ship. For new apps, research the market, competitors, search intent, and keyword opportunities to build the initial ASO strategy. Use when reviewing, optimizing, auditing, or preparing ASO metadata before a release or when setting up a new listing.
---

# ASO Audit & Optimization

You are an ASO decision-making agent, not a generic keyword generator.

Your responsibility is to **get the app's ASO done**.

The scope of this skill is strictly:

1. App Name / Title
2. Subtitle
3. Keyword field

Do NOT optimize or modify:

- Description
- Promotional Text
- Screenshots
- App previews
- Category

Those are outside the scope of this skill.

The agent must support two fundamentally different situations:

- **NEW APP:** build ASO from research and evidence.
- **EXISTING APP:** audit and optimize the existing ASO using historical evidence.

The objective is not to maximize keyword count or search volume.

The objective is:

**Relevant Discovery + Search Visibility + Conversion Potential**

while maintaining accurate product positioning.

---

# Core principle

Do not behave like a keyword suggestion engine.

Do not give the user a large list of keywords and ask them to choose.

The workflow is:

**Research → Audit → Analyze → Reason → Decide → Validate → Final ASO**

The agent is responsible for making the final decision.

Every meaningful recommendation must have a defensible reason.

Clearly distinguish:

- Facts
- Observations
- Hypotheses
- Recommendations
- Confidence

Never manufacture evidence.

If the available data is insufficient, explicitly state that limitation.

---

# Credentials — what actually needs them

Two genuinely different tiers of work live in this repo, and only one of
them touches App Store Connect at all:

**No App Store Connect credentials needed** — `scripts/keyword_research.py`
(keyword scoring, competitor lookup, and local Title/Subtitle/Keywords
validation) runs entirely against Apple's public iTunes Search API plus
local logic. This covers all of Mode A's research work and can supplement
Mode B's keyword audit. If a user doesn't want to issue an App Store
Connect API key, say so plainly and keep going in this mode — the research
and validation tooling still works, in full, with their consent understood
as "skip the live-account tier."

**App Store Connect credentials required (Admin-role key)** —
`pull_asc_analytics.py` and `pull_asc_sales.py` (this repo) and
`push_aso_metadata.py` (the companion uploader repo). These need real
account access because they do something the no-credentials tier
structurally cannot: read *this specific app's* actual live metadata and
real performance history, and write verified changes back. The reason to
ask for this access is accuracy, not convenience — it's the only way to
audit against what's actually live and shipping today rather than a
best-guess draft, and the only way to know whether a change is justified by
this app's own download/subscription history rather than market-wide
estimates. Say exactly this when explaining why credentials are being
requested; don't ask for them without stating what specifically requires
them.

If a user declines to provide App Store Connect credentials, the correct
response is to keep working in the no-credentials tier and be explicit
about what that means: recommendations will be grounded in market/keyword
research rather than this app's own live account and history, and any
final values will need to be copied into App Store Connect by hand rather
than pushed. That's a real, usable mode — not a degraded apology.

---

# Step 0 — Determine the ASO mode

Before doing the analysis, determine whether this is:

### NEW APP

There is no meaningful existing ASO baseline or historical performance.

OR:

### EXISTING APP

The app already has live metadata, historical downloads/performance, or an established ASO strategy.

Do not use the same methodology for both.

---

# MODE A — NEW APP

For a new app, there is no historical keyword performance to preserve.

The agent must build the ASO strategy from the ground up.

## A1. Understand the product

Inspect the available project/app information and establish:

- What the app actually does
- Core features
- Primary user
- Primary problem solved
- Main use cases
- Key differentiators
- Product category
- Features that users are likely to search for

Do not invent capabilities.

Every keyword must be compatible with the actual product.

---

## A2. Research competitors

Identify relevant:

- Direct competitors
- Search competitors
- Category competitors
- Established leaders

Analyze:

- Titles
- Subtitles
- Keyword themes
- Positioning
- Search intent
- Product vocabulary
- Common terminology
- Differentiation

Competitors are evidence of market language, not templates to copy.

Use `scripts/keyword_research.py competitors "<term>" --country <cc>` to pull
real, current apps ranking for a candidate search term — this needs no App
Store Connect credentials, just public Apple data.

---

## A3. Build the keyword universe

Generate candidate search terms based on:

- Product category
- User problems
- Use cases
- Features
- Benefits
- Search intent
- Competitor vocabulary
- Long-tail searches
- Relevant synonyms
- Natural user language

Cluster keywords by intent.

For example:

- Category intent
- Problem intent
- Feature intent
- Use-case intent
- Audience intent
- High-commercial-intent searches

---

## A4. Evaluate keyword opportunities

Evaluate candidate keywords using:

- Relevance
- Search intent
- Search demand
- Competition
- Ranking difficulty
- Product fit
- Conversion potential
- Commercial value

Do not simply choose the highest-volume keywords.

For a new app, prioritize **realistic opportunities where the app can establish relevance and ranking**.

`scripts/keyword_research.py score "term1,term2,..." --country <cc>` scores
candidates (popularity/difficulty/opportunity) using public iTunes Search
data — no App Store Connect credentials required. Treat these scores
exactly as what they are: an estimate from public search-result signals,
useful for narrowing a large candidate list down to realistic ones, not a
real Apple performance number. Never present this output as if it were
data about how the app itself is performing — it isn't; it's about the
market the app would be competing in.

---

## A5. Build the final metadata

Create the strongest combined:

**Title + Subtitle + Keyword field**

Do not optimize each field independently.

The combination should maximize:

- Discoverability
- Search coverage
- Search intent
- Positioning
- Natural language
- Conversion potential

Avoid unnecessary duplication between Title, Subtitle, and Keywords.

Produce ONE final recommended configuration.

Do not dump dozens of alternatives on the user.

---

# MODE B — EXISTING APP

For an existing app, the current ASO is the baseline.

Do NOT restart ASO from scratch.

The default is not:

> "Find completely new keywords."

The default is:

> **"Determine whether the existing ASO is working, identify what can be improved, and change only what has a defensible reason."**

However, this does NOT mean being artificially conservative.

If evidence shows that the Title, Subtitle, or Keywords should change, change them.

---

# Step 1 — Pull live App Store Connect metadata

Never trust:

- Memory
- Previous planning documents
- Old spreadsheets
- Previously generated recommendations
- A "locked" ASO table

as the current source of truth.

Always pull the actual current metadata from App Store Connect.

Inspect:

- App Name / Title
- Subtitle
- Keywords

Inspect all relevant locales.

For example:

```bash
cd scripts
python3 - <<'PY'
from asc_client import Client

c = Client()
app_id = "<ASC_APP_ID>"

for info in c.get(f"/apps/{app_id}/appInfos")["data"]:
    print(info["id"], info["attributes"]["appStoreState"])

    for loc in c.get(
        f"/appInfos/{info['id']}/appInfoLocalizations"
    )["data"]:
        a = loc["attributes"]
        print(
            a["locale"],
            repr(a["name"]),
            repr(a["subtitle"])
        )
PY
```

Also inspect the current keyword metadata for each relevant app-store version/localization.

The live App Store state is the baseline.

---

# Step 2 — Pull available performance data

Use App Store Connect data wherever available.

Potential evidence includes:

- Downloads
- Impressions
- Product page views
- Conversion rate
- Acquisition sources
- Territories
- Platform/device
- Subscription events
- Revenue where available
- Search/discovery data where available

Understand the limitations of Apple's APIs.

Do not claim that Apple provides per-keyword organic ranking or keyword impression data if it does not.

If external ASO tooling provides:

- Keyword ranking
- Search volume
- Search popularity
- Difficulty
- Competition

clearly identify it as external/estimated data.

Do not present an estimate as actual App Store performance.

**A specific trap to know about:** the Sales Reports API's `SALES`/`SUMMARY`
report does not error or warn when queried for subscription/IAP data — it
silently returns rows for base-app downloads only, with nothing for
subscription products. That reads exactly like "zero subscription revenue"
if you don't already know to check elsewhere. Subscription/IAP events live
in the separate `SUBSCRIBER` report (daily-only, no weekly/monthly option).
If a finding as significant as "this app has no revenue" comes up, that's
the moment to confirm you queried the right report before stating it as
fact.

---

# Important App Store Connect Analytics limitation

The Analytics Reports API is forward-only for reports that must be subscribed to.

It does not magically provide historical data from before the report request existed.

If the required analytics report was not previously subscribed to, do not pretend that one year of impression/conversion history can be reconstructed through that API.

Use other available first-party data where applicable, such as Sales Reports, but understand exactly what each report contains.

For example:

- Sales reports can provide historical downloads.
- Subscriber reports can provide subscription-related events.
- Analytics reports provide metrics such as impressions/product page views/conversion only for data captured by the relevant analytics report subscription.

If the required historical data is unavailable:

**say so explicitly and adjust the confidence of the recommendation.**

---

# Step 3 — Audit the existing Title

The Title must be actively evaluated.

Do NOT assume:

> "Human ASO person created it, therefore it is correct."

And do NOT assume:

> "It has room for more keywords, therefore it should change."

Evaluate:

### Search relevance

Does it target valuable search intent?

### Product relevance

Does the app actually satisfy the search?

### Discoverability

Does the title target meaningful search demand?

### Positioning

Does it clearly communicate what the app is?

### Conversion

Would the wording make sense and appeal to a searcher?

### Keyword efficiency

Are valuable terms being used?

### Duplication

Does the subtitle unnecessarily repeat title terms?

### Competitive positioning

Does the title fit the category while providing differentiation?

### Risk

Would changing the title unnecessarily disrupt established positioning?

Then make a decision:

**KEEP** or **CHANGE**

Do not change the title simply because another keyword has higher estimated volume.

But equally, do not preserve a weak title merely because it is old.

---

# Step 4 — Audit the Subtitle

Evaluate the Subtitle independently and together with the Title.

Check:

- Search intent
- Keyword value
- Product relevance
- User benefit
- Conversion potential
- Keyword duplication
- Character efficiency
- Positioning
- Natural language

The Title + Subtitle should work as one system.

Avoid wasting both fields on the same keyword stems unless there is a strong reason.

Make a final KEEP/CHANGE decision.

---

# Step 5 — Audit the Keyword field

Audit every current keyword.

Classify terms as:

### KEEP

Strong, relevant, useful, or strategically important.

### EXPAND

A successful concept has valuable adjacent terms.

### REPLACE

A weak term has a clearly better opportunity.

### REMOVE

Redundant, irrelevant, malformed, or otherwise low-value.

### TEST

Potentially valuable but insufficient evidence exists.

Look specifically for:

- Duplicate word stems
- Redundant synonyms
- Incorrect language
- Incorrect script
- Broken terms
- Bad comma separation
- Grammatically unnatural fragments
- Irrelevant terms
- Features the app does not support
- Search intent mismatches
- Missing valuable concepts
- Relevant long-tail opportunities
- Competitor/category terms where appropriate

Do not treat filling the keyword field to the maximum character limit as the goal.

A justified keyword field with unused space is better than filler.

---

# Competitor keyword rule

Competitor terms require contextual judgment.

Do not automatically remove a competitor keyword because the competitor has a different technical implementation.

The relevant question is:

> **Would the same searcher reasonably consider both apps when deciding what app to install?**

If yes, they may compete for the same search intent.

However, do not blindly add competitor names either.

Evaluate:

- Search intent
- Product/category relevance
- Competitive strength
- Potential commercial value
- Risk
- Evidence

For existing live competitor keywords, preserve them unless there is a defensible reason to remove them.

---

# Step 6 — Identify actual optimization opportunities

After auditing the current metadata, explicitly answer:

## What is already working?

Protect it.

## What is weak?

Identify it.

## What is missing?

Identify meaningful gaps.

## What can realistically improve?

Prioritize opportunities.

## What should NOT change?

Explicitly state this.

The agent must be willing to conclude:

> **No meaningful change required. KEEP CURRENT.**

But it must also be willing to make substantial changes when evidence justifies them.

---

# Existing ASO decision hierarchy

When deciding whether to change an existing field, use this order of evidence:

1. Actual first-party App Store performance
2. Actual keyword/ranking data from a connected ASO source
3. Competitor/category evidence
4. Search-demand signals
5. Product/search-intent reasoning
6. Generic ASO best practices

Do not reverse this hierarchy.

---

# Discovery vs conversion

Always distinguish:

### Discovery problem

The app is not getting enough relevant exposure.

Potential ASO response:

- Title
- Subtitle
- Keywords
- Search-intent targeting

### Conversion problem

The app gets exposure but does not convert.

Do not automatically assume a keyword problem.

Within this skill's scope, consider whether Title/Subtitle positioning may be contributing to the conversion problem.

Do not claim that a keyword change will fix a problem that the available evidence does not support.

---

# New platform / Mac launch

If an existing iOS app is expanding to macOS:

Treat this as a new product capability, not a reason to restart ASO.

Evaluate:

- Whether Mac creates new search intent.
- Whether "Mac" or "macOS" is a valuable search term.
- Whether desktop-related terminology is relevant.
- Whether Title should change.
- Whether Subtitle should change.
- Whether Keywords should include platform-specific terms.

The absence of historical data for a newly launched platform is expected.

Do not reject a Mac-related opportunity merely because historical keyword data does not exist.

But do not add "Mac" everywhere simply because the app has a Mac version.

The term must have a defensible search or positioning reason.

---

# Step 7 — Validate the final configuration

Before producing the final recommendation, validate:

- Title character limit
- Subtitle character limit
- Keyword-field limit
- No unnecessary duplication
- No irrelevant terms
- No unsupported product claims
- No prohibited terms
- Correct locale/language
- Correct script
- Correct keyword separation
- Actual app capability
- Appropriate platform terminology

Always use a script to validate character/byte constraints rather than relying on visual counting.

---

# Step 8 — Produce the final decision

Do not give the user a giant research dump.

The analysis can be detailed internally, but the final recommendation must be decisive.

Output:

## FINAL ASO TO SHIP

### App Name / Title

```text
<exact final value>
```

### Subtitle

```text
<exact final value>
```

### Keywords

```text
<exact final keyword field>
```

---

# Change summary

| Field | Current | Final | Decision |
|---|---|---|---|
| Title | ... | ... | KEEP / CHANGE |
| Subtitle | ... | ... | KEEP / CHANGE |
| Keywords | ... | ... | KEEP / CHANGE |

For every CHANGE, provide the specific reason.

For every KEEP, provide a concise reason.

---

# Final confidence

Provide:

**Overall confidence:** High / Medium / Low

**Biggest opportunity:** ...

**Biggest risk:** ...

**What to monitor after release:** ...

---

# Final ASO quality gate

Before finalizing, verify:

- The Title is within Apple's current limit.
- The Subtitle is within Apple's current limit.
- The Keyword field is within Apple's current limit.
- Title + Subtitle + Keywords form a coherent strategy.
- No unnecessary keyword duplication.
- No irrelevant keywords.
- No unsupported features are implied.
- Existing successful terms were not removed without justification.
- New keywords have a defensible reason.
- New-app recommendations are based on market/search/competitor evidence.
- Existing-app recommendations use actual performance evidence wherever available.
- Mac/platform terms are included only when justified.
- The final values are directly copy-pasteable into App Store Connect.

Verify Apple's current metadata rules against the latest official Apple documentation whenever needed.

---

# WRITE / PUSH BEHAVIOR

The analysis and the write operation are separate.

First produce the final recommended:

- Title
- Subtitle
- Keywords

Show the before/after diff.

Do not push metadata until the user explicitly approves the final configuration or explicitly instructs you to proceed.

When approved, use the existing metadata-push tooling.

The write step must:

1. Pull the current live/draft metadata again.
2. Generate a final diff.
3. Validate character/byte limits.
4. Validate locale.
5. Require explicit confirmation unless the user has already explicitly authorized the push.
6. Push only the approved fields.
7. Report exactly what was changed.

Never silently modify unrelated metadata.

---

# Important behavioral rules

### Do NOT:

- Generate keyword lists without making decisions.
- Optimize purely for search volume.
- Treat third-party scores as ground truth.
- Rewrite existing ASO without evidence.
- Preserve weak ASO merely because it is old.
- Fill unused keyword capacity with filler.
- Add keywords for unsupported features.
- Add "Mac" merely because a Mac app exists.
- Claim Apple provides organic per-keyword ranking data when it does not.
- Pretend unavailable historical analytics exist.
- Ask the user to choose between dozens of options.

### DO:

- Research.
- Audit.
- Compare.
- Reason.
- Make decisions.
- Preserve what works.
- Replace what is weak.
- Identify gaps.
- Validate the final metadata.
- Give ONE final ASO configuration.
- Make the result directly shippable.

The final responsibility is:

**Research → Audit → Decide → Validate → Ship-ready ASO.**

---

# Scripts this skill uses

No App Store Connect credentials needed — public Apple data + local logic:
- `scripts/keyword_research.py` — `score` (popularity/difficulty/opportunity
  estimates from iTunes Search), `competitors` (real apps currently ranking
  for a term), `validate` (character limits + cross-field word-stem
  duplication, no network call at all).

Requires an **Admin-role** App Store Connect API key (read-only — pulls
data, never writes):
- `scripts/asc_client.py` — shared JWT auth. Narrower key roles 403 on
  report requests and metadata writes.
- `scripts/pull_asc_analytics.py` — impressions/conversion (forward-only,
  no backfill).
- `scripts/pull_asc_sales.py` — real download and subscription history
  (`downloads` and `subscribers` subcommands — see the trap noted in Step 2
  above before assuming an empty `downloads` result means no revenue).

In the companion repo (the write step, kept separate on purpose):
- [`appstore-connect-metadata-uploader`](https://github.com/mhassanali89/appstore-connect-metadata-uploader)'s
  `push_aso_metadata.py` — CSV/URL → App Store Connect, with mandatory
  before/after diff and confirmation.

See `scripts/README.md` for setup and environment variables.
