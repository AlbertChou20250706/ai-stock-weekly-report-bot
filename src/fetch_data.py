"""Fetch weekly market data and write it as structured JSON for generate_report.py."""

import json
import pathlib

import yfinance as yf

from twse_institutional import fetch_institutional_flow

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
WATCHLIST_PATH = BASE_DIR / "config" / "watchlist.json"
OUTPUT_PATH = BASE_DIR / "data" / "latest.json"


def fetch_weekly_change(symbol: str) -> dict:
    history = yf.Ticker(symbol).history(period="6d")
    if history.empty or len(history) < 2:
        raise RuntimeError(f"no usable price history for {symbol}")

    first_open = float(history["Open"].iloc[0])
    last_close = float(history["Close"].iloc[-1])
    change_pct = (last_close - first_open) / first_open * 100

    return {
        # LINE auto-linkifies "NNNN.TW" as if it were a domain name (.TW is a
        # real ccTLD), turning stock codes into broken clickable links in the
        # message. Strip the yfinance suffix for display; it's only needed
        # for the API call above.
        "symbol": symbol.removesuffix(".TW").removesuffix(".TWO"),
        "date_start": history.index[0].strftime("%Y-%m-%d"),
        "date_end": history.index[-1].strftime("%Y-%m-%d"),
        "open": round(first_open, 2),
        "close": round(last_close, 2),
        "change_pct": round(change_pct, 2),
    }


def main() -> None:
    watchlist = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))

    index_data = fetch_weekly_change(watchlist["index"]["symbol"])
    index_data["name"] = watchlist["index"]["name"]

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
            data["institutional"] = fetch_institutional_flow(data["symbol"], data["date_end"])
            must_watch.append(data)
        else:
            ranked_pool.append(data)

    ranked_sorted = sorted(ranked_pool, key=lambda e: e["change_pct"], reverse=True)

    result = {
        "date_range": {
            "start": index_data["date_start"],
            "end": index_data["date_end"],
        },
        "index": index_data,
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
