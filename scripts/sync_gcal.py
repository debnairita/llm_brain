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
from datetime import datetime, timezone
from pathlib import Path

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
    time_max = now.replace(
        year=now.year if now.month + (days_ahead // 30) <= 12 else now.year + 1
    )
    # Simple approach: just use RFC3339 strings
    from datetime import timedelta
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
# Transform
# ---------------------------------------------------------------------------

def parse_gcal_datetime(dt_field: dict) -> str:
    """Convert Google's dateTime or date field to 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'."""
    if "dateTime" in dt_field:
        dt = datetime.fromisoformat(dt_field["dateTime"])
        return dt.strftime("%Y-%m-%d %H:%M")
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

    print("\n(Full merge into events.yaml coming in next step.)")


if __name__ == "__main__":
    main()
