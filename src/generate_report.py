"""Generate the weekly stock report as structured data (for a Flex Message card),
via the Claude API. Falls back to plain text if the model doesn't follow the
delimiter format, so a report still goes out either way.
"""

import json
import os
import pathlib
import re
from datetime import date

import anthropic

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "latest.json"
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.md"
ARCHIVE_DIR = BASE_DIR / "reports"
OUTPUT_DIR = BASE_DIR / "output"

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
DISCLAIMER = "投資一定有風險，基金/ETF/股票投資有賺有賠，以上資訊非投資建議"

SECTION_RE = re.compile(r"^##([A-Z]+)##\s*$", re.MULTILINE)


def build_user_content(market_data: dict) -> str:
    return (
        "以下是本週台股市場的結構化資料（JSON），請依照系統提示的格式輸出：\n\n"
        + json.dumps(market_data, ensure_ascii=False, indent=2)
    )


def parse_sections(text: str) -> dict | None:
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return None

    raw = {}
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw[name] = text[start:end].strip()

    if "SUMMARY" not in raw:
        return None

    tracked = []
    for line in raw.get("TRACKED", "").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 4:
            tracked.append({"symbol": parts[0], "name": parts[1], "change_pct": parts[2], "price": parts[3]})

    news = []
    for line in raw.get("NEWS", "").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 2 and parts[1].startswith("http"):
            news.append({"title": parts[0], "url": parts[1]})

    return {
        "summary": raw.get("SUMMARY", "").strip(),
        "tracked": tracked,
        "highlights": [l.strip() for l in raw.get("HIGHLIGHTS", "").splitlines() if l.strip()],
        "risks": [l.strip() for l in raw.get("RISKS", "").splitlines() if l.strip()],
        "outlook": raw.get("OUTLOOK", "").strip(),
        "news": news,
        "disclaimer": DISCLAIMER,
    }


def render_markdown(parsed: dict, date_range: dict) -> str:
    lines = [f"台股週報（{date_range['start']} - {date_range['end']}）", ""]
    lines += ["一、本週市場總結", parsed["summary"], ""]
    lines += ["二、追蹤股代號動態"]
    lines += [f"{t['symbol']} {t['name']}：{t['change_pct']}%，收在 {t['price']} 元" for t in parsed["tracked"]]
    lines += [""]
    lines += ["三、產業／ETF 亮點"] + parsed["highlights"] + [""]
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
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "medium"},
        system=system_prompt,
        tools=[{
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": 3,
            "allowed_domains": [
                "tw.stock.yahoo.com",
                "cnyes.com",
                "money.udn.com",
                "ctee.com.tw",
                "moneydj.com",
                "wantgoo.com",
            ],
        }],
        messages=[{"role": "user", "content": build_user_content(market_data)}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    archive_path = ARCHIVE_DIR / f"{today}.md"

    parsed = parse_sections(raw_text)
    if parsed is None:
        print("warning: could not parse structured sections, falling back to plain text")
        report_text = raw_text if DISCLAIMER in raw_text else raw_text.rstrip() + "\n\n" + DISCLAIMER
        archive_path.write_text(report_text, encoding="utf-8")
        (OUTPUT_DIR / "report.txt").write_text(report_text, encoding="utf-8")
        (OUTPUT_DIR / "report_data.json").write_text(json.dumps({"mode": "plain_text"}), encoding="utf-8")
        print(f"wrote {archive_path} (plain text fallback)")
        return

    parsed["title"] = "台股週報"
    parsed["date_range"] = market_data["date_range"]
    parsed["index"] = market_data["index"]

    archive_text = render_markdown(parsed, market_data["date_range"])
    archive_path.write_text(archive_text, encoding="utf-8")
    (OUTPUT_DIR / "report.txt").write_text(archive_text, encoding="utf-8")

    parsed["mode"] = "structured"
    (OUTPUT_DIR / "report_data.json").write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"wrote {archive_path} and output/report_data.json")


if __name__ == "__main__":
    main()
