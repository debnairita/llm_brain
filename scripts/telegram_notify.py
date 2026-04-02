#!/usr/bin/env python3
"""
Send a Telegram message to the configured chat.

Usage (CLI):
    python scripts/telegram_notify.py "Hello from llm_brain"

Usage (module):
    from scripts.telegram_notify import send
    send("Task due in 30 minutes: Buy groceries")

Config is read from ~/Documents/llm_brain/telegram.json:
    {
        "token": "YOUR_BOT_TOKEN",
        "chat_id": 123456789
    }

Run telegram_bot.py once and send any message to the bot to auto-populate chat_id.
"""

import json
import sys
from pathlib import Path

import requests
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


def load_telegram_config() -> dict:
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    tg_path = Path(cfg["telegram"]["config_file"]).expanduser()
    if not tg_path.exists():
        raise FileNotFoundError(
            f"Telegram config not found at {tg_path}.\n"
            "Create it with: {\"token\": \"YOUR_BOT_TOKEN\", \"chat_id\": null}"
        )
    with open(tg_path) as f:
        return json.load(f)


def send(message: str) -> bool:
    """Send a message to the configured Telegram chat. Returns True on success."""
    tg = load_telegram_config()
    token = tg.get("token")
    chat_id = tg.get("chat_id")

    if not token:
        print("ERROR: No bot token in telegram.json", file=sys.stderr)
        return False
    if not chat_id:
        print("ERROR: chat_id not set in telegram.json. Start the bot and send it a message first.", file=sys.stderr)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)

    if not resp.ok:
        print(f"ERROR: Telegram API error: {resp.status_code} {resp.text}", file=sys.stderr)
        return False
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/telegram_notify.py \"Your message here\"")
        sys.exit(1)
    message = " ".join(sys.argv[1:])
    success = send(message)
    sys.exit(0 if success else 1)
