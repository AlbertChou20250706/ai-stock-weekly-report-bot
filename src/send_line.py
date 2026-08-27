"""Push the generated weekly report to one or more LINE targets (users or groups).

Usage: python src/send_line.py [path-to-report.txt]   (defaults to output/report.txt)
"""

import os
import pathlib
import sys

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_REPORT_PATH = BASE_DIR / "output" / "report.txt"

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def push_message(token: str, target_id: str, text: str) -> None:
    response = requests.post(
        LINE_PUSH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": target_id, "messages": [{"type": "text", "text": text}]},
        timeout=30,
    )
    response.raise_for_status()


def main() -> None:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    target_ids = [t.strip() for t in os.environ["LINE_PUSH_TARGET_IDS"].split(",") if t.strip()]
    if not target_ids:
        raise RuntimeError("LINE_PUSH_TARGET_IDS is empty")

    report_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPORT_PATH
    report_text = report_path.read_text(encoding="utf-8")

    for target_id in target_ids:
        push_message(token, target_id, report_text)
        print(f"sent to {target_id}")


if __name__ == "__main__":
    main()
