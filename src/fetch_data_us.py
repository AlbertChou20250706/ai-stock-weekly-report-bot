"""Fetch weekly US market data and write it as structured JSON for generate_report_us.py."""

import json
import math
import pathlib

import yfinance as yf

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
WATCHLIST_PATH = BASE_DIR / "config" / "watchlist_us.json"
OUTPUT_PATH = BASE_DIR / "data" / "latest_us.json"

WEEK_TRADING_DAYS = 5


def fetch_weekly_change(symbol: str) -> dict:
    # period="Nd" counts calendar days, not trading days — querying on a
    # weekend or right after a holiday can silently return more (or fewer)
    # trading rows than intended (e.g. a Sunday-night query, which is what
    # every Monday-morning Taipei run is in US market time, reaching back to
    # the week before last instead of just last week). Fetch a generous
    # calendar buffer instead and explicitly slice to exactly one trading
    # week below, so the window is stable no matter what day/time this runs.
    history = yf.Ticker(symbol).history(period="1mo")
    # Yahoo's feed can settle the official EOD close later for some
    # instruments (ETFs in particular) than for others — the most recent
    # session can already appear as a row with Open filled in but Close
    # still NaN. Drop any such not-yet-settled trailing rows and fall back
    # to the last settled day, instead of discarding the whole ticker.
    while not history.empty and not math.isfinite(history["Close"].iloc[-1]):
        history = history.iloc[:-1]
    if history.empty or len(history) < WEEK_TRADING_DAYS:
        raise RuntimeError(f"no usable price history for {symbol}")
    history = history.tail(WEEK_TRADING_DAYS)

    first_open = float(history["Open"].iloc[0])
    last_close = float(history["Close"].iloc[-1])
    # yfinance can return NaN for a single row (data-provider gap) without
    # raising anything — NaN silently survives the arithmetic below and, once
    # JSON-serialized as a bare `NaN` token, reads to the model like a missing
    # value, which it then renders as literal "NA" in the report. Treat it as
    # the same failure as no usable history at all, not a value to pass on.
    if not (math.isfinite(first_open) and math.isfinite(last_close)):
        raise RuntimeError(f"non-finite price data for {symbol} (open={first_open}, close={last_close})")
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
