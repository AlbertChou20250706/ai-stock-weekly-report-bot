"""Render a real candlestick chart (yfinance OHLC data, not AI-drawn) for the
US market's benchmark index (S&P 500)."""

import pathlib
from datetime import date

import mplfinance as mpf
import yfinance as yf

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
CHARTS_DIR = BASE_DIR / "charts"

INDEX_SYMBOL = "^GSPC"
LOOKBACK_DAYS = "1mo"

# Same CJK font fix as generate_chart.py: mplfinance builds its own rc
# context from the style, so the font must go through make_mpf_style(rc=...)
# rather than plain pyplot.rcParams. US convention: green = up, red = down
# (opposite of the TW chart's red-up/green-down).
US_STYLE = mpf.make_mpf_style(
    marketcolors=mpf.make_marketcolors(up="green", down="red", inherit=True),
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
    chart_path = CHARTS_DIR / f"us_index_{today}.png"

    mpf.plot(
        history,
        type="candle",
        style=US_STYLE,
        volume=True,
        figsize=(9, 5.5),
        title="\n美股大盤（S&P 500）",
        savefig=dict(fname=chart_path, dpi=150, bbox_inches="tight"),
    )

    print(f"wrote {chart_path}")


if __name__ == "__main__":
    main()
