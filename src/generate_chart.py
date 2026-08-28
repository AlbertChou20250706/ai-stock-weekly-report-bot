"""Render a real candlestick chart (yfinance OHLC data, not AI-drawn) for the TW index."""

import pathlib
from datetime import date

import mplfinance as mpf
import yfinance as yf

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
CHARTS_DIR = BASE_DIR / "charts"

INDEX_SYMBOL = "^TWII"
LOOKBACK_DAYS = "1mo"

# GitHub Actions' ubuntu-latest has no CJK font by default; without this the
# Chinese title renders as tofu boxes (font installed via apt in the workflow:
# fonts-wqy-zenhei). Plain pyplot.rcParams doesn't work here — mplfinance
# builds its own rc context from the style, so the font must be set via
# make_mpf_style(rc=...) instead.
TW_STYLE = mpf.make_mpf_style(
    marketcolors=mpf.make_marketcolors(up="red", down="green", inherit=True),
    gridstyle="",
    facecolor="white",
    rc={"font.sans-serif": ["WenQuanYi Zen Hei"], "axes.unicode_minus": False},
)


def main() -> None:
    history = yf.Ticker(INDEX_SYMBOL).history(period=LOOKBACK_DAYS)
    if history.empty:
        raise RuntimeError(f"no usable price history for {INDEX_SYMBOL}")

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    chart_path = CHARTS_DIR / f"tw_index_{today}.png"

    mpf.plot(
        history,
        type="candle",
        style=TW_STYLE,
        volume=True,
        figsize=(9, 5.5),
        title="\n台灣加權指數",
        savefig=dict(fname=chart_path, dpi=150, bbox_inches="tight"),
    )

    print(f"wrote {chart_path}")


if __name__ == "__main__":
    main()
