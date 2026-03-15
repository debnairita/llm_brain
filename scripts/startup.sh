#!/usr/bin/env bash
# Anvaya startup script.
# - Pulls latest Anvaya project code from GitHub (origin/main)
# - Syncs ~/Documents/anvaya with the NAS remote (pull if behind, push if ahead)
# - Rebuilds the index via reindex.py

set -euo pipefail

ANVAYA_DIR="${HOME}/Documents/anvaya"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PYTHON="$(command -v python3 || true)"
if [ -z "${PYTHON}" ]; then
  echo "Error: python3 not found in PATH." >&2
  exit 1
fi

# --- Pull latest project code from GitHub ---
echo "==> Pulling latest Anvaya code from GitHub..."
cd "${REPO_ROOT}"
if ! git fetch origin --quiet 2>/dev/null; then
  echo "WARNING: Could not reach GitHub. Skipping code pull."
  echo ""
else
  LOCAL=$(git rev-parse @)
  REMOTE=$(git rev-parse "origin/main" 2>/dev/null || true)
  BASE=$(git merge-base @ "origin/main" 2>/dev/null || true)

  if [ -z "${REMOTE}" ]; then
    echo "INFO: Could not resolve origin/main. Skipping code pull."
  elif [ "${LOCAL}" = "${REMOTE}" ]; then
    echo "Code up to date with GitHub."
  elif [ "${LOCAL}" = "${BASE}" ]; then
    BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "?")
    echo "Behind by ${BEHIND} commit(s) — pulling..."
    git pull origin main --rebase
    echo "Pull complete."
  elif [ "${REMOTE}" = "${BASE}" ]; then
    echo "INFO: Local code is ahead of GitHub. No pull needed."
  else
    echo "WARNING: Local code has diverged from GitHub. Skipping pull — resolve manually." >&2
    echo "  cd ${REPO_ROOT} && git status" >&2
  fi
fi
echo ""

if [ ! -d "${ANVAYA_DIR}/.git" ]; then
  echo "Error: ${ANVAYA_DIR} is not a git repository." >&2
  exit 1
fi

cd "${ANVAYA_DIR}"

echo "==> Fetching from NAS..."
if ! git fetch nas --quiet 2>/dev/null; then
  echo "WARNING: Could not reach NAS. Skipping sync — data may be stale."
  echo ""
else
  LOCAL=$(git rev-parse @)
  REMOTE=$(git rev-parse "@{u}" 2>/dev/null || true)
  BASE=$(git merge-base @ "@{u}" 2>/dev/null || true)

  if [ -z "${REMOTE}" ]; then
    echo "INFO: No upstream tracking branch set. Skipping sync."
  elif [ "${LOCAL}" = "${REMOTE}" ]; then
    echo "Sync OK: up to date with NAS."
  elif [ "${LOCAL}" = "${BASE}" ]; then
    BEHIND=$(git rev-list --count HEAD..nas/main 2>/dev/null || echo "?")
    echo "SYNC BEHIND by ${BEHIND} commit(s) — pulling..."
    git pull nas main --rebase
    echo "Pull complete."
  elif [ "${REMOTE}" = "${BASE}" ]; then
    AHEAD=$(git rev-list --count nas/main..HEAD 2>/dev/null || echo "?")
    echo "SYNC AHEAD by ${AHEAD} commit(s) — pushing..."
    git push nas main
    echo "Push complete."
  else
    echo "ERROR: Local and NAS have diverged. Resolve manually before continuing." >&2
    echo "  cd ${ANVAYA_DIR} && git status" >&2
    exit 1
  fi
fi

echo ""
echo "==> Rebuilding index..."
"${PYTHON}" "${REPO_ROOT}/scripts/reindex.py"
