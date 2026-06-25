import json
import os
import sys
from datetime import datetime

import yfinance as yf

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), "r") as f:
        return json.load(f)


def get_all_tickers():
    """Collect every unique ticker from holdings + watchlist."""
    watchlist = load_json("watchlist.json")
    tickers = set()

    tickers.update(watchlist["held"])

    for t2 in watchlist["tier2"]["tickers"]:
        tickers.add(t2["ticker"])

    tickers.update(watchlist["tier3"]["tickers"])
    tickers.update(watchlist["tier4"]["tickers"])

    for etf in watchlist["etfs"]["tickers"]:
        tickers.add(etf["ticker"])

    return sorted(tickers)


def _extract_price_data(ticker, info):
    """Pull price/change/currency from a yfinance fast_info object."""
    price = info.get("lastPrice", None) or info.get("last_price", None)
    prev_close = info.get("previousClose", None) or info.get("previous_close", None)
    currency = info.get("currency", "USD")

    if price is None:
        return {"error": "No price data"}

    change = round(price - prev_close, 2) if prev_close else 0
    pct_change = round((change / prev_close) * 100, 2) if prev_close else 0

    return {
        "price": round(price, 2),
        "prev_close": round(prev_close, 2) if prev_close else None,
        "change": change,
        "pct_change": pct_change,
        "currency": currency,
    }


def fetch_prices(tickers):
    """Fetch live price data for a list of tickers using yfinance.

    Canadian .TO tickers are fetched individually (yfinance batch mode
    mangles the dot). US tickers are fetched in one batch for speed.
    """
    results = {}

    ca_tickers = [t for t in tickers if ".TO" in t]
    us_tickers = [t for t in tickers if ".TO" not in t]

    if us_tickers:
        batch = yf.Tickers(" ".join(us_tickers))
        for ticker in us_tickers:
            try:
                info = batch.tickers[ticker].fast_info
                results[ticker] = _extract_price_data(ticker, info)
            except Exception as e:
                results[ticker] = {"error": str(e)}

    for ticker in ca_tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            results[ticker] = _extract_price_data(ticker, info)
        except Exception as e:
            results[ticker] = {"error": str(e)}

    return results


def fetch_fx_rate():
    """Fetch live USD/CAD exchange rate."""
    try:
        fx = yf.Ticker("USDCAD=X")
        rate = fx.fast_info.get("lastPrice", None) or fx.fast_info.get("last_price", None)
        return round(rate, 4) if rate else None
    except Exception as e:
        print(f"  FX fetch error: {e}")
        return None


def print_price_table(prices, fx_rate):
    """Print a readable price table to the console."""
    print("=" * 72)
    print(f"  PRICE BOARD — {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
    print(f"  USD/CAD: {fx_rate}")
    print("=" * 72)
    print(f"  {'Ticker':<10} {'Price':>10} {'Change':>10} {'%':>8} {'Ccy':>5}")
    print("-" * 72)

    for ticker in sorted(prices.keys()):
        data = prices[ticker]
        if "error" in data:
            print(f"  {ticker:<10} {'ERROR':>10}   {data['error']}")
            continue

        sign = "+" if data["change"] >= 0 else ""
        print(
            f"  {ticker:<10} {data['price']:>10.2f} "
            f"{sign}{data['change']:>9.2f} "
            f"{sign}{data['pct_change']:>7.2f}% "
            f"{data['currency']:>5}"
        )

    print("=" * 72)


def main():
    print("\nFetching all tickers from watchlist...")
    tickers = get_all_tickers()
    print(f"  Found {len(tickers)} tickers: {', '.join(tickers)}\n")

    print("Fetching USD/CAD exchange rate...")
    fx_rate = fetch_fx_rate()
    if fx_rate:
        print(f"  USD/CAD = {fx_rate}\n")
    else:
        print("  WARNING: Could not fetch FX rate\n")

    print(f"Fetching prices for {len(tickers)} tickers...")
    prices = fetch_prices(tickers)

    successes = sum(1 for v in prices.values() if "error" not in v)
    errors = sum(1 for v in prices.values() if "error" in v)
    print(f"  {successes} succeeded, {errors} failed\n")

    print_price_table(prices, fx_rate)

    return prices, fx_rate


if __name__ == "__main__":
    prices, fx_rate = main()
