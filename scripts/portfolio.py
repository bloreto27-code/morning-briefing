import json
import os
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), "r") as f:
        return json.load(f)


def build_snapshot(prices, fx_rate):
    """Build a full portfolio snapshot with everything converted to CAD.

    Takes the prices dict from fetch_prices and the live USD/CAD rate.
    Returns a dict with per-position details, account summaries, and totals.
    """
    holdings = load_json("holdings.json")
    positions = []

    for pos in holdings["positions"]:
        ticker = pos["ticker"]
        shares = pos["shares"]
        avg_cost = pos["avg_cost"]
        currency = pos["currency"]
        account = pos["account"]

        price_data = prices.get(ticker)
        if not price_data or "error" in price_data:
            positions.append({
                "ticker": ticker,
                "shares": shares,
                "account": account,
                "currency": currency,
                "error": f"No price data for {ticker}",
            })
            continue

        live_price = price_data["price"]
        day_change = price_data["change"]
        day_pct = price_data["pct_change"]

        value_native = round(shares * live_price, 2)
        cost_native = round(shares * avg_cost, 2)
        gain_native = round(value_native - cost_native, 2)
        gain_pct = round((gain_native / cost_native) * 100, 2) if cost_native else 0

        if currency == "USD":
            value_cad = round(value_native * fx_rate, 2)
            cost_cad = round(cost_native * fx_rate, 2)
            gain_cad = round(value_cad - cost_cad, 2)
        else:
            value_cad = value_native
            cost_cad = cost_native
            gain_cad = gain_native

        positions.append({
            "ticker": ticker,
            "shares": shares,
            "avg_cost": avg_cost,
            "live_price": live_price,
            "day_change": day_change,
            "day_pct": day_pct,
            "currency": currency,
            "account": account,
            "status": pos["status"],
            "value_native": value_native,
            "cost_native": cost_native,
            "gain_native": gain_native,
            "gain_pct": gain_pct,
            "value_cad": value_cad,
            "cost_cad": cost_cad,
            "gain_cad": gain_cad,
        })

    accounts = holdings["accounts"]
    cash_cad = sum(acct["cash"] for acct in accounts.values())

    total_positions_cad = sum(p["value_cad"] for p in positions if "error" not in p)
    total_portfolio_cad = round(total_positions_cad + cash_cad, 2)
    total_cost_cad = sum(p["cost_cad"] for p in positions if "error" not in p)
    total_gain_cad = round(total_positions_cad - total_cost_cad, 2)
    total_gain_pct = round((total_gain_cad / total_cost_cad) * 100, 2) if total_cost_cad else 0

    for p in positions:
        if "error" not in p:
            p["weight_pct"] = round((p["value_cad"] / total_portfolio_cad) * 100, 2) if total_portfolio_cad else 0

    account_summaries = {}
    for acct_key, acct_info in accounts.items():
        acct_positions = [p for p in positions if p.get("account") == acct_key and "error" not in p]
        acct_value = sum(p["value_cad"] for p in acct_positions)
        acct_cost = sum(p["cost_cad"] for p in acct_positions)
        acct_gain = round(acct_value - acct_cost, 2)
        account_summaries[acct_key] = {
            "name": acct_info["name"],
            "positions_value_cad": round(acct_value, 2),
            "cash_cad": acct_info["cash"],
            "total_cad": round(acct_value + acct_info["cash"], 2),
            "gain_cad": acct_gain,
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "fx_rate": fx_rate,
        "positions": positions,
        "accounts": account_summaries,
        "cash_cad": cash_cad,
        "total_positions_cad": round(total_positions_cad, 2),
        "total_portfolio_cad": total_portfolio_cad,
        "total_cost_cad": round(total_cost_cad, 2),
        "total_gain_cad": total_gain_cad,
        "total_gain_pct": total_gain_pct,
    }


def print_snapshot(snapshot):
    """Print the portfolio snapshot in a readable format."""
    print()
    print("=" * 80)
    print("  PORTFOLIO SNAPSHOT")
    print(f"  USD/CAD: {snapshot['fx_rate']}")
    print("=" * 80)

    print(f"\n  {'Ticker':<10} {'Shares':>8} {'Price':>9} {'Value':>10} "
          f"{'CAD Val':>10} {'Gain':>10} {'G%':>7} {'Wt%':>6}")
    print("-" * 80)

    for p in sorted(snapshot["positions"], key=lambda x: x.get("value_cad", 0), reverse=True):
        if "error" in p:
            print(f"  {p['ticker']:<10} {p['shares']:>8.4f}   ERROR — {p['error']}")
            continue

        ccy = p["currency"]
        sign_g = "+" if p["gain_native"] >= 0 else ""
        print(
            f"  {p['ticker']:<10} {p['shares']:>8.4f} "
            f"{p['live_price']:>8.2f}{ccy[0]} "
            f"{p['value_native']:>9.2f}{ccy[0]} "
            f"${p['value_cad']:>9.2f} "
            f"{sign_g}{p['gain_cad']:>9.2f} "
            f"{sign_g}{p['gain_pct']:>6.1f}% "
            f"{p['weight_pct']:>5.1f}%"
        )

    print("-" * 80)
    print(f"  {'Cash':<10} {'':>8} {'':>9} {'':>10} ${snapshot['cash_cad']:>9.2f}")

    sign_t = "+" if snapshot["total_gain_cad"] >= 0 else ""
    print(
        f"  {'TOTAL':<10} {'':>8} {'':>9} {'':>10} "
        f"${snapshot['total_portfolio_cad']:>9.2f} "
        f"{sign_t}{snapshot['total_gain_cad']:>9.2f} "
        f"{sign_t}{snapshot['total_gain_pct']:>6.1f}%"
    )
    print("=" * 80)

    print("\n  ACCOUNT BREAKDOWN")
    print("-" * 50)
    for key, acct in snapshot["accounts"].items():
        sign_a = "+" if acct["gain_cad"] >= 0 else ""
        print(f"  {acct['name']:<25} ${acct['total_cad']:>9.2f}  ({sign_a}${abs(acct['gain_cad']):.2f})")
    print(f"  {'Combined':.<25} ${snapshot['total_portfolio_cad']:>9.2f}")
    print("=" * 50)


if __name__ == "__main__":
    from fetch_prices import fetch_prices, fetch_fx_rate, get_all_tickers

    print("Fetching prices...")
    tickers = get_all_tickers()
    fx_rate = fetch_fx_rate()
    prices = fetch_prices(tickers)

    print(f"USD/CAD = {fx_rate}")
    snapshot = build_snapshot(prices, fx_rate)
    print_snapshot(snapshot)
