# llm_brain

A plain-file personal assistant powered by Claude Code. Manages tasks, calendar events, a daily journal, and personal profiles — all as plain YAML and Markdown on your filesystem.

---

## What it does

- **Tasks** — add, update, and prioritise to-dos; categorised as `work` or `personal`; ephemeral todos auto-purge after completion; recurring tasks auto-generated from templates
- **Events** — track calendar events with automatic commute and schedule enrichment
- **Journal** — one Markdown file per day; tag entries for fast lookup
- **Profiles** — personal context (identity, family, locations, goals, calendar, reading list, checklists) that Claude reads when scheduling or suggesting activities
- **Search** — hierarchical lookup via an index file so Claude never scans blindly
- **Daily briefing** — ask "what's on today?" for a prioritised summary of tasks (grouped by Work / Personal), events, and morning notes
- **Free-time matching** — tell Claude how much time you have and your energy level; it suggests goal-aligned activities

---

## Setup

```bash
git clone git@github.com:royvineet/llm_brain.git
cd llm_brain
```

**First-time setup** — create the data directory with template files:

```bash
bash scripts/init.sh
```

This creates `~/Documents/llm_brain/` with blank `tasks.yaml`, `events.yaml`, `index.yaml`, template profile files under `profiles/`, and a git repo in the data directory so your data is version-tracked from day one.

To use a different data location:

```bash
bash scripts/init.sh --data-dir /path/to/your/data
```

Then update `config/config.yaml` to match:

```yaml
storage:
  tasks: "/path/to/your/data/tasks.yaml"
  events: "/path/to/your/data/events.yaml"
  journal_dir: "/path/to/your/data/journal"
  profiles_dir: "/path/to/your/data/profiles"
  recurring_tasks: "/path/to/your/data/recurring_tasks.yaml"
```

Fill in the profile files in `~/Documents/llm_brain/profiles/` before your first session — they tell Claude who you are, your schedule, family, locations, and goals.

**Optional: back up your data to a remote**

The data directory is a plain git repo. Point it at any remote you like:

```bash
# GitHub (private repo recommended), NAS, any git server, etc.
git -C ~/Documents/llm_brain remote add origin <url>
git -C ~/Documents/llm_brain branch --set-upstream-to=origin/main main
```

`startup.sh` will automatically push/pull if a remote is configured, and skip sync silently if there is none.

Run the startup script before each session:

```bash
bash scripts/startup.sh
```

This pulls the latest project code from GitHub, syncs your data with the remote (if configured), rebuilds the index, purges expired todos, and generates any recurring tasks that are due. Then open the project in Claude Code:

```bash
claude
```

---

## Data layout

Data lives outside the repo at the path configured in `config/config.yaml`. Default: `~/Documents/llm_brain/`.

```
~/Documents/llm_brain/
├── index.yaml               # search index — auto-maintained
├── tasks.yaml               # all tasks (work and personal)
├── events.yaml              # calendar events
├── recurring_tasks.yaml     # recurring task templates (auto-generates tasks on startup)
├── journal/                 # YYYY-MM-DD.md per day
└── profiles/
    ├── directives.md   # guiding principles — read first for scheduling
    ├── individual.md   # identity, work, schedule, preferences
    ├── family.md       # family members, schedules, locations
    ├── friends.md      # friends context
    ├── environment.md  # key locations and commute times
    ├── goals.md        # personal goals and progress
    ├── tasks.md        # task-type durations, energy requirements, and category
    ├── calendar.md     # public holidays, vacations, business travel, blackout periods
    ├── reading_list.md # books and articles — read status, format, links
    └── checklists.md   # reusable travel and prep checklists
```

This directory is its own git repo (created by `init.sh`). Changes are tracked locally; push to a remote of your choice for backup.

---

## Task schema

```yaml
- id: 1
  title: "Example task"
  description: ""
  status: pending          # pending | in_progress | done | cancelled
  priority: medium         # low | medium | high
  category: personal       # work | personal
  due_date: "2026-03-15"   # or null
  tags: []
  created_at: "2026-03-13"
  ttl_days: 14             # null for permanent tasks; integer for ephemeral todos
  completed_at: null
```

- **`category`** separates work tasks from personal ones. Daily briefings group tasks by category (Work first, then Personal).
- **`ttl_days`** marks short-lived chores. Completed ephemeral tasks are auto-purged by `purge_todos.py` and summarised in the journal.

---

## Recurring tasks

For tasks that repeat on a schedule too complex for simple recurrence (e.g. "2nd Saturday of every month"), add a template to `recurring_tasks.yaml`:

```yaml
recurring_tasks:
  - id: rt1
    title: Charge drone battery
    description: Charge drone battery. Takes ~10 min.
    priority: low
    category: personal
    tags: [errands, drone]
    ttl_days: 7
    recurrence:
      type: monthly_nth_weekday
      n: 2        # 2nd occurrence
      weekday: 5  # 0=Monday ... 6=Sunday
    advance_days: 0   # generate task N days before due (0 = on the day)
    last_generated: null
```

`startup.sh` calls `generate_recurring_tasks.py` which creates a one-off entry in `tasks.yaml` when the occurrence is due. Generation is idempotent. Occurrences missed by ≤7 days are still generated on the next startup; older ones are skipped.

**Supported recurrence types:**

| Type | Fields | Example |
|------|--------|---------|
| `monthly_nth_weekday` | `n`, `weekday` | 2nd Saturday = `n: 2, weekday: 5` |

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/init.sh` | One-time setup: create data directory, template profiles, and blank data files |
| `scripts/startup.sh` | Pull latest code, sync data remote (if configured), rebuild index, purge expired todos, generate recurring tasks — run before each session |
| `scripts/reindex.py` | Rebuild `index.yaml` from scratch — called by `startup.sh`, or run manually after bulk file changes |
| `scripts/purge_todos.py` | Remove completed ephemeral tasks past their TTL; append a summary to the journal |
| `scripts/generate_recurring_tasks.py` | Generate due tasks from `recurring_tasks.yaml` templates; idempotent |
| `scripts/sync_check.sh` | Check whether the data directory is in sync with its remote; exits non-zero if behind or diverged |

---

## Example usage

Just talk to Claude Code naturally:

```
Add a high-priority work task to finish the Q1 report by Friday.
What's on my plate today?
Show me just my work tasks.
Log a journal entry: finished the API refactor, blocked on auth review.
I have 45 minutes free — what should I work on?
Find everything I have about the Berlin trip.
What's on my reading list?
```

---

## Requirements

- [Claude Code](https://claude.ai/code)
- Python 3.10+
- `PyYAML` — installed automatically by `startup.sh` via `requirements.txt`
