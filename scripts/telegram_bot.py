#!/usr/bin/env python3
"""
Telegram bot — direct relay to Claude Code.

Every message sent to the bot is passed to `claude -p "<message>"` and
the response is sent back to Telegram.

Usage:
    python scripts/telegram_bot.py
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
REPO_ROOT = Path(__file__).parent.parent
POLL_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_telegram_config(cfg: dict) -> dict:
    tg_path = Path(cfg["telegram"]["config_file"]).expanduser()
    if not tg_path.exists():
        raise FileNotFoundError(f"Telegram config not found at {tg_path}.")
    with open(tg_path) as f:
        return json.load(f)


def save_telegram_config(cfg: dict, tg: dict):
    tg_path = Path(cfg["telegram"]["config_file"]).expanduser()
    with open(tg_path, "w") as f:
        json.dump(tg, f, indent=2)


# ---------------------------------------------------------------------------
# Telegram API helpers
# ---------------------------------------------------------------------------

def api(token: str, method: str, **kwargs) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    resp = requests.post(url, json=kwargs, timeout=60)
    resp.raise_for_status()
    return resp.json()


def send_message(token: str, chat_id: int, text: str):
    # Telegram message limit is 4096 chars
    for i in range(0, max(1, len(text)), 4096):
        api(token, "sendMessage", chat_id=chat_id, text=text[i:i+4096])


def get_updates(token: str, offset: int) -> list:
    result = api(token, "getUpdates", offset=offset, timeout=POLL_TIMEOUT)
    return result.get("result", [])


# ---------------------------------------------------------------------------
# Claude relay
# ---------------------------------------------------------------------------

def ask_claude(message: str) -> str:
    result = subprocess.run(
        ["claude", "-p", message],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    output = result.stdout.strip()
    if result.returncode != 0 and not output:
        output = result.stderr.strip() or "Error: no response from Claude."
    return output or "No response."


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    cfg = load_config()
    tg = load_telegram_config(cfg)
    token = tg.get("token")
    if not token:
        print("ERROR: No token in telegram.json", file=sys.stderr)
        sys.exit(1)

    chat_id = tg.get("chat_id")
    offset = 0

    print("Bot started. Relaying all messages to Claude Code...")
    if not chat_id:
        print("chat_id not set — send any message to the bot to register it.")

    while True:
        try:
            updates = get_updates(token, offset)
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}. Retrying in 5s...")
            time.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message") or update.get("edited_message")
            if not msg:
                continue

            incoming_chat_id = msg["chat"]["id"]
            text = msg.get("text", "").strip()
            if not text:
                continue

            # Auto-save chat_id on first contact
            if not chat_id:
                chat_id = incoming_chat_id
                tg["chat_id"] = chat_id
                save_telegram_config(cfg, tg)
                print(f"chat_id saved: {chat_id}")

            if incoming_chat_id != chat_id:
                print(f"Ignored message from unknown chat_id: {incoming_chat_id}")
                continue

            if text == "/start":
                send_message(token, chat_id, "llm_brain bot ready.")
                continue

            print(f"→ Claude: {text}")
            reply = ask_claude(text)
            print(f"← Reply: {reply[:80]}...")
            send_message(token, chat_id, reply)


if __name__ == "__main__":
    main()
