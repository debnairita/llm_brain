#!/usr/bin/env python3
"""
Sync Google Calendar events into events.yaml.

Usage:
    python scripts/sync_gcal.py            # full sync
    python scripts/sync_gcal.py --dry-run  # fetch and print only, no writes
"""

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config():
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    return cfg


def resolve(path_str):
    return Path(path_str).expanduser()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_credentials(creds_path: Path, token_path: Path) -> Credentials:
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_events(service, calendar_id: str, days_ahead: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    results = []
    page_token = None

    while True:
        response = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token,
            maxResults=250,
        ).execute()

        results.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def load_events_yaml(events_path: Path) -> tuple[dict, list]:
    """Return (raw_doc, events_list). Creates empty structure if file missing."""
    if events_path.exists():
        with open(events_path) as f:
            doc = yaml.safe_load(f) or {}
    else:
        doc = {}
    events = doc.get("events") or []
    return doc, events


def parse_start_date(start_str) -> datetime:
    """Parse a start string from events.yaml into a timezone-aware datetime."""
    s = str(start_str)
    try:
        if len(s) == 10:  # YYYY-MM-DD (all-day)
            return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=IST).astimezone(timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def merge_into_yaml(
    existing: list,
    incoming: list,
    window_start: datetime,
    window_end: datetime,
) -> tuple[list, int, int, int]:
    """
    Merge incoming GCal events into existing list.
    - Adds new events, updates changed ones (by external_id).
    - Removes GCal-sourced events (external_id present) whose start falls within
      the sync window but were not returned — they were deleted in Google Calendar.
    - Never touches manually created events (no external_id).
    Returns (merged_list, added, updated, deleted).
    """
    fetched_ids = {ev["external_id"] for ev in incoming}

    by_external_id = {
        e["external_id"]: i
        for i, e in enumerate(existing)
        if e.get("external_id")
    }
    next_id = max((e.get("id", 0) for e in existing), default=0) + 1
    added = updated = deleted = 0

    # Determine which existing GCal events to drop (deleted in GCal within window)
    removed_ids = set()
    for e in existing:
        ext_id = e.get("external_id")
        if not ext_id:
            continue  # manually created — never touch
        if ext_id in fetched_ids:
            continue  # still exists in GCal
        start_dt = parse_start_date(e.get("start", ""))
        if window_start <= start_dt <= window_end:
            removed_ids.add(ext_id)
            deleted += 1

    # Build merged list, skipping removed events
    merged = [e for e in existing if e.get("external_id") not in removed_ids]

    # Rebuild index after removals
    by_external_id = {
        e["external_id"]: i
        for i, e in enumerate(merged)
        if e.get("external_id")
    }

    for ev in incoming:
        ext_id = ev["external_id"]
        if ext_id in by_external_id:
            # Update mutable fields, preserve id and created_at
            idx = by_external_id[ext_id]
            old = merged[idx]
            changed = False
            for field in ("title", "start", "end", "location", "description", "recurring", "tags", "calendar"):
                if old.get(field) != ev.get(field):
                    old[field] = ev[field]
                    changed = True
            if changed:
                updated += 1
        else:
            # New event
            new_ev = {
                "id": next_id,
                "title": ev["title"],
                "description": ev["description"],
                "start": ev["start"],
                "end": ev["end"],
                "location": ev["location"],
                "recurring": ev["recurring"],
                "tags": ev["tags"],
                "created_at": ev["created_at"],
                "external_id": ext_id,
                "calendar": ev["calendar"],
            }
            merged.append(new_ev)
            by_external_id[ext_id] = len(merged) - 1
            next_id += 1
            added += 1

    return merged, added, updated, deleted


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

IST = ZoneInfo("Asia/Kolkata")


def parse_gcal_datetime(dt_field: dict) -> str:
    """Convert Google's dateTime or date field to 'YYYY-MM-DD HH:MM' (IST) or 'YYYY-MM-DD'."""
    if "dateTime" in dt_field:
        dt = datetime.fromisoformat(dt_field["dateTime"].replace("Z", "+00:00"))
        return dt.astimezone(IST).strftime("%Y-%m-%d %H:%M")
    elif "date" in dt_field:
        return dt_field["date"]
    return ""


def transform(gcal_event: dict, calendar_label: str) -> dict:
    title = gcal_event.get("summary", "(No title)")
    description = gcal_event.get("description", "") or ""
    location = gcal_event.get("location", "") or ""
    external_id = gcal_event["id"]
    created_at = gcal_event.get("created", "")[:10] if gcal_event.get("created") else ""

    start = parse_gcal_datetime(gcal_event.get("start", {}))
    end = parse_gcal_datetime(gcal_event.get("end", {}))

    # Map recurrence
    recurring = None
    if gcal_event.get("recurrence"):
        rule = " ".join(gcal_event["recurrence"])
        if "WEEKLY" in rule:
            recurring = "weekly"
        elif "DAILY" in rule:
            recurring = "daily"
        elif "MONTHLY" in rule:
            recurring = "monthly"

    tags = [calendar_label]

    return {
        "title": title,
        "description": description,
        "start": start,
        "end": end,
        "location": location,
        "recurring": recurring,
        "tags": tags,
        "created_at": created_at,
        "external_id": external_id,
        "calendar": calendar_label,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print only, no writes")
    args = parser.parse_args()

    cfg = load_config()
    gcal_cfg = cfg["gcal"]

    creds_path = resolve(gcal_cfg["credentials"])
    token_path = resolve(gcal_cfg["token"])
    calendars = gcal_cfg["calendars"]
    days_ahead = gcal_cfg.get("sync_days_ahead", 60)

    window_start = datetime.now(timezone.utc)
    window_end = window_start + timedelta(days=days_ahead)

    print("Authenticating...")
    creds = get_credentials(creds_path, token_path)
    service = build("calendar", "v3", credentials=creds)
    print("Authenticated.\n")

    all_events = []

    for cal in calendars:
        cal_id = cal["id"]
        label = cal["label"]
        print(f"Fetching calendar: {label} ({cal_id})...")
        raw_events = fetch_events(service, cal_id, days_ahead)
        print(f"  Found {len(raw_events)} events")
        for e in raw_events:
            all_events.append(transform(e, label))

    print(f"\nTotal events fetched: {len(all_events)}\n")

    # Print summary
    for e in all_events:
        print(f"  [{e['calendar']:8}] {e['start']}  {e['title']}")

    if args.dry_run:
        print("\n--dry-run: no changes written.")
        return

    # Load existing events and merge
    events_path = resolve(cfg["storage"]["events"])
    _, existing = load_events_yaml(events_path)
    merged, added, updated, deleted = merge_into_yaml(existing, all_events, window_start, window_end)

    # Write back
    with open(events_path, "w") as f:
        yaml.dump({"events": merged}, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    unchanged = len(all_events) - added - updated
    print(f"\nSync complete: {added} added, {updated} updated, {unchanged} unchanged, {deleted} deleted.")


if __name__ == "__main__":
    main()
