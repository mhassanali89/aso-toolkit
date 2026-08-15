#!/usr/bin/env python3
"""
Pull App Store Connect Analytics reports for an app.

Flow (App Store Connect Analytics Reports API):
  1. Authenticate (see asc_client.py for setup/env vars).
  2. Sanity check auth by listing apps.
  3. Find or create an ONGOING analyticsReportRequest for the app.
  4. List the analyticsReports available under that request (one per report name/category,
     e.g. "App Store Discovery and Engagement", "App Downloads", etc — Apple exposes 150+,
     most of them unrelated framework/performance telemetry, not ASO-relevant).
  5. For each report, list its analyticsReportInstances (report-per-day/week granularity).
  6. For each instance, list its segments (the actual downloadable files) and download them.
  7. Each segment is a gzip-compressed TSV — decompress and save under ./asc_reports/.

Docs: https://developer.apple.com/documentation/appstoreconnectapi/analytics_reports

IMPORTANT — this API only captures data going *forward* from when the ONGOING request
is first created. It does NOT backfill history. For historical trends, use the Sales
Reports API instead (downloads/proceeds/subscriptions — see push_aso_metadata.py's
sibling analysis in the ASO skill), or export from the App Store Connect web UI.

Setup: see asc_client.py. Then:
    python3 pull_asc_analytics.py
"""

import gzip
import io
import os
import zipfile
from pathlib import Path

import requests

from asc_client import Client

APP_ID = os.environ.get("ASC_APP_ID")
if not APP_ID:
    raise SystemExit("Set ASC_APP_ID to your app's numeric Apple ID.")

OUT_DIR = Path(__file__).parent / "asc_reports"

# Report names worth pulling first — verified against the actual names returned by
# /analyticsReportRequests/{id}/reports. Edit this if you want different categories.
REPORT_NAME_ALLOWLIST = {
    "App Store Discovery and Engagement Standard",
    "App Store Discovery and Engagement Detailed",
    "App Store Web Preview Engagement Standard",
    "App Store Web Preview Engagement Detailed",
    "App Downloads Standard",
    "App Downloads Detailed",
    "App Store Purchases Standard",
    "App Store Purchases Detailed",
}


def sanity_check(client: Client):
    print("== Sanity check: listing apps you have access to ==")
    body = client.get("/apps", params={"limit": 50})
    for app in body.get("data", []):
        attrs = app.get("attributes", {})
        marker = "  <-- target app" if app["id"] == APP_ID else ""
        print(f"  {app['id']}  {attrs.get('name', '?'):40s} {attrs.get('bundleId', '?')}{marker}")
    print()


def get_or_create_report_request(client: Client) -> str:
    print("== Looking for an existing ONGOING analyticsReportRequest ==")
    existing = list(
        client.paginate(f"/apps/{APP_ID}/analyticsReportRequests", params={"filter[accessType]": "ONGOING"})
    )
    if existing:
        req_id = existing[0]["id"]
        print(f"  Found existing request: {req_id}")
        return req_id

    print("  None found — creating one.")
    body = client.post(
        "/analyticsReportRequests",
        {
            "data": {
                "type": "analyticsReportRequests",
                "attributes": {"accessType": "ONGOING"},
                "relationships": {"app": {"data": {"type": "apps", "id": APP_ID}}},
            }
        },
    )
    req_id = body["data"]["id"]
    print(f"  Created request: {req_id}")
    print(
        "  NOTE: Apple backfills ONGOING reports asynchronously from creation time onward — "
        "reports/instances may not show up for several minutes to a day on first creation, "
        "and will NEVER contain data from before this request was created."
    )
    return req_id


def list_reports(client: Client, request_id: str):
    print("== Listing analyticsReports under this request ==")
    reports = list(client.paginate(f"/analyticsReportRequests/{request_id}/reports", params={"limit": 200}))
    for r in reports:
        name = r.get("attributes", {}).get("name", "?")
        cat = r.get("attributes", {}).get("category", "?")
        print(f"  {r['id']}  [{cat}] {name}")
    print()
    return reports


def download_segment(segment: dict, dest_dir: Path):
    attrs = segment.get("attributes", {})
    url = attrs.get("url")
    checksum = attrs.get("checksum")
    if not url:
        return
    # Segment URLs are pre-signed — no auth header needed/allowed here.
    r = requests.get(url)
    r.raise_for_status()
    raw = r.content

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Apple ships these as gzip most of the time, occasionally as a zip of gzips.
    try:
        data = gzip.decompress(raw)
        out_name = Path(url.split("?")[0]).name
        if out_name.endswith(".gz"):
            out_name = out_name[:-3]
        out_path = dest_dir / out_name
        out_path.write_bytes(data)
        print(f"    wrote {out_path.relative_to(dest_dir.parent)} ({len(data):,} bytes)")
        return
    except OSError:
        pass

    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            zf.extractall(dest_dir)
            print(f"    extracted zip into {dest_dir}")
            return
    except zipfile.BadZipFile:
        pass

    # Fallback: save whatever we got, unmodified.
    out_path = dest_dir / (Path(url.split("?")[0]).name or "segment.bin")
    out_path.write_bytes(raw)
    print(f"    wrote raw {out_path} ({len(raw):,} bytes, checksum={checksum})")


def pull_report_instances(client: Client, report: dict):
    name = report.get("attributes", {}).get("name", "report")
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip()
    report_dir = OUT_DIR / safe_name

    instances = list(client.paginate(f"/analyticsReports/{report['id']}/instances", params={"limit": 200}))
    if not instances:
        print(f"  [{name}] no instances yet")
        return
    print(f"  [{name}] {len(instances)} instance(s)")

    # Most recent first; grab a handful so this doesn't take forever on first run.
    instances.sort(key=lambda i: i.get("attributes", {}).get("processingDate", ""), reverse=True)
    for inst in instances[:5]:
        granularity = inst.get("attributes", {}).get("granularity", "?")
        date = inst.get("attributes", {}).get("processingDate", "?")
        segments = list(client.paginate(f"/analyticsReportInstances/{inst['id']}/segments"))
        print(f"    instance {inst['id']} ({granularity}, {date}) — {len(segments)} segment(s)")
        for seg in segments:
            download_segment(seg, report_dir)


def main():
    client = Client()
    sanity_check(client)

    request_id = get_or_create_report_request(client)
    reports = list_reports(client, request_id)

    if not reports:
        print(
            "No reports listed yet under this request. If the request was just created, "
            "Apple hasn't backfilled data — rerun in 10-15 minutes (can take longer on first run)."
        )
        return

    wanted = [r for r in reports if r.get("attributes", {}).get("name") in REPORT_NAME_ALLOWLIST]
    if not wanted:
        print("None of the allowlisted report names matched — pulling all reports instead.")
        wanted = reports

    print(f"== Downloading segments for {len(wanted)} report(s) into {OUT_DIR} ==")
    for report in wanted:
        pull_report_instances(client, report)

    print("\nDone. TSV files are under:", OUT_DIR)


if __name__ == "__main__":
    main()
