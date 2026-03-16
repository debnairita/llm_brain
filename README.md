# llm_brain

A plain-file personal assistant powered by Claude Code. Manages tasks, calendar events, a daily journal, and an ingested file store — all as plain YAML and Markdown on your filesystem.

---

## What it does

- **Tasks** — add, update, and prioritise to-dos
- **Events** — track calendar events
- **Journal** — one Markdown file per day
- **Files** — ingest documents, photos, and notes with searchable metadata
- **Search** — hierarchical lookup via an index file so Claude never scans blindly
- **Daily briefing** — ask "what's on today?" for a prioritised summary of tasks, events, and morning notes

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

This creates `~/Documents/llm_brain/` with blank `tasks.yaml`, `events.yaml`, `index.yaml`, and template profile files under `profiles/`. It also initialises a git repo in the data directory so your data is version-tracked from day one. Backups and remote sync are your responsibility — see below.

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

This syncs with your remote (if configured), rebuilds the index, and purges expired todos. Then open the project in Claude Code:

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
└── files/
    ├── documents/      # PDFs, spreadsheets, text files
    ├── photos/         # images
    └── notes/          # short notes and clippings
```

This directory is its own git repo (created by `init.sh`). Changes are tracked locally; push to a remote of your choice for backup.

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/init.sh` | One-time setup: create data directory, template profiles, and blank data files |
| `scripts/startup.sh` | Sync with remote (if configured), rebuild index, purge expired todos — run before each session |
| `scripts/reindex.py` | Rebuild `index.yaml` from scratch — called by `startup.sh`, or run manually after bulk file changes |

---

## Example usage

Just talk to Claude Code naturally:

```
Add a high-priority task to review the Q1 report by Friday.
What's on my plate today?
Log a journal entry: finished the API refactor, blocked on auth review.
Ingest ~/Downloads/invoice-april.pdf
Find everything I have about the Berlin trip.
```

---

## Requirements

- [Claude Code](https://claude.ai/code)
- Python 3.10+ (for scripts)
- `PyPDF2`, `Pillow`, `pytesseract` — only needed if ingesting PDFs or images
