#!/usr/bin/env bash
# Anvaya startup script.
# - Pulls latest Anvaya project code from GitHub (origin/main)
# - Syncs ~/Documents/anvaya with the NAS remote (pull if behind, push if ahead)
# - Rebuilds the index via reindex.py

set -euo pipefail

ANVAYA_DIR="${HOME}/Documents/anvaya"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- Detect OS ---
OS="$(uname -s)"
case "${OS}" in
  Darwin) OS_NAME="macOS" ;;
  Linux)
    if grep -qi ubuntu /etc/os-release 2>/dev/null; then
      OS_NAME="Ubuntu"
    else
      OS_NAME="Linux"
    fi
    ;;
  *) OS_NAME="${OS}" ;;
esac
echo "==> Detected OS: ${OS_NAME}"

# --- Check and install system dependencies ---
if [ "${OS_NAME}" = "Ubuntu" ]; then
  MISSING_APT=()
  command -v tesseract >/dev/null 2>&1 || MISSING_APT+=("tesseract-ocr")
  python3 -m venv --help >/dev/null 2>&1 || MISSING_APT+=("python3-venv")
  dpkg -s libjpeg-dev >/dev/null 2>&1 || MISSING_APT+=("libjpeg-dev")
  dpkg -s zlib1g-dev >/dev/null 2>&1 || MISSING_APT+=("zlib1g-dev")
  if [ ${#MISSING_APT[@]} -gt 0 ]; then
    echo "==> Installing missing system packages: ${MISSING_APT[*]}"
    sudo apt-get install -y "${MISSING_APT[@]}"
  fi
elif [ "${OS_NAME}" = "macOS" ]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "WARNING: Homebrew not found. If packages are missing, install it from https://brew.sh" >&2
  else
    MISSING_BREW=()
    command -v tesseract >/dev/null 2>&1 || MISSING_BREW+=("tesseract")
    if [ ${#MISSING_BREW[@]} -gt 0 ]; then
      echo "==> Installing missing Homebrew packages: ${MISSING_BREW[*]}"
      brew install "${MISSING_BREW[@]}"
    fi
  fi
fi
echo ""

SYSTEM_PYTHON="$(command -v python3 || true)"
if [ -z "${SYSTEM_PYTHON}" ]; then
  echo "Error: python3 not found in PATH." >&2
  exit 1
fi

# --- Set up virtual environment ---
VENV_DIR="${REPO_ROOT}/.venv"
if [ ! -d "${VENV_DIR}" ]; then
  echo "==> Creating virtual environment..."
  if ! "${SYSTEM_PYTHON}" -m venv "${VENV_DIR}"; then
    if [ "${OS_NAME}" = "Ubuntu" ]; then
      echo "Error: venv creation failed. Run: sudo apt install python3-venv" >&2
    else
      echo "Error: venv creation failed." >&2
    fi
    exit 1
  fi
fi
PYTHON="${VENV_DIR}/bin/python3"
echo "==> Installing/updating requirements..."
"${VENV_DIR}/bin/pip" install -q -r "${REPO_ROOT}/requirements.txt"
echo "Requirements up to date."
echo ""
echo "To activate the venv in your shell: source .venv/bin/activate"
echo ""

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
