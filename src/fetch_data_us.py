"""Fetch weekly US market data and write it as structured JSON for generate_report_us.py."""

import json
import pathlib

import yfinance as yf

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
WATCHLIST_PATH = BASE_DIR / "config" / "watchlist_us.json"
OUTPUT_PATH = BASE_DIR / "data" / "latest_us.json"


def fetch_weekly_change(symbol: str) -> dict:
    history = yf.Ticker(symbol).history(period="6d")
    if history.empty or len(history) < 2:
        raise RuntimeError(f"no usable price history for {symbol}")

    first_open = float(history["Open"].iloc[0])
    last_close = float(history["Close"].iloc[-1])
    change_pct = (last_close - first_open) / first_open * 100

    return {
        "symbol": symbol,
        "date_start": history.index[0].strftime("%Y-%m-%d"),
        "date_end": history.index[-1].strftime("%Y-%m-%d"),
        "open": round(first_open, 2),
        "close": round(last_close, 2),
        "change_pct": round(change_pct, 2),
    }


def main() -> None:
    watchlist = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))

    indices = []
    for entry in watchlist["indices"]:
        data = fetch_weekly_change(entry["symbol"])
        data["name"] = entry["name"]
        indices.append(data)

    must_watch = []
    ranked_pool = []
    for entry in watchlist["watchlist"]:
        try:
            data = fetch_weekly_change(entry["symbol"])
        except RuntimeError as exc:
            print(f"warning: skipping {entry['symbol']}: {exc}")
            continue
        data["name"] = entry["name"]
        if entry.get("category") == "must_watch":
            must_watch.append(data)
        else:
            ranked_pool.append(data)

    ranked_sorted = sorted(ranked_pool, key=lambda e: e["change_pct"], reverse=True)

    result = {
        "date_range": {
            "start": indices[0]["date_start"],
            "end": indices[0]["date_end"],
        },
        "indices": indices,
        "must_watch": must_watch,
        "top_gainers": ranked_sorted[:5],
        "top_losers": list(reversed(ranked_sorted[-5:])),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
