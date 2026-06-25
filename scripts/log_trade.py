import json
import os
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), "r") as f:
        return json.load(f)


def save_json(filename, data):
    with open(os.path.join(DATA_DIR, filename), "w") as f:
        json.dump(data, f, indent=2)


def log_buy(ticker, shares, price, account, currency=None):
    """Record a buy: add shares to an existing position or create a new one.

    Updates holdings.json with the new share count and recalculated average
    cost. Also logs the contribution in contributions.json.
    """
    holdings = load_json("holdings.json")
    ticker = ticker.upper()
    shares = float(shares)
    price = float(price)

    if currency is None:
        currency = "CAD" if ".TO" in ticker else "USD"

    existing = None
    for p in holdings["positions"]:
        if p["ticker"] == ticker:
            existing = p
            break

    if existing:
        old_shares = existing["shares"]
        old_cost = existing["avg_cost"]
        old_total = old_shares * old_cost
        new_total = shares * price
        combined_shares = round(old_shares + shares, 6)
        combined_avg = round((old_total + new_total) / combined_shares, 2)

        existing["shares"] = combined_shares
        existing["avg_cost"] = combined_avg

        print(f"\n  UPDATED existing position:")
        print(f"    {ticker}: {old_shares} -> {combined_shares} shares")
        print(f"    Avg cost: ${old_cost} -> ${combined_avg} {currency}")
    else:
        watchlist = load_json("watchlist.json")
        tier2_tickers = [t["ticker"] for t in watchlist["tier2"]["tickers"]]

        if ticker in tier2_tickers:
            status = "active_buy"
        elif ticker in ("XEQT.TO",):
            status = "active_buy"
        else:
            status = "hold_no_add"

        new_position = {
            "ticker": ticker,
            "shares": round(shares, 6),
            "avg_cost": round(price, 2),
            "currency": currency,
            "account": account,
            "status": status,
        }
        holdings["positions"].append(new_position)

        print(f"\n  NEW position added:")
        print(f"    {ticker}: {shares} shares at ${price} {currency}")
        print(f"    Account: {account} | Status: {status}")

    holdings["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    save_json("holdings.json", holdings)
    print(f"  holdings.json updated.")

    cost_cad = shares * price
    if currency == "USD":
        try:
            import yfinance as yf
            fx = yf.Ticker("USDCAD=X")
            rate = fx.fast_info.get("lastPrice") or fx.fast_info.get("last_price") or 1.42
            cost_cad = round(cost_cad * rate, 2)
            print(f"  Cost in CAD: ${cost_cad} (USD/CAD = {rate})")
        except Exception:
            cost_cad = round(cost_cad * 1.42, 2)
            print(f"  Cost in CAD (estimated): ${cost_cad}")

    contributions = load_json("contributions.json")
    contributions["contributions_this_year_cad"] = round(
        contributions["contributions_this_year_cad"] + cost_cad, 2
    )
    contributions["remaining_room_cad"] = round(
        contributions["tfsa_annual_limit"] - contributions["contributions_this_year_cad"], 2
    )
    contributions["milestones"]["current_total_cad"] = round(
        contributions["milestones"]["current_total_cad"] + cost_cad, 2
    )
    contributions["contribution_log"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "amount_cad": cost_cad,
        "notes": f"BUY {shares} {ticker} @ ${price} {currency} ({account})",
    })
    save_json("contributions.json", contributions)
    print(f"  contributions.json updated. TFSA room remaining: ${contributions['remaining_room_cad']:.2f}")


def log_sell(ticker, shares, price):
    """Record a sell: reduce shares from an existing position.

    If all shares are sold, removes the position entirely.
    """
    holdings = load_json("holdings.json")
    ticker = ticker.upper()
    shares = float(shares)
    price = float(price)

    existing = None
    for p in holdings["positions"]:
        if p["ticker"] == ticker:
            existing = p
            break

    if not existing:
        print(f"\n  ERROR: {ticker} not found in holdings. Cannot sell what you don't own.")
        return

    old_shares = existing["shares"]
    if shares > old_shares + 0.0001:
        print(f"\n  ERROR: Trying to sell {shares} shares but only hold {old_shares}.")
        return

    remaining = round(old_shares - shares, 6)

    if remaining < 0.0001:
        holdings["positions"] = [p for p in holdings["positions"] if p["ticker"] != ticker]
        print(f"\n  SOLD ALL {ticker}: {old_shares} shares at ${price}")
        print(f"  Position removed from holdings.")
    else:
        existing["shares"] = remaining
        print(f"\n  PARTIAL SELL {ticker}:")
        print(f"    {old_shares} -> {remaining} shares")
        print(f"    Sold {shares} at ${price}")

    holdings["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    save_json("holdings.json", holdings)
    print(f"  holdings.json updated.")


def print_usage():
    print("""
  Morning Briefing — Trade Logger
  ================================

  Record a buy:
    python log_trade.py buy <TICKER> <SHARES> <PRICE> <ACCOUNT>

  Record a sell:
    python log_trade.py sell <TICKER> <SHARES> <PRICE>

  Examples:
    python log_trade.py buy XEQT.TO 5 44.88 wealthsimple
    python log_trade.py buy BWXT 0.5 205.65 questrade
    python log_trade.py buy MSFT 0.3 365.00 questrade
    python log_trade.py sell OSS 2 17.35

  Accounts: questrade, wealthsimple
  Currency is auto-detected: .TO tickers = CAD, everything else = USD
  Average cost is automatically recalculated when adding to a position.
  TFSA contribution tracking is updated automatically on buys.
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    action = sys.argv[1].lower()

    if action == "buy":
        if len(sys.argv) < 6:
            print("\n  ERROR: Buy needs: python log_trade.py buy <TICKER> <SHARES> <PRICE> <ACCOUNT>")
            print("  Example: python log_trade.py buy XEQT.TO 5 44.88 wealthsimple")
            sys.exit(1)
        ticker = sys.argv[2]
        shares = sys.argv[3]
        price = sys.argv[4]
        account = sys.argv[5].lower()
        if account not in ("questrade", "wealthsimple"):
            print(f"\n  ERROR: Account must be 'questrade' or 'wealthsimple', got '{account}'")
            sys.exit(1)
        log_buy(ticker, shares, price, account)

    elif action == "sell":
        if len(sys.argv) < 5:
            print("\n  ERROR: Sell needs: python log_trade.py sell <TICKER> <SHARES> <PRICE>")
            print("  Example: python log_trade.py sell OSS 2 17.35")
            sys.exit(1)
        ticker = sys.argv[2]
        shares = sys.argv[3]
        price = sys.argv[4]
        log_sell(ticker, shares, price)

    else:
        print(f"\n  ERROR: Unknown action '{action}'. Use 'buy' or 'sell'.")
        print_usage()
