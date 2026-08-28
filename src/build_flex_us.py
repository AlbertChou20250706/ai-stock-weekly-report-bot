"""Build a LINE Flex Message (card layout) for the US weekly report, from
output/report_us_data.json + the chart image already pushed to the repo.
Falls back to nothing if generate_report_us.py had to fall back to plain
text (send_line.py handles that case directly).
"""

import json
import os
import pathlib
from datetime import date

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_PATH = OUTPUT_DIR / "report_us_data.json"

UP_COLOR = "#2E7D32"    # US convention: green = up
DOWN_COLOR = "#D32F2F"  # US convention: red = down
HEADER_BG = "#1A2942"
MUTED = "#666666"
INK = "#222222"


def change_color(value) -> str:
    try:
        return UP_COLOR if float(value) >= 0 else DOWN_COLOR
    except (TypeError, ValueError):
        return INK


def chart_url() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "AlbertChou20250706/ai-stock-weekly-report-bot")
    today = date.today().isoformat()
    return f"https://raw.githubusercontent.com/{repo}/main/charts/us_index_{today}.png"


def text(content: str, **kwargs) -> dict:
    return {"type": "text", "text": content, "wrap": True, **kwargs}


def separator() -> dict:
    return {"type": "separator", "margin": "lg"}


def section_title(label: str) -> dict:
    return text(label, weight="bold", size="md", margin="lg", color=INK)


def index_row(idx: dict) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "margin": "sm",
        "contents": [
            text(idx["name"], size="sm", color=MUTED, flex=2),
            text(f"{idx['close']}", size="sm", align="end", color=INK, flex=2),
            text(f"{'▲' if idx['change_pct'] >= 0 else '▼'} {idx['change_pct']}%", size="sm",
                 align="end", weight="bold", color=change_color(idx["change_pct"]), flex=2),
        ],
    }


def tracked_row(t: dict) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "margin": "sm",
        "contents": [
            text(f"{t['symbol']} {t['name']}", size="sm", color=INK, flex=3),
            text(f"{t['change_pct']}%", size="sm", align="end", weight="bold",
                 color=change_color(t["change_pct"]), flex=1),
            text(f"${t['price']}", size="sm", align="end", color=MUTED, flex=2),
        ],
    }


def bullet(content: str) -> dict:
    return {
        "type": "box",
        "layout": "baseline",
        "margin": "sm",
        "contents": [
            text("•", size="sm", color=MUTED, flex=0),
            text(content, size="sm", color=INK, margin="sm"),
        ],
    }


def news_row(n: dict) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "margin": "sm",
        "action": {"type": "uri", "uri": n["url"]},
        "contents": [text(f"🔗 {n['title']}", size="sm", color="#2563EB", wrap=True)],
    }


def build_bubble(data: dict) -> dict:
    date_range = data["date_range"]

    body_contents = [section_title("三大指數")]
    body_contents += [index_row(idx) for idx in data["indices"]]

    body_contents += [
        separator(),
        section_title("本週市場總結"),
        text(data["summary"], size="sm", color=INK, margin="sm"),
        separator(),
        section_title("追蹤股代號動態"),
    ]
    body_contents += [tracked_row(t) for t in data["tracked"]]

    if data["highlights"]:
        body_contents += [separator(), section_title("科技股亮點")]
        body_contents += [bullet(h) for h in data["highlights"]]

    if data["risks"]:
        body_contents += [separator(), section_title("風險提示")]
        body_contents += [bullet(r) for r in data["risks"]]

    body_contents += [
        separator(),
        section_title("下週觀察重點"),
        text(data["outlook"], size="sm", color=INK, margin="sm"),
    ]

    if data["news"]:
        body_contents += [separator(), section_title("相關新聞來源")]
        body_contents += [news_row(n) for n in data["news"]]

    body_contents += [
        {
            "type": "box",
            "layout": "vertical",
            "margin": "lg",
            "paddingAll": "10px",
            "backgroundColor": "#FFF4E5",
            "cornerRadius": "8px",
            "contents": [text(f"⚠️ {data['disclaimer']}", size="xxs", color="#92400E", wrap=True)],
        }
    ]

    return {
        "type": "bubble",
        "size": "giga",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": HEADER_BG,
            "paddingAll": "16px",
            "contents": [
                text(data["title"], color="#FFFFFF", size="xl", weight="bold"),
                text(f"{date_range['start']} - {date_range['end']}", color="#A8B8D0", size="xs", margin="xs"),
            ],
        },
        "hero": {
            "type": "image",
            "url": chart_url(),
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "fit",
            "backgroundColor": "#FFFFFF",
        },
        "body": {"type": "box", "layout": "vertical", "contents": body_contents},
    }


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if data.get("mode") != "structured":
        print("report_us_data.json is not in structured mode, skipping flex build")
        return

    flex_message = {
        "type": "flex",
        "altText": f"{data['title']}（{data['date_range']['start']} - {data['date_range']['end']}）",
        "contents": build_bubble(data),
    }

    out_path = OUTPUT_DIR / "flex_message_us.json"
    out_path.write_text(json.dumps(flex_message, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
