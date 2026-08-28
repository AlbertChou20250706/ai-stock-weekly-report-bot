"""Push a generated report to one or more LINE targets (users or groups).

Usage: python src/send_line.py [tw|us]   (default: tw)
Sends output/flex_message[_us].json as a Flex Message if present, otherwise
falls back to output/report[_us].txt as plain text.
"""

import json
import os
import pathlib
import sys

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

REPORTS = {
    "tw": {"flex": OUTPUT_DIR / "flex_message.json", "text": OUTPUT_DIR / "report.txt"},
    "us": {"flex": OUTPUT_DIR / "flex_message_us.json", "text": OUTPUT_DIR / "report_us.txt"},
}


def push(token: str, target_id: str, message: dict) -> None:
    response = requests.post(
        LINE_PUSH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": target_id, "messages": [message]},
        timeout=30,
    )
    response.raise_for_status()


def main() -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    target_ids = [t.strip() for t in os.environ["LINE_PUSH_TARGET_IDS"].split(",") if t.strip()]
    if not target_ids:
        raise RuntimeError("LINE_PUSH_TARGET_IDS is empty")

    market = sys.argv[1] if len(sys.argv) > 1 else "tw"
    if market not in REPORTS:
        raise RuntimeError(f"unknown market {market!r}, expected one of {list(REPORTS)}")

    paths = REPORTS[market]
    if paths["flex"].exists():
        message = json.loads(paths["flex"].read_text(encoding="utf-8"))
    else:
        message = {"type": "text", "text": paths["text"].read_text(encoding="utf-8")}

    for target_id in target_ids:
        push(token, target_id, message)
        print(f"sent to {target_id}")


if __name__ == "__main__":
    main()
