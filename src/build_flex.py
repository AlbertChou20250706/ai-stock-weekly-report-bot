"""Build a LINE Flex Message (card layout) from output/report_data.json + the
chart image already pushed to the repo. Falls back to nothing if generate_report.py
had to fall back to plain text (send_line.py handles that case directly).
"""

import json
import os
import pathlib
from datetime import date

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_PATH = OUTPUT_DIR / "report_data.json"

UP_COLOR = "#D32F2F"    # TW convention: red = up
DOWN_COLOR = "#2E7D32"  # TW convention: green = down
HEADER_BG = "#1A2942"
MUTED = "#666666"
INK = "#222222"


def change_color(pct_str: str) -> str:
    try:
        return UP_COLOR if float(pct_str) >= 0 else DOWN_COLOR
    except ValueError:
        return INK


def chart_url() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "AlbertChou20250706/ai-stock-weekly-report-bot")
    today = date.today().isoformat()
    return f"https://raw.githubusercontent.com/{repo}/main/charts/tw_index_{today}.png"


def text(content: str, **kwargs) -> dict:
    return {"type": "text", "text": content, "wrap": True, **kwargs}


def separator() -> dict:
    return {"type": "separator", "margin": "lg"}


def section_title(label: str) -> dict:
    return text(label, weight="bold", size="md", margin="lg", color=INK)


def institutional_line(inst: dict | None) -> dict | None:
    if not inst or inst.get("total") is None:
        return None
    parts = []
    for label, key in [("外資", "foreign"), ("投信", "trust"), ("自營", "dealer")]:
        v = inst.get(key)
        if v is not None:
            parts.append(f"{label} {v:+,}")
    if not parts:
        return None
    total = inst["total"]
    return text(
        f"三大法人（張）：{' / '.join(parts)} ｜ 合計 {total:+,}",
        size="xxs",
        color=change_color(str(total)) if total != 0 else MUTED,
        margin="xs",
    )


def tracked_row(t: dict) -> dict:
    contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                text(f"{t['symbol']} {t['name']}", size="sm", color=INK, flex=3),
                text(f"{t['change_pct']}%", size="sm", align="end", weight="bold", color=change_color(t["change_pct"]), flex=1),
                text(f"{t['price']} 元", size="sm", align="end", color=MUTED, flex=2),
            ],
        }
    ]
    inst_line = institutional_line(t.get("institutional"))
    if inst_line:
        contents.append(inst_line)
    return {"type": "box", "layout": "vertical", "margin": "sm", "paddingBottom": "sm", "contents": contents}


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
        "contents": [
            text(f"🔗 {n['title']}", size="sm", color="#2563EB", wrap=True),
        ],
    }


def build_bubble(data: dict) -> dict:
    date_range = data["date_range"]
    index = data["index"]

    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                text(index["name"], size="sm", color=MUTED, flex=1),
                text(f"{index['close']}", size="xxl", weight="bold", align="end", color=INK, flex=2),
            ],
        },
        text(f"{'▲' if index['change_pct'] >= 0 else '▼'} {index['change_pct']}%",
             align="end", weight="bold", size="md", color=change_color(str(index["change_pct"]))),
        separator(),
        section_title("本週市場總結"),
        text(data["summary"], size="sm", color=INK, margin="sm"),
        separator(),
        section_title("追蹤股代號動態"),
    ]
    body_contents += [tracked_row(t) for t in data["tracked"]]

    if data["highlights"]:
        body_contents += [separator(), section_title("產業／ETF 亮點")]
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
            "contents": [
                text(f"⚠️ {data['disclaimer']}", size="xxs", color="#92400E", wrap=True),
            ],
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
        print("report_data.json is not in structured mode, skipping flex build")
        return

    flex_message = {
        "type": "flex",
        "altText": f"{data['title']}（{data['date_range']['start']} - {data['date_range']['end']}）",
        "contents": build_bubble(data),
    }

    out_path = OUTPUT_DIR / "flex_message.json"
    out_path.write_text(json.dumps(flex_message, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
