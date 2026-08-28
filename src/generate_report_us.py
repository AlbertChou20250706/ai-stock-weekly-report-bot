"""Generate the weekly US stock report text via the Claude API."""

import json
import os
import pathlib
from datetime import date

import anthropic

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "latest_us.json"
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt_us.md"
ARCHIVE_DIR = BASE_DIR / "reports"
OUTPUT_PATH = BASE_DIR / "output" / "report_us.txt"

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
DISCLAIMER = "投資一定有風險，基金/ETF/股票投資有賺有賠，以上資訊非投資建議"


def build_user_content(market_data: dict) -> str:
    return (
        "以下是本週美股市場的結構化資料（JSON），請依照系統提示的格式撰寫週報：\n\n"
        + json.dumps(market_data, ensure_ascii=False, indent=2)
    )


def ensure_disclaimer(text: str) -> str:
    if DISCLAIMER in text:
        return text
    print("warning: disclaimer missing from model output, appending it")
    return text.rstrip() + "\n\n" + DISCLAIMER


def main() -> None:
    market_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "medium"},
        system=system_prompt,
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}],
        messages=[{"role": "user", "content": build_user_content(market_data)}],
    )

    report_text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    report_text = ensure_disclaimer(report_text)

    today = date.today().isoformat()
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = ARCHIVE_DIR / f"us_{today}.md"
    archive_path.write_text(report_text, encoding="utf-8")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report_text, encoding="utf-8")

    print(f"wrote {archive_path} and {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
