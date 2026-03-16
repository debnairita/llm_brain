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
pip install -r requirements.txt   # optional — only needed for file ingestion
```

Configure your data directory in `config/config.yaml` (default: `~/Documents/llm_brain/`):

```yaml
storage:
  tasks: "~/Documents/llm_brain/tasks.yaml"
  events: "~/Documents/llm_brain/events.yaml"
  journal_dir: "~/Documents/llm_brain/journal"
  files_dir: "~/Documents/llm_brain/files"
```

Create the data directory:

```bash
mkdir -p ~/Documents/llm_brain/journal \
         ~/Documents/llm_brain/files/documents \
         ~/Documents/llm_brain/files/photos \
         ~/Documents/llm_brain/files/notes
```

Run the startup script before each session:

```bash
bash scripts/startup.sh
```

This syncs `~/Documents/llm_brain/` with the NAS remote (pulling if behind, pushing if ahead) and rebuilds the index. Then open the project in Claude Code:

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

Nothing in this directory is committed to git — it is purely local personal data.

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/startup.sh` | Sync with NAS remote and rebuild the index — run before each session |
| `scripts/ingest.py <file>` | Extract text/metadata from a file and print JSON for Claude to classify and store |
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
