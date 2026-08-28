"""Generate the weekly US stock report as structured data (for a Flex Message
card), via the Claude API. Falls back to plain text if the model doesn't
follow the delimiter format, so a report still goes out either way. Reuses
generate_report.py's parse_sections() since both reports share the same
##SECTION## delimiter format.
"""

import json
import os
import pathlib
from datetime import date

import anthropic

from generate_report import parse_sections

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "latest_us.json"
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt_us.md"
ARCHIVE_DIR = BASE_DIR / "reports"
OUTPUT_DIR = BASE_DIR / "output"

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
DISCLAIMER = "投資一定有風險，基金/ETF/股票投資有賺有賠，以上資訊非投資建議"


def build_user_content(market_data: dict) -> str:
    return (
        "以下是本週美股市場的結構化資料（JSON），請依照系統提示的格式輸出：\n\n"
        + json.dumps(market_data, ensure_ascii=False, indent=2)
    )


def render_markdown(parsed: dict, date_range: dict) -> str:
    lines = [f"美股週報（{date_range['start']} - {date_range['end']}）", ""]
    lines += ["一、本週市場總結", parsed["summary"], ""]
    lines += ["二、追蹤股代號動態"]
    lines += [
        f"{t['symbol']} {t['name']}：{t['change_pct']}%，收在 {t['price']} 美元"
        for t in parsed["tracked"]
    ]
    lines += [""]
    lines += ["三、科技股亮點"] + parsed["highlights"] + [""]
    lines += ["四、風險提示"] + parsed["risks"] + [""]
    lines += ["五、下週觀察重點", parsed["outlook"], ""]
    if parsed["news"]:
        lines += ["六、相關新聞來源"]
        lines += [f"{n['title']}\n{n['url']}" for n in parsed["news"]]
        lines += [""]
    lines += [parsed["disclaimer"]]
    return "\n".join(lines)


def main() -> None:
    market_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    client = anthropic.Anthropic()
    request_kwargs = dict(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "medium"},
        system=system_prompt,
        tools=[{
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": 3,
            # Anthropic's crawler accessibility to a given domain can change
            # over time (robots.txt / bot-blocking on the site's end); a
            # domain it currently can't reach makes the whole request fail
            # with a 400, not just that one search. See the except clause
            # below for the fallback that keeps a report going out anyway.
            "allowed_domains": [
                "bloomberg.com",
                "cnbc.com",
                "finance.yahoo.com",
            ],
        }],
        messages=[{"role": "user", "content": build_user_content(market_data)}],
    )
    try:
        response = client.messages.create(**request_kwargs)
    except anthropic.BadRequestError as exc:
        if "not accessible to our user agent" in str(exc):
            print(f"warning: web_search domain access error, retrying without web_search: {exc}")
            request_kwargs.pop("tools")
            response = client.messages.create(**request_kwargs)
        else:
            raise

    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    archive_path = ARCHIVE_DIR / f"us_{today}.md"

    parsed = parse_sections(raw_text)
    if parsed is None:
        print("warning: could not parse structured sections, falling back to plain text")
        report_text = raw_text if DISCLAIMER in raw_text else raw_text.rstrip() + "\n\n" + DISCLAIMER
        archive_path.write_text(report_text, encoding="utf-8")
        (OUTPUT_DIR / "report_us.txt").write_text(report_text, encoding="utf-8")
        (OUTPUT_DIR / "report_us_data.json").write_text(json.dumps({"mode": "plain_text"}), encoding="utf-8")
        print(f"wrote {archive_path} (plain text fallback)")
        return

    parsed["title"] = "美股週報"
    parsed["date_range"] = market_data["date_range"]
    parsed["indices"] = market_data["indices"]
    parsed["disclaimer"] = DISCLAIMER

    archive_text = render_markdown(parsed, market_data["date_range"])
    archive_path.write_text(archive_text, encoding="utf-8")
    (OUTPUT_DIR / "report_us.txt").write_text(archive_text, encoding="utf-8")

    parsed["mode"] = "structured"
    (OUTPUT_DIR / "report_us_data.json").write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"wrote {archive_path} and output/report_us_data.json")


if __name__ == "__main__":
    main()
