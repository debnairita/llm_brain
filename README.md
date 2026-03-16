# llm_brain

A plain-file personal assistant powered by Claude Code. Manages tasks, calendar events, a daily journal, and personal profiles — all as plain YAML and Markdown on your filesystem.

---

## What it does

- **Tasks** — add, update, and prioritise to-dos; ephemeral todos auto-purge after completion
- **Events** — track calendar events with automatic commute and schedule enrichment
- **Journal** — one Markdown file per day; tag entries for fast lookup
- **Profiles** — personal context (identity, family, locations, goals, calendar, reading list, checklists) that Claude reads when scheduling or suggesting activities
- **Search** — hierarchical lookup via an index file so Claude never scans blindly
- **Daily briefing** — ask "what's on today?" for a prioritised summary of tasks, events, and morning notes
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

This pulls the latest project code from GitHub, syncs your data with the remote (if configured), rebuilds the index, and purges expired todos. Then open the project in Claude Code:

```bash
claude
```

---

## Data layout

Data lives outside the repo at the path configured in `config/config.yaml`. Default: `~/Documents/llm_brain/`.

```
~/Documents/llm_brain/
├── index.yaml          # search index — auto-maintained
├── tasks.yaml          # all tasks
├── events.yaml         # calendar events
├── journal/            # YYYY-MM-DD.md per day
└── profiles/
    ├── directives.md   # guiding principles — read first for scheduling
    ├── individual.md   # identity, work, schedule, preferences
    ├── family.md       # family members, schedules, locations
    ├── friends.md      # friends context
    ├── environment.md  # key locations and commute times
    ├── goals.md        # personal goals and progress
    ├── tasks.md        # task-type durations and energy requirements
    ├── calendar.md     # public holidays, vacations, blackout periods
    ├── reading_list.md # books and articles
    └── checklists.md   # reusable travel and prep checklists
```

This directory is its own git repo (created by `init.sh`). Changes are tracked locally; push to a remote of your choice for backup.

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/init.sh` | One-time setup: create data directory, template profiles, and blank data files |
| `scripts/startup.sh` | Pull latest code, sync data remote (if configured), rebuild index, purge expired todos — run before each session |
| `scripts/reindex.py` | Rebuild `index.yaml` from scratch — called by `startup.sh`, or run manually after bulk file changes |
| `scripts/purge_todos.py` | Remove completed ephemeral tasks past their TTL; append a summary to the journal |
| `scripts/sync_check.sh` | Check whether the data directory is in sync with its remote; exits non-zero if behind or diverged |

---

## Example usage

Just talk to Claude Code naturally:

```
Add a high-priority task to review the Q1 report by Friday.
What's on my plate today?
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
