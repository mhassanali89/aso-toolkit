#!/usr/bin/env python3
"""
Pull real download and subscription history from the App Store Connect Sales Reports API.

This is a DIFFERENT API from Analytics Reports (pull_asc_analytics.py) and has a
different, crucial property: it is NOT an "ongoing" subscription — Apple generates a
report for every past day regardless, so you can fetch real history back to your app's
launch, not just data from today forward.

Two report types matter for ASO/product decisions:
  - SALES / SUMMARY (MONTHLY): app unit downloads by day/territory/product-type.
    Product Type Identifier "1F" = free new download (the real acquisition metric).
    "7F" = free update/redownload on an already-installed device — NOT a new install,
    don't count it as one. "3F" = free download via an education institution program.
  - SUBSCRIBER / DETAILED (DAILY only — no weekly/monthly for this report type):
    every subscription event (trial start, paid conversion, renewal, refund) with
    plan name, price, proceeds, and country. This is where IAP/subscription revenue
    actually lives — it is NOT included in the SALES report despite what you'd expect.

Gotcha we hit in practice: subscription/IAP transactions in the SALES report (if you
go looking) will NOT show your subscription product IDs at all — only the base app
SKU shows up there. Don't conclude "$0 revenue" from an empty SALES report; you have
to pull the SUBSCRIBER report specifically.

Setup: see asc_client.py, plus:
    export ASC_VENDOR_NUMBER=...   # App Store Connect -> Reports -> Sales and Trends,
                                    # shown at the top of the page

Usage:
    python3 pull_asc_sales.py downloads --from 2025-08 --to 2026-07
    python3 pull_asc_sales.py subscribers --from 2025-08-13 --to 2026-08-13
"""

import argparse
import csv
import gzip
import io
import os
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

from asc_client import Client

VENDOR = os.environ.get("ASC_VENDOR_NUMBER")
APP_ID = os.environ.get("ASC_APP_ID")


def month_range(start_ym: str, end_ym: str):
    """Yield 'YYYY-MM' strings from start to end inclusive."""
    sy, sm = map(int, start_ym.split("-"))
    ey, em = map(int, end_ym.split("-"))
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def day_range(start_ymd: str, end_ymd: str):
    d = date.fromisoformat(start_ymd)
    end = date.fromisoformat(end_ymd)
    while d <= end:
        yield d.isoformat()
        d += timedelta(days=1)


def fetch_report(client, report_type, sub_type, freq, report_date, version=None):
    if not VENDOR:
        sys.exit("Set ASC_VENDOR_NUMBER (App Store Connect -> Reports -> Sales and Trends).")
    params = {
        "filter[frequency]": freq,
        "filter[reportDate]": report_date,
        "filter[reportSubType]": sub_type,
        "filter[reportType]": report_type,
        "filter[vendorNumber]": VENDOR,
    }
    if version:
        params["filter[version]"] = version
    r = client.session.get(
        "https://api.appstoreconnect.apple.com/v1/salesReports", headers=client._headers(), params=params
    )
    if r.status_code == 404:
        return None  # no report for this date — normal for days with zero activity
    if r.status_code != 200:
        print(f"  warning: {report_date} -> {r.status_code} {r.text[:200]}", file=sys.stderr)
        return None
    return gzip.decompress(r.content).decode("utf-8", errors="replace")


def cmd_downloads(args):
    if not APP_ID:
        sys.exit("Set ASC_APP_ID.")
    client = Client()
    monthly = {}
    type_units = Counter()
    country_units = Counter()

    for m in month_range(args.from_, args.to):
        text = fetch_report(client, "SALES", "SUMMARY", "MONTHLY", m)
        if not text:
            monthly[m] = 0
            continue
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        total = 0
        for row in reader:
            if row.get("Apple Identifier") != APP_ID:
                continue
            units = int(row.get("Units") or 0)
            total += units
            type_units[row.get("Product Type Identifier", "?")] += units
            country_units[row.get("Country Code", "?")] += units
        monthly[m] = total
        print(f"{m}: {total} total units")

    new_installs = type_units.get("1F", 0) + type_units.get("3F", 0)
    print(f"\n=== Real new installs (1F + 3F, excludes update-redownloads) ===")
    print(f"Total: {new_installs}")
    print("\n=== By product type ===")
    for t, u in type_units.most_common():
        label = {"1F": "free new download", "7F": "free update/redownload (NOT a new install)",
                  "3F": "free download, education program"}.get(t, t)
        print(f"  {t} ({label}): {u}")
    print("\n=== Top territories ===")
    for c, u in country_units.most_common(15):
        print(f"  {c}: {u}")


def cmd_subscribers(args):
    client = Client()
    rows = []
    days = list(day_range(args.from_, args.to))
    print(f"Pulling {len(days)} days (Apple only exposes this report daily — this is slow, be patient)...")
    for i, d in enumerate(days, 1):
        text = fetch_report(client, "SUBSCRIBER", "DETAILED", "DAILY", d, version="1_3")
        if text:
            reader = csv.DictReader(io.StringIO(text), delimiter="\t")
            for row in reader:
                if not APP_ID or row.get("App Apple ID") == APP_ID:
                    rows.append(row)
        if i % 30 == 0:
            print(f"  ...{i}/{len(days)} days checked, {len(rows)} events so far")

    print(f"\nTotal subscriber events: {len(rows)}")
    by_plan = Counter(r["Subscription Name"] for r in rows)
    by_offer = Counter((r.get("Subscription Offer Type") or "Paid/Renewal") for r in rows)
    by_country = Counter(r.get("Country") for r in rows)
    subscriber_ids = set(r["Subscriber ID"] for r in rows if r.get("Subscriber ID"))
    refunds = [r for r in rows if (r.get("Refund") or "").strip()]
    proceeds_by_currency = defaultdict(float)
    for r in rows:
        try:
            proceeds_by_currency[r["Proceeds Currency"]] += float(r["Developer Proceeds"] or 0) * int(r["Units"] or 1)
        except (ValueError, KeyError):
            pass

    print(f"Distinct subscribers: {len(subscriber_ids)}")
    print(f"Refunds: {len(refunds)}")
    print("\n=== By plan ===")
    for k, v in by_plan.most_common():
        print(f"  {k}: {v}")
    print("\n=== By offer type ===")
    for k, v in by_offer.most_common():
        print(f"  {k}: {v}")
    print("\n=== Top countries ===")
    for k, v in by_country.most_common(15):
        print(f"  {k}: {v}")
    print("\n=== Proceeds by currency (not FX-converted — sum per currency) ===")
    for k, v in proceeds_by_currency.items():
        print(f"  {k}: {v:.2f}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("downloads", help="Monthly download/unit history (SALES/SUMMARY report)")
    d.add_argument("--from", dest="from_", required=True, help="YYYY-MM")
    d.add_argument("--to", required=True, help="YYYY-MM")
    d.set_defaults(func=cmd_downloads)

    s = sub.add_parser("subscribers", help="Daily subscription/IAP event history (SUBSCRIBER report)")
    s.add_argument("--from", dest="from_", required=True, help="YYYY-MM-DD")
    s.add_argument("--to", required=True, help="YYYY-MM-DD")
    s.set_defaults(func=cmd_subscribers)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
