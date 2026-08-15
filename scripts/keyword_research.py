#!/usr/bin/env python3
"""
Keyword research and metadata validation — no App Store Connect credentials
required. Uses only Apple's public, unauthenticated iTunes Search API, so
this works before you have an API key, or if you never want to give one.

What this can and can't tell you, honestly:

Popularity/Difficulty/Opportunity below are ESTIMATES derived from public
search-result signals (how many apps match a term, how established the
top-ranking apps for it are). They are a genuinely useful proxy for
research — but they are not, and must never be presented as, real Apple
performance data for *your* app. Apple does not expose real per-keyword
search volume or ranking to anyone, through any channel. See
`.claude/skills/aso-audit/SKILL.md` for why that distinction matters.

Usage:
    python3 keyword_research.py score "voice notes" --country us
    python3 keyword_research.py score "voice notes,note taking,transcription" --country us
    python3 keyword_research.py competitors "note taking app" --country us --limit 10
    python3 keyword_research.py validate --title "..." --subtitle "..." --keywords "..."
"""

import argparse
import sys
import time
from urllib.parse import urlencode

import requests

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
# Apple doesn't publish a rate limit for this endpoint; ~1 req/sec is the
# commonly used, conservative pace that avoids getting throttled.
REQUEST_DELAY_SECONDS = 1.0

LIMITS = {"title": 30, "subtitle": 30, "keywords": 100}


def itunes_search(term: str, country: str = "us", limit: int = 50):
    params = {"term": term, "country": country, "entity": "software", "limit": limit}
    r = requests.get(f"{ITUNES_SEARCH_URL}?{urlencode(params)}", timeout=15)
    r.raise_for_status()
    return r.json().get("results", [])


def _scale(value, low, high):
    """Clamp+scale a raw value into 1-100."""
    if high <= low:
        return 1
    pct = (value - low) / (high - low)
    return max(1, min(100, round(pct * 100)))


def score_keyword(term: str, country: str = "us") -> dict:
    """
    Independent scoring heuristic (not a port of any third-party tool):

    Popularity: proxied by how many apps exist for this term — a term with
    very few matching apps is either extremely niche or barely searched;
    a term with a large, saturated result set suggests real, sustained
    search demand (that's *why* apps compete for it).

    Difficulty: proxied by how entrenched the top-ranking apps for this
    term already are — average rating count of the top 10 results, plus
    how many of them use the term directly in their app name (exact-title
    matches are the hardest incumbents to outrank).

    Opportunity: popularity weighted down by difficulty — same combinator
    concept common across ASO tools, independently computed here.
    """
    results = itunes_search(term, country=country, limit=50)
    result_count = len(results)

    top10 = results[:10]
    if top10:
        avg_rating_count = sum(a.get("userRatingCount", 0) or 0 for a in top10) / len(top10)
        title_matches = sum(
            1 for a in top10 if term.lower() in (a.get("trackName") or "").lower()
        )
        title_match_ratio = title_matches / len(top10)
    else:
        avg_rating_count = 0
        title_match_ratio = 0

    # Popularity: more matching apps -> more assumed demand. Scaled
    # generously since result counts vary hugely by term.
    popularity = _scale(result_count, low=0, high=50)

    # Difficulty: entrenched incumbents (high rating counts) + exact-title
    # saturation both make it harder to rank. Rating count scaled on a log
    # curve since it spans orders of magnitude.
    import math

    rating_component = _scale(math.log10(avg_rating_count + 1), low=0, high=5)  # 0 to 100k+ ratings
    difficulty = round(0.7 * rating_component + 0.3 * (title_match_ratio * 100))
    difficulty = max(1, min(100, difficulty))

    opportunity = round(popularity * (100 - difficulty) / 100)

    if opportunity >= 55 and difficulty <= 45:
        classification = "Sweet Spot"
    elif opportunity >= 40 and difficulty <= 60:
        classification = "Good Target"
    elif difficulty >= 75:
        classification = "High Competition"
    elif popularity <= 15:
        classification = "Low Volume"
    else:
        classification = "Moderate"

    return {
        "term": term,
        "country": country,
        "result_count": result_count,
        "popularity": popularity,
        "difficulty": difficulty,
        "opportunity": opportunity,
        "classification": classification,
    }


def score_keywords_batch(terms: list, country: str = "us") -> list:
    scored = []
    for i, term in enumerate(terms):
        if i > 0:
            time.sleep(REQUEST_DELAY_SECONDS)
        scored.append(score_keyword(term.strip(), country=country))
    scored.sort(key=lambda s: s["opportunity"], reverse=True)
    return scored


def get_competitors(term: str, country: str = "us", limit: int = 10) -> list:
    results = itunes_search(term, country=country, limit=limit)
    return [
        {
            "name": a.get("trackName"),
            "developer": a.get("artistName"),
            "rating": a.get("averageUserRating"),
            "ratingCount": a.get("userRatingCount"),
            "genre": a.get("primaryGenreName"),
            "url": a.get("trackViewUrl"),
        }
        for a in results
    ]


def validate_metadata(title: str = "", subtitle: str = "", keywords: str = "") -> dict:
    """Pure local validation — no network call. Character limits and
    word-stem duplication across the three indexed fields."""
    issues = []
    counts = {"title": len(title), "subtitle": len(subtitle), "keywords": len(keywords)}
    for field, limit in LIMITS.items():
        if counts[field] > limit:
            issues.append(f"{field} is {counts[field]}/{limit} — over the limit")

    def words(s):
        return {w.strip(",.:-").lower() for w in s.replace(",", " ").split() if len(w) > 2}

    title_words, subtitle_words, keyword_words = words(title), words(subtitle), words(keywords)
    dup_title_subtitle = title_words & subtitle_words
    dup_title_keywords = title_words & keyword_words
    dup_subtitle_keywords = subtitle_words & keyword_words

    if dup_title_subtitle:
        issues.append(f"Title/Subtitle share words (wasted index space): {sorted(dup_title_subtitle)}")
    if dup_title_keywords:
        issues.append(f"Title/Keywords share words (wasted index space): {sorted(dup_title_keywords)}")
    if dup_subtitle_keywords:
        issues.append(f"Subtitle/Keywords share words (wasted index space): {sorted(dup_subtitle_keywords)}")

    return {"counts": counts, "limits": LIMITS, "issues": issues, "ok": not issues}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="Score one or more comma-separated keywords")
    s.add_argument("terms", help="Comma-separated keyword(s)")
    s.add_argument("--country", default="us")

    c = sub.add_parser("competitors", help="List apps currently ranking for a search term")
    c.add_argument("term")
    c.add_argument("--country", default="us")
    c.add_argument("--limit", type=int, default=10)

    v = sub.add_parser("validate", help="Check Title/Subtitle/Keywords limits and duplication (no network call)")
    v.add_argument("--title", default="")
    v.add_argument("--subtitle", default="")
    v.add_argument("--keywords", default="")

    args = ap.parse_args()

    if args.cmd == "score":
        terms = [t for t in args.terms.split(",") if t.strip()]
        results = score_keywords_batch(terms, country=args.country)
        print(f"{'term':30s} {'pop':>4s} {'diff':>4s} {'opp':>4s}  classification")
        for r in results:
            print(f"{r['term'][:30]:30s} {r['popularity']:4d} {r['difficulty']:4d} {r['opportunity']:4d}  {r['classification']}")
        print("\n(Popularity/Difficulty/Opportunity are estimates from public iTunes")
        print(" Search data, not real Apple performance numbers for your app.)")

    elif args.cmd == "competitors":
        for a in get_competitors(args.term, country=args.country, limit=args.limit):
            rating = f"{a['rating']}★ ({a['ratingCount']:,})" if a["rating"] else "no ratings"
            print(f"- {a['name']} — {a['developer']} — {rating} — {a['genre']}")

    elif args.cmd == "validate":
        result = validate_metadata(args.title, args.subtitle, args.keywords)
        for field, limit in LIMITS.items():
            print(f"{field}: {result['counts'][field]}/{limit}")
        if result["issues"]:
            print("\nIssues:")
            for issue in result["issues"]:
                print(f"  - {issue}")
        else:
            print("\nNo issues found.")
        sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
