#!/usr/bin/env python3
"""
Generate tasks from recurring task templates.

Reads recurring_tasks.yaml and creates one-off task entries in tasks.yaml
when the next occurrence of a recurring task is due (within advance_days).

Missed occurrences are generated if they are within 7 days past due.
Occurrences older than 7 days are skipped silently.

Recurrence types supported:
  monthly_nth_weekday:
    n:       nth occurrence (1 = first, 2 = second, ...)
    weekday: 0=Monday ... 6=Sunday

Usage:
    python scripts/generate_recurring_tasks.py
"""

import calendar
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
_config = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8"))
_storage = _config["storage"]

TASKS_PATH = Path(_storage["tasks"]).expanduser()
RECURRING_PATH = Path(_storage["recurring_tasks"]).expanduser()


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_yaml(path: Path, data: dict) -> None:
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def nth_weekday_of_month(year: int, month: int, n: int, weekday: int) -> date | None:
    """Return the date of the nth occurrence of weekday in the given month.
    Returns None if the month has fewer than n occurrences of that weekday."""
    count = 0
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        d = date(year, month, day)
        if d.weekday() == weekday:
            count += 1
            if count == n:
                return d
    return None


def next_occurrence(recurrence: dict, on_or_after: date) -> date | None:
    """Return the next occurrence date on or after `on_or_after`."""
    rtype = recurrence.get("type")

    if rtype == "monthly_nth_weekday":
        n = recurrence["n"]
        weekday = recurrence["weekday"]
        year, month = on_or_after.year, on_or_after.month
        for _ in range(14):  # look ahead at most 14 months
            occ = nth_weekday_of_month(year, month, n, weekday)
            if occ and occ >= on_or_after:
                return occ
            month += 1
            if month > 12:
                month = 1
                year += 1

    return None


def task_exists(tasks: list[dict], title: str, due_date: date) -> bool:
    due_str = due_date.isoformat()
    return any(
        t.get("title") == title and str(t.get("due_date", "")) == due_str
        for t in tasks
    )


def max_task_id(tasks: list[dict]) -> int:
    return max((t.get("id", 0) for t in tasks), default=0)


def find_actionable_occurrence(recurrence: dict, last_generated: date | None, today: date) -> date | None:
    """Find the next occurrence that is either upcoming (within advance window)
    or missed but not stale (within 7 days past due). Skips stale occurrences."""
    STALE_DAYS = 7
    search_from = (last_generated + timedelta(days=1)) if last_generated else today

    for _ in range(24):  # safety cap — at most 2 years of searching
        due = next_occurrence(recurrence, search_from)
        if due is None:
            return None
        if today > due + timedelta(days=STALE_DAYS):
            # Stale — skip to next occurrence
            search_from = due + timedelta(days=1)
            continue
        return due

    return None


def main() -> None:
    today = date.today()

    if not RECURRING_PATH.exists():
        print("No recurring_tasks.yaml found — skipping.")
        return

    recurring_data = load_yaml(RECURRING_PATH)
    recurring_tasks = recurring_data.get("recurring_tasks", [])

    if not recurring_tasks:
        print("No recurring tasks defined.")
        return

    tasks_data = load_yaml(TASKS_PATH)
    tasks = tasks_data.get("tasks", [])

    generated = 0
    changed_recurring = False

    for rt in recurring_tasks:
        title = rt["title"]
        recurrence = rt.get("recurrence", {})
        advance_days = rt.get("advance_days", 0)
        last_generated_raw = rt.get("last_generated")
        last_generated = (
            date.fromisoformat(str(last_generated_raw)) if last_generated_raw else None
        )

        due_date = find_actionable_occurrence(recurrence, last_generated, today)

        if due_date is None:
            print(f"  '{title}': could not compute next occurrence — check recurrence config")
            continue

        generate_from = due_date - timedelta(days=advance_days)

        if today < generate_from:
            print(f"  '{title}': next due {due_date} — not yet")
            continue

        if task_exists(tasks, title, due_date):
            print(f"  '{title}': task for {due_date} already exists — skipping")
            continue

        new_task = {
            "id": max_task_id(tasks) + 1,
            "title": title,
            "description": rt.get("description", ""),
            "status": "pending",
            "priority": rt.get("priority", "medium"),
            "category": rt.get("category", "personal"),
            "due_date": due_date.isoformat(),
            "tags": rt.get("tags", []),
            "created_at": today.isoformat(),
            "ttl_days": rt.get("ttl_days"),
            "completed_at": None,
        }
        tasks.append(new_task)
        rt["last_generated"] = due_date.isoformat()
        changed_recurring = True
        generated += 1
        print(f"  Generated: '{title}' due {due_date} (id {new_task['id']})")

    if generated > 0:
        save_yaml(TASKS_PATH, {"tasks": tasks})

    if changed_recurring:
        save_yaml(RECURRING_PATH, {"recurring_tasks": recurring_tasks})

    if generated == 0:
        print("No recurring tasks to generate.")
    else:
        print(f"Generated {generated} task(s).")


if __name__ == "__main__":
    main()
